#!/usr/bin/env python3
"""kaji-brain: the Brain agent's eyes and hands.

The Kaji "First Mate" (a Sonnet orchestrator) uses this CLI to observe every
worker agent session and to route the user's instructions to the right pane.

Commands (the INTERFACE CONTRACT every downstream stage depends on):

  kaji-brain sessions
      Print a JSON array of worker sessions, one object per pane that Kaji is
      tracking as an agent session. Each object:
          {
            "pane_id":      int,      # Kaji/wezterm pane id
            "harness":      str,      # "claude" | "kiro" | "opencode" | ...
            "project":      str,      # basename of the session cwd
            "state":        str,      # "working" | "waiting" | "background" | ...
            "runtime_secs": int,      # now - start_time
            "tokens_today": int       # from quota.py for that harness (0 if N/A)
          }
      Panes with no runtime.json entry (not agent sessions) are skipped.

  kaji-brain send <pane_id> <text>
      Inject <text> followed by Enter into the given worker pane.

  kaji-brain spawn <harness> <cwd> [initial_task...]
      Spawn a NEW worker session: open a tab in Kaji running <harness>
      (kiro | claude | opencode | codex) in <cwd>. Prints {"pane_id": N} as
      JSON on success. If an initial_task is given, it is sent to the new pane
      once the harness has started. On failure (Kaji not running, bad harness,
      bad cwd) prints {"error": ...} to stderr and exits non-zero. This is how
      the Brain splits work by project: one spawned session per project dir.

  kaji-brain notify <title> <msg>
      Pop a macOS notification.

  kaji-brain watch
      Poll `sessions` every 3s and print a line whenever a session's state
      changes (especially -> waiting). Also appends each transition to the
      event log.

  kaji-brain timeline [--json] [--pane N]
      Render the fleet history from the event log plus the current snapshot.
      --json dumps the parsed events array (for the Cmd+1 Brain view to render).

History substrate: spawn / send / watch append to an append-only event log at
~/.helm/sessions/events.jsonl (one JSON event per line). runtime.json is the
"now" snapshot; events.jsonl is the history chain the timeline renders and a
future First Mate reads. All event writes are best-effort and never raise.

Robustness contract: never crash if Kaji is not running or files are missing.
`sessions` prints [] and exits 0 in that case.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
RUNTIME_JSON = HOME / ".helm" / "sessions" / "runtime.json"
LAST_SESSION_JSON = HOME / ".helm" / "sessions" / "last_session.json"
# Append-only history substrate: one JSON event per line. runtime.json is the
# "now" snapshot (overwritten each tick); events.jsonl is the history chain the
# timeline renders and a future First Mate reads. Override with $HELM_EVENTS_JSONL.
EVENTS_JSONL = (
    Path(os.environ["HELM_EVENTS_JSONL"])
    if os.environ.get("HELM_EVENTS_JSONL")
    else HOME / ".helm" / "sessions" / "events.jsonl"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
QUOTA_PY = REPO_ROOT / "tools" / "helm-quota" / "quota.py"

# Kaji's wezterm-compatible mux CLI. In the Kaji.app bundle this is the `kaku`
# binary (the fork of wezterm's main binary). Note: the sibling `k` binary is
# the agent one-shot CLI, NOT the mux CLI — do not use it here. Allow override
# via $HELM_CLI, and fall back to `wezterm`/`kaku` on PATH.
HELM_CLI = os.environ.get("HELM_CLI") or "/Applications/Kaji.app/Contents/MacOS/helm"

# Where the Kaji GUI drops its mux sockets (gui-sock-<pid>). Overridable for
# tests. A socket file lingering here after a crash/quit is exactly the
# kaji#125 trap: the cli's own discovery may resolve a dead socket.
SOCK_DIR = Path(os.environ.get("HELM_SOCK_DIR") or HOME / ".local" / "share" / "helm")

# harness name -> argv to run in the spawned pane. Mirrors Kaji.harnesses.list
# in kaku.lua so a Brain-spawned session behaves exactly like one started from
# the Kaji launcher (same auto-approve / trust flags). The harness IS the pane
# process (spawned directly, not under a wrapper shell), so the pane lives for
# as long as the agent does.
# Kaji.app launched from Finder/`open -a` gets the minimal GUI PATH
# (/usr/bin:/bin:/usr/sbin:/sbin), so the mux can't find harness binaries that
# live in user dirs ("Unable to spawn codex: No viable candidates found in
# PATH"). Resolve to an absolute path before handing the program to the mux.
EXTRA_BIN_DIRS = [
    "/opt/homebrew/bin",
    "/usr/local/bin",
    str(HOME / ".local" / "bin"),
    str(HOME / ".npm-global" / "bin"),
]


def _resolve_prog(prog):
    """Return prog with argv[0] made absolute (searching PATH + EXTRA_BIN_DIRS)."""
    name = prog[0]
    if os.path.isabs(name):
        return prog
    exe = shutil.which(name)
    if not exe:
        for d in EXTRA_BIN_DIRS:
            cand = os.path.join(d, name)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                exe = cand
                break
    return ([exe] + list(prog[1:])) if exe else list(prog)


HARNESS_CMDS = {
    "kiro": ["kiro-cli", "chat", "--trust-all-tools", "--agent", "default", "--effort", "medium"],
    "claude": ["claude", "--dangerously-skip-permissions"],
    "opencode": ["opencode"],
    "codex": ["codex"],
}


def _helm_cli():
    """Return the argv prefix for the Kaji/wezterm mux cli, or None if missing."""
    if os.path.exists(HELM_CLI):
        return [HELM_CLI, "cli", "--no-auto-start"]
    for name in ("helm", "kaku", "wezterm"):
        found = shutil.which(name)
        if found:
            return [found, "cli", "--no-auto-start"]
    return None


def _live_gui_sock():
    """Path of a live Kaji gui socket, or None if the mux is down.

    Liveness = an actual unix-socket connect, not a PID check: a recycled PID
    or a socket file left behind by a crashed GUI must not count (kaji#125).
    Newest socket wins when several are live (a fresh launch supersedes).
    """
    import socket as _socket
    try:
        candidates = sorted(
            SOCK_DIR.glob("gui-sock-*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    for p in candidates:
        s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect(str(p))
            return str(p)
        except OSError:
            continue
        finally:
            s.close()
    return None


def _cli_run(cli, args, timeout=10):
    """Run a mux cli command pinned to a LIVE gui socket. (rc, stdout, stderr).

    Refuses with a clear error when no live socket exists instead of letting
    the cli's own discovery resolve a stale one (kaji#125 dead-socket send).
    """
    sock = _live_gui_sock()
    if not sock:
        return 1, "", "Kaji mux not running (no live gui socket in %s)" % SOCK_DIR
    env = dict(os.environ)
    env["WEZTERM_UNIX_SOCKET"] = sock
    return _run(cli + args, timeout=timeout, env=env)


def _run(argv, timeout=10, env=None):
    """Run a command, returning (rc, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
        )
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - robustness: never crash
        return 1, "", str(e)


# ── sessions ────────────────────────────────────────────────────────────────

def list_panes():
    """Pane dicts from the Kaji cli. [] = mux up but no panes; None = mux
    down/unreachable. Callers MUST treat None as "no live fleet", never fall
    back to cached state (kaji#125 phantom sessions)."""
    cli = _helm_cli()
    if not cli:
        return None
    rc, out, _ = _cli_run(cli, ["list", "--format", "json"])
    if rc != 0:
        return None
    if not out.strip():
        return []
    try:
        data = json.loads(out)
    except Exception:
        return None
    return data if isinstance(data, list) else None


def load_runtime():
    """Return the runtime.json map {pane_id(str): {...}} or {} if missing/bad."""
    if not RUNTIME_JSON.exists():
        return {}
    try:
        raw = RUNTIME_JSON.read_text()
        data = json.loads(raw) if raw.strip() else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# quota.py scans session files on every run — memoize briefly so the serve
# poll loop (SSE beat + several clients at 4s) doesn't re-scan constantly.
_QUOTA_CACHE = {"ts": 0.0, "data": {}}
QUOTA_TTL_SECS = float(os.environ.get("HELM_QUOTA_TTL", "20"))


def load_quota_raw():
    """Full per-harness dict from quota.py --json (briefly cached). {} on failure."""
    now = time.time()
    if now - _QUOTA_CACHE["ts"] < QUOTA_TTL_SECS:
        return _QUOTA_CACHE["data"]
    data = {}
    if QUOTA_PY.exists():
        rc, out, _ = _run([sys.executable or "python3", str(QUOTA_PY), "--json"])
        if rc == 0 and out.strip():
            try:
                parsed = json.loads(out)
                if isinstance(parsed, dict):
                    data = parsed
            except Exception:
                pass
    _QUOTA_CACHE["ts"] = now
    _QUOTA_CACHE["data"] = data
    return data


def load_quota():
    """Return {harness: tokens_today} (lowercase keys). {} on any failure."""
    tokens = {}
    for name, info in load_quota_raw().items():
        if isinstance(info, dict):
            tokens[name.lower()] = info.get("tokens_today", 0) or 0
    return tokens


def _munge_cwd(cwd):
    """cwd path the way ~/.claude/projects names dirs (mirror of quota.py)."""
    return str(cwd or "").replace("/", "-").replace(".", "-").replace("_", "-")


def load_by_project():
    """{harness: {project-key: tokens_today}} from quota.py (cached)."""
    out = {}
    for name, info in load_quota_raw().items():
        if isinstance(info, dict) and isinstance(info.get("by_project"), dict):
            out[name.lower()] = info["by_project"]
    return out


def load_limits():
    """Return {harness: limits-dict} for harnesses exposing real quota
    (used_percent / resets_at / plan — currently codex only). {} if none."""
    limits = {}
    for name, info in load_quota_raw().items():
        if isinstance(info, dict) and isinstance(info.get("limits"), dict):
            limits[name.lower()] = info["limits"]
    return limits


# ── event log (append-only history substrate) ────────────────────────────────

def append_event(ev, **fields):
    """Append one event to events.jsonl. Best-effort: NEVER raises.

    An event is {"ts": <unix int>, "ev": <type>, **fields}. Writers are pure
    rules (0 token): spawn / dispatch / state. Logging must never break the
    command that triggered it, so all I/O errors are swallowed.
    """
    rec = {"ts": int(time.time()), "ev": ev}
    rec.update(fields)
    try:
        EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - robustness: the log is best-effort
        pass
    return rec


def read_events():
    """Return events.jsonl as a list of dicts (oldest first). [] if missing.

    Corrupt lines are skipped, not fatal — a half-written final line must not
    lose the whole history.
    """
    if not EVENTS_JSONL.exists():
        return []
    out = []
    try:
        with open(EVENTS_JSONL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
    except Exception:  # noqa: BLE001 - robustness: return what we parsed so far
        return out
    return out


def _as_pane(pane_id):
    """Best-effort int pane id (events use ints to match the snapshot)."""
    try:
        return int(pane_id)
    except (TypeError, ValueError):
        return pane_id


def collect_sessions():
    """Merge panes + runtime.json + quota into the contract's session objects."""
    runtime = load_runtime()
    if not runtime:
        return []

    panes = list_panes()
    if panes is None:
        # Mux down/unreachable: runtime.json is then a stale snapshot, never
        # report it as a live fleet (kaji#125 phantom sessions).
        return []
    quota = load_quota()
    by_project = load_by_project()
    live_ids = {str(p.get("pane_id")) for p in panes}

    now = int(time.time())
    sessions = []
    for pane_id, s in runtime.items():
        if not isinstance(s, dict):
            continue
        if str(pane_id) not in live_ids:
            # Tracked in runtime but no longer a live pane -> skip.
            continue
        harness_raw = (s.get("harness") or "").strip()
        harness = harness_raw.lower()
        cwd = s.get("cwd") or ""
        project = os.path.basename(cwd.rstrip("/")) or cwd
        start_time = s.get("start_time") or 0
        try:
            runtime_secs = max(0, now - int(start_time))
        except Exception:
            runtime_secs = 0
        try:
            pid = int(pane_id)
        except Exception:
            pid = pane_id
        # Per-session burn: this session's own tokens today + share of the
        # harness total. claude keys by munged cwd, codex by the exact cwd.
        cwd_full = s.get("cwd_full") or cwd
        proj_map = by_project.get(harness, {})
        own = int(proj_map.get(_munge_cwd(cwd_full))
                  or proj_map.get(cwd_full) or 0)
        total = int(quota.get(harness, 0) or 0)
        sessions.append({
            "pane_id": pid,
            "harness": harness,
            "project": project,
            "state": s.get("state") or "working",
            "runtime_secs": runtime_secs,
            "tokens_today": total,
            "tokens_session": own,
            "tokens_share": (round(100.0 * own / total) if total and own else 0),
        })

    sessions.sort(key=lambda x: str(x["pane_id"]))
    return sessions


def cmd_sessions(_args):
    print(json.dumps(collect_sessions()))
    return 0


# ── send ─────────────────────────────────────────────────────────────────────

def _send_text(cli, pane_id, text):
    """Inject text + a carriage return into a pane. Returns (rc, errmsg)."""
    # Inject the text without the auto trailing newline paste behaviour, then
    # send a carriage return so the agent actually submits the line. Using argv
    # (not string interpolation) keeps arbitrary text safe.
    rc, _, err = _cli_run(cli, ["send-text", "--pane-id", str(pane_id), "--no-paste", "--", text])
    if rc != 0:
        return rc, (err.strip() or "send-text failed")
    # Second call: the carriage return to submit.
    rc2, _, err2 = _cli_run(cli, ["send-text", "--pane-id", str(pane_id), "--no-paste", "--", "\r"])
    if rc2 != 0:
        return rc2, (err2.strip() or "send-text (CR) failed")
    return 0, ""


def cmd_send(args):
    if len(args) < 2:
        print("usage: kaji-brain send <pane_id> <text>", file=sys.stderr)
        return 2
    pane_id = args[0]
    text = args[1]
    cli = _helm_cli()
    if not cli:
        print("helm cli not available (Kaji not installed?)", file=sys.stderr)
        return 1
    rc, err = _send_text(cli, pane_id, text)
    if rc != 0:
        print(err, file=sys.stderr)
    else:
        # History: record what the captain dispatched to this worker.
        append_event("dispatch", pane=_as_pane(pane_id), text=text)
    return rc


# ── spawn ─────────────────────────────────────────────────────────────────────

def cmd_spawn(args):
    if len(args) < 2:
        print(json.dumps({"error": "usage: kaji-brain spawn <harness> <cwd> [task...]"}),
              file=sys.stderr)
        return 2
    harness = (args[0] or "").strip().lower()
    cwd = args[1]
    task = " ".join(args[2:]).strip() if len(args) > 2 else ""

    prog = HARNESS_CMDS.get(harness)
    if prog:
        prog = _resolve_prog(prog)
    if not prog:
        print(json.dumps({"error": "unknown harness: %s" % harness,
                          "known": sorted(HARNESS_CMDS)}), file=sys.stderr)
        return 2

    cwd_abs = os.path.abspath(os.path.expanduser(cwd))
    if not os.path.isdir(cwd_abs):
        print(json.dumps({"error": "cwd is not a directory: %s" % cwd_abs}), file=sys.stderr)
        return 2

    cli = _helm_cli()
    if not cli:
        print(json.dumps({"error": "helm cli not available (Kaji not running?)"}),
              file=sys.stderr)
        return 1

    # Keep every worker session visible at once: tile them in ONE "Work" tab.
    # The first worker opens a new tab; each later worker SPLITS an existing
    # worker pane in that tab instead of opening a separate (hidden) tab. We
    # find the Work tab via runtime.json (the GUI keys it by worker pane id) and
    # split its largest still-live pane. `--` separates cli options from the
    # program; split-pane/spawn both print the new pane id on stdout.
    panes = list_panes()
    if panes is None:
        print(json.dumps({"error": "Kaji mux not running (no live gui socket)"}),
              file=sys.stderr)
        return 1
    by_id = {}
    for p in panes:
        pid = p.get("pane_id")
        if pid is not None:
            by_id[int(pid)] = p
    live = set(by_id.keys())
    try:
        with open(RUNTIME_JSON) as _rf:
            workers = [int(k) for k in json.load(_rf).keys()]
    except Exception:
        workers = []
    # Exclude the calling pane: kaji-brain is invoked FROM the Brain, so the
    # Brain's own pane must never be used as a split anchor (that would tile the
    # worker right next to the Brain instead of into the dedicated Work tab).
    try:
        _origin_id = int(os.environ.get("WEZTERM_PANE", ""))
    except (TypeError, ValueError):
        _origin_id = None
    cand = [w for w in workers if w in live and w != _origin_id]
    if cand:
        # Balanced tiling: split the LARGEST worker pane along its longer side.
        # Splitting the biggest pane each time keeps the Work grid even as it
        # grows (2 -> equal columns, 4 -> even 2x2) instead of degrading into
        # thin slivers. Orientation uses true pixel aspect: wide -> left/right,
        # tall -> top/bottom.
        def _area(w):
            s = by_id[w].get("size") or {}
            return (s.get("pixel_width") or 0) * (s.get("pixel_height") or 0)
        anchor = max(cand, key=_area)
        s = by_id[anchor].get("size") or {}
        direction = "--right" if (s.get("pixel_width") or 0) >= (s.get("pixel_height") or 0) else "--bottom"
        rc, out, err = _cli_run(cli, ["split-pane", "--pane-id", str(anchor),
                                      "--cwd", cwd_abs, direction, "--"] + prog)
    else:
        rc, out, err = _cli_run(cli, ["spawn", "--cwd", cwd_abs, "--"] + prog)
    if rc != 0:
        print(json.dumps({"error": err.strip() or "spawn failed (is Kaji running?)"}),
              file=sys.stderr)
        return rc or 1

    pane_line = out.strip().splitlines()[-1].strip() if out.strip() else ""
    try:
        pane_id = int(pane_line)
    except Exception:
        print(json.dumps({"error": "could not parse pane id from spawn output",
                          "raw": out.strip()}), file=sys.stderr)
        return 1

    result = {"pane_id": pane_id, "harness": harness, "cwd": cwd_abs}

    # History: record the spawn (with the initial task) on the event log.
    append_event("spawn", pane=pane_id, harness=harness,
                 cwd=os.path.basename(cwd_abs.rstrip("/")) or cwd_abs, task=task)

    # Don't steal focus. Spawning/splitting activates the new worker pane, but
    # the captain lives in the Brain — return focus there immediately. The task
    # send below targets the worker by pane id, so it doesn't need focus.
    origin = os.environ.get("WEZTERM_PANE")
    if origin:
        _cli_run(cli, ["activate-pane", "--pane-id", str(origin)])

    if task:
        # Give the harness a moment to boot its prompt before sending the task.
        time.sleep(2.0)
        srt, serr = _send_text(cli, pane_id, task)
        result["task_sent"] = (srt == 0)
        if srt != 0:
            result["task_error"] = serr
    print(json.dumps(result))
    return 0


# ── notify ────────────────────────────────────────────────────────────────────

def _osa_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def cmd_notify(args):
    if len(args) < 2:
        print("usage: kaji-brain notify <title> <msg>", file=sys.stderr)
        return 2
    title, msg = args[0], args[1]
    script = 'display notification "%s" with title "%s"' % (_osa_escape(msg), _osa_escape(title))
    rc, _, err = _run(["osascript", "-e", script])
    if rc != 0:
        print(err.strip() or "osascript failed", file=sys.stderr)
        return rc
    return 0


# ── watch ─────────────────────────────────────────────────────────────────────

def cmd_watch(_args):
    prev = {}
    print("kaji-brain watch — polling every 3s (Ctrl-C to stop)", file=sys.stderr)
    try:
        while True:
            for s in collect_sessions():
                pid = s["pane_id"]
                state = s["state"]
                if prev.get(pid) != state:
                    arrow = "->" if pid in prev else "  "
                    print("[%s] pane %s (%s/%s) %s %s" % (
                        time.strftime("%H:%M:%S"), pid, s["harness"], s["project"], arrow, state))
                    sys.stdout.flush()
                    # History: every state transition is an event. The watch
                    # poll loop is the designated state writer (no Lua change).
                    append_event("state", pane=_as_pane(pid), to=state,
                                 harness=s["harness"], project=s["project"])
                    prev[pid] = state
            time.sleep(3)
    except KeyboardInterrupt:
        return 0


# ── timeline ──────────────────────────────────────────────────────────────────

def _fmt_hms(ts):
    try:
        return time.strftime("%H:%M:%S", time.localtime(int(ts)))
    except Exception:
        return "--:--:--"


def _fmt_event(e):
    ev = e.get("ev", "?")
    pane = e.get("pane", "?")
    ts = _fmt_hms(e.get("ts"))
    if ev == "spawn":
        det = "%s in %s" % (e.get("harness", "?"), e.get("cwd", "?"))
        task = e.get("task")
        if task:
            det += '  — "%s"' % task
    elif ev == "dispatch":
        det = '"%s"' % (e.get("text", ""))
    elif ev == "state":
        det = e.get("to", "?")
    else:
        extra = {k: v for k, v in e.items() if k not in ("ts", "ev", "pane")}
        det = json.dumps(extra, ensure_ascii=False) if extra else ""
    return "  %s  pane %-3s %-9s %s" % (ts, pane, ev, det)


def cmd_timeline(args):
    """Render the fleet history (events.jsonl) + the current snapshot.

      --json    dump the parsed events array (for the Cmd+1 Brain view to render)
      --pane N  restrict the feed to one pane
    """
    want_json = "--json" in args
    pane_filter = None
    if "--pane" in args:
        i = args.index("--pane")
        if i + 1 < len(args):
            try:
                pane_filter = int(args[i + 1])
            except ValueError:
                pane_filter = None

    events = read_events()
    if pane_filter is not None:
        events = [e for e in events if e.get("pane") == pane_filter]

    if want_json:
        print(json.dumps(events))
        return 0

    print("Kaji fleet timeline  (%s)" % EVENTS_JSONL)
    print()

    # "now" — the live snapshot from runtime.json + quota.
    sessions = collect_sessions()
    if pane_filter is not None:
        sessions = [s for s in sessions if s.get("pane_id") == pane_filter]
    if sessions:
        print("now:")
        for s in sessions:
            mins = s["runtime_secs"] // 60
            tok = s["tokens_today"]
            tokstr = ("  %s tok" % tok) if tok else ""
            print("  pane %-3s %s/%-12s %-9s %dm%s" % (
                s["pane_id"], s["harness"], s["project"], s["state"], mins, tokstr))
        print()
    else:
        print("now: (no live sessions)\n")

    # Feed — newest first.
    if not events:
        print("events: (none yet — spawn a worker to start the log)")
        return 0
    print("events (newest first):")
    for e in reversed(events):
        print(_fmt_event(e))
    return 0


# ── dispatch ──────────────────────────────────────────────────────────────────

USAGE = """kaji-brain — the Brain agent's eyes and hands

usage:
  kaji-brain sessions                 print JSON array of worker sessions
  kaji-brain send <pane_id> <text>    inject text + Enter into a pane
  kaji-brain spawn <harness> <cwd> [task...]
                                      open a new worker session (kiro|claude|
                                      opencode|codex) in <cwd>, optionally
                                      sending an initial task. Prints {"pane_id":N}.
  kaji-brain notify <title> <msg>     pop a macOS notification
  kaji-brain watch                    stream session state changes
  kaji-brain timeline [--json] [--pane N]
                                      render the fleet history (events.jsonl)
                                      + the current snapshot
  kaji-brain serve [--host H] [--port P] [--token T]
                                      run the fleet HTTP+SSE API (default
                                      127.0.0.1:8765). Non-loopback host needs
                                      a token. Clients: cockpit, phone, scripts.
"""

def cmd_last_session(_args):
    """Print the previous run's worker sessions, for the Brain's restore offer.

    Reads last_session.json (written by the GUI at startup, before live tracking
    resets). Emits a JSON array of {harness, cwd, cwd_full, state}, de-duped by
    (harness, cwd_full), harness lowercased so it can be passed straight to
    `kaji-brain spawn`. Empty array if there's nothing to restore.
    """
    try:
        with open(LAST_SESSION_JSON) as f:
            data = json.load(f)
    except Exception:
        data = {}
    seen = set()
    out = []
    for _id, s in (data or {}).items():
        if not isinstance(s, dict):
            continue
        harness = (s.get("harness") or "").strip().lower()
        cwd_full = s.get("cwd_full") or ""
        if not harness or not cwd_full:
            continue
        key = (harness, cwd_full)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "harness": harness,
            "cwd": s.get("cwd") or "",
            "cwd_full": cwd_full,
            "state": s.get("state") or "",
        })
    print(json.dumps(out))
    return 0


def cmd_quota(_args):
    """Print the full per-harness quota dict (tokens_today + limits) as JSON."""
    print(json.dumps(load_quota_raw()))
    return 0


COMMANDS = {
    "sessions": cmd_sessions,
    "quota": cmd_quota,
    "send": cmd_send,
    "spawn": cmd_spawn,
    "notify": cmd_notify,
    "watch": cmd_watch,
    "timeline": cmd_timeline,
    "last-session": cmd_last_session,
    "serve": lambda args: __import__("serve").cmd_serve(args),
}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        sys.stdout.write(USAGE)
        return 0
    cmd = argv[0]
    fn = COMMANDS.get(cmd)
    if not fn:
        sys.stderr.write("unknown command: %s\n\n%s" % (cmd, USAGE))
        return 2
    return fn(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
