#!/usr/bin/env python3
"""helm-brain: the Brain agent's eyes and hands.

The Helm "First Mate" (a Sonnet orchestrator) uses this CLI to observe every
worker agent session and to route the user's instructions to the right pane.

Commands (the INTERFACE CONTRACT every downstream stage depends on):

  helm-brain sessions
      Print a JSON array of worker sessions, one object per pane that Helm is
      tracking as an agent session. Each object:
          {
            "pane_id":      int,      # Helm/wezterm pane id
            "harness":      str,      # "claude" | "kiro" | "opencode" | ...
            "project":      str,      # basename of the session cwd
            "state":        str,      # "working" | "waiting" | "background" | ...
            "runtime_secs": int,      # now - start_time
            "tokens_today": int       # from quota.py for that harness (0 if N/A)
          }
      Panes with no runtime.json entry (not agent sessions) are skipped.

  helm-brain send <pane_id> <text>
      Inject <text> followed by Enter into the given worker pane.

  helm-brain spawn <harness> <cwd> [initial_task...]
      Spawn a NEW worker session: open a tab in Helm running <harness>
      (kiro | claude | opencode | codex) in <cwd>. Prints {"pane_id": N} as
      JSON on success. If an initial_task is given, it is sent to the new pane
      once the harness has started. On failure (Helm not running, bad harness,
      bad cwd) prints {"error": ...} to stderr and exits non-zero. This is how
      the Brain splits work by project: one spawned session per project dir.

  helm-brain notify <title> <msg>
      Pop a macOS notification.

  helm-brain watch
      Poll `sessions` every 3s and print a line whenever a session's state
      changes (especially -> waiting).

Robustness contract: never crash if Helm is not running or files are missing.
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
REPO_ROOT = Path(__file__).resolve().parents[2]
QUOTA_PY = REPO_ROOT / "tools" / "helm-quota" / "quota.py"

# Helm's wezterm-compatible mux CLI. In the Helm.app bundle this is the `kaku`
# binary (the fork of wezterm's main binary). Note: the sibling `k` binary is
# the agent one-shot CLI, NOT the mux CLI — do not use it here. Allow override
# via $HELM_CLI, and fall back to `wezterm`/`kaku` on PATH.
HELM_CLI = os.environ.get("HELM_CLI") or "/Applications/Helm.app/Contents/MacOS/kaku"

# harness name -> argv to run in the spawned pane. Mirrors Helm.harnesses.list
# in kaku.lua so a Brain-spawned session behaves exactly like one started from
# the Helm launcher (same auto-approve / trust flags). The harness IS the pane
# process (spawned directly, not under a wrapper shell), so the pane lives for
# as long as the agent does.
HARNESS_CMDS = {
    "kiro": ["kiro-cli", "chat", "--trust-all-tools", "--agent", "default", "--effort", "medium"],
    "claude": ["claude", "--dangerously-skip-permissions"],
    "opencode": ["opencode"],
    "codex": ["codex"],
}


def _helm_cli():
    """Return the argv prefix for the Helm/wezterm mux cli, or None if missing."""
    if os.path.exists(HELM_CLI):
        return [HELM_CLI, "cli", "--no-auto-start"]
    for name in ("kaku", "wezterm"):
        found = shutil.which(name)
        if found:
            return [found, "cli", "--no-auto-start"]
    return None


def _run(argv, timeout=10):
    """Run a command, returning (rc, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - robustness: never crash
        return 1, "", str(e)


# ── sessions ────────────────────────────────────────────────────────────────

def list_panes():
    """Return the list of pane dicts from the Helm cli, or [] if unavailable."""
    cli = _helm_cli()
    if not cli:
        return []
    rc, out, _ = _run(cli + ["list", "--format", "json"])
    if rc != 0 or not out.strip():
        return []
    try:
        data = json.loads(out)
    except Exception:
        return []
    return data if isinstance(data, list) else []


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


def load_quota():
    """Return {harness: tokens_today} (lowercase keys). {} on any failure."""
    if not QUOTA_PY.exists():
        return {}
    rc, out, _ = _run([sys.executable or "python3", str(QUOTA_PY), "--json"])
    if rc != 0 or not out.strip():
        return {}
    try:
        data = json.loads(out)
    except Exception:
        return {}
    tokens = {}
    if isinstance(data, dict):
        for name, info in data.items():
            if isinstance(info, dict):
                tokens[name.lower()] = info.get("tokens_today", 0) or 0
    return tokens


def collect_sessions():
    """Merge panes + runtime.json + quota into the contract's session objects."""
    runtime = load_runtime()
    if not runtime:
        return []

    quota = load_quota()
    panes = list_panes()
    # Pane ids known to Helm right now (so we only report live panes when the
    # pane list is available). If Helm isn't running we fall back to runtime.
    live_ids = {str(p.get("pane_id")) for p in panes} if panes else None

    now = int(time.time())
    sessions = []
    for pane_id, s in runtime.items():
        if not isinstance(s, dict):
            continue
        if live_ids is not None and str(pane_id) not in live_ids:
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
        sessions.append({
            "pane_id": pid,
            "harness": harness,
            "project": project,
            "state": s.get("state") or "working",
            "runtime_secs": runtime_secs,
            "tokens_today": int(quota.get(harness, 0) or 0),
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
    rc, _, err = _run(cli + ["send-text", "--pane-id", str(pane_id), "--no-paste", "--", text])
    if rc != 0:
        return rc, (err.strip() or "send-text failed")
    # Second call: the carriage return to submit.
    rc2, _, err2 = _run(cli + ["send-text", "--pane-id", str(pane_id), "--no-paste", "--", "\r"])
    if rc2 != 0:
        return rc2, (err2.strip() or "send-text (CR) failed")
    return 0, ""


def cmd_send(args):
    if len(args) < 2:
        print("usage: helm-brain send <pane_id> <text>", file=sys.stderr)
        return 2
    pane_id = args[0]
    text = args[1]
    cli = _helm_cli()
    if not cli:
        print("helm cli not available (Helm not installed?)", file=sys.stderr)
        return 1
    rc, err = _send_text(cli, pane_id, text)
    if rc != 0:
        print(err, file=sys.stderr)
    return rc


# ── spawn ─────────────────────────────────────────────────────────────────────

def cmd_spawn(args):
    if len(args) < 2:
        print(json.dumps({"error": "usage: helm-brain spawn <harness> <cwd> [task...]"}),
              file=sys.stderr)
        return 2
    harness = (args[0] or "").strip().lower()
    cwd = args[1]
    task = " ".join(args[2:]).strip() if len(args) > 2 else ""

    prog = HARNESS_CMDS.get(harness)
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
        print(json.dumps({"error": "helm cli not available (Helm not running?)"}),
              file=sys.stderr)
        return 1

    # Spawn a new tab running the harness in cwd. `kaku cli spawn` prints the
    # new pane id on stdout. The `--` separates spawn's options from the program.
    rc, out, err = _run(cli + ["spawn", "--cwd", cwd_abs, "--"] + prog)
    if rc != 0:
        print(json.dumps({"error": err.strip() or "spawn failed (is Helm running?)"}),
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
        print("usage: helm-brain notify <title> <msg>", file=sys.stderr)
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
    print("helm-brain watch — polling every 3s (Ctrl-C to stop)", file=sys.stderr)
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
                    prev[pid] = state
            time.sleep(3)
    except KeyboardInterrupt:
        return 0


# ── dispatch ──────────────────────────────────────────────────────────────────

USAGE = """helm-brain — the Brain agent's eyes and hands

usage:
  helm-brain sessions                 print JSON array of worker sessions
  helm-brain send <pane_id> <text>    inject text + Enter into a pane
  helm-brain spawn <harness> <cwd> [task...]
                                      open a new worker session (kiro|claude|
                                      opencode|codex) in <cwd>, optionally
                                      sending an initial task. Prints {"pane_id":N}.
  helm-brain notify <title> <msg>     pop a macOS notification
  helm-brain watch                    stream session state changes
"""

COMMANDS = {
    "sessions": cmd_sessions,
    "send": cmd_send,
    "spawn": cmd_spawn,
    "notify": cmd_notify,
    "watch": cmd_watch,
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
