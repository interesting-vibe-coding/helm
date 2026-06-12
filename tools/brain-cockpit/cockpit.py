#!/usr/bin/env python3
"""brain-cockpit — the render-only Brain (Cmd+1).

A pure-visualization cockpit for the fleet: brand + session list + status dots +
"most-neglected first" ordering + the selected session's history. NO model —
see docs/BRAIN_DESIGN.md § "Visualization first". It reads the substrate
(`kaji-brain sessions` for the live snapshot, `kaji-brain timeline --json` for
history) and renders one calm screen.

This is **TUI-first**: cloud-buildable, lower-risk, and the layout the eventual
native GUI overlay (and any future LLM region) would mirror. Rendering is a pure
function of (sessions, events, selection, width) so it is unit-tested and
screenshot-able with `--demo --once`; the interactive key loop is a thin shell
on top.

Aesthetic: Kaji ghost + warm ink. Status reads at a glance —
  ● waiting (amber, needs you)  ● working (teal)  ● idle (grey)
  ● done (dim)  ● error (red)  ● background (blue)
The list is ordered so the session most likely to need you is always on top.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# ── palette ───────────────────────────────────────────────────────────────────
# 24-bit ANSI. Kept in one place so the GUI port can reuse the same values.
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def _fg(r: int, g: int, b: int) -> str:
    return "\033[38;2;%d;%d;%dm" % (r, g, b)


# Kaji Sun (docs/design/KAJI_EMBER.md + kaji-sun-v3): two faces, one hero.
#   day   — paper terminal bg, warm ink text
#   night — warm charcoal bg, candle-lit cream text (own palette, NOT Kaku's)
# Persimmon is constant across both: orange means "needs you", nothing else.
# Theme comes from KAJI_THEME (set by kaku.lua to match the window scheme)
# or --theme; default night — safe on the dark terminals most people run.
_DARK = os.environ.get("KAJI_THEME", "dark").lower() != "light"

SUN = _fg(0xF2, 0x5C, 0x05)     # persimmon — brand + waiting + selection
if _DARK:                        # Sun Night
    INK = _fg(0xEC, 0xE4, 0xD6)  # warm cream (paper, inverted)
    MUTE = _fg(0x9C, 0x92, 0x83) # secondary
    ASH = _fg(0x66, 0x5E, 0x53)  # quiet
    _ERR = _fg(0xE0, 0x5A, 0x48)
else:                            # Sun Day
    INK = _fg(0x21, 0x1C, 0x15)  # warm ink on cream
    MUTE = _fg(0x8A, 0x81, 0x74)
    ASH = _fg(0xC0, 0xB8, 0xA8)
    _ERR = _fg(0xC0, 0x3A, 0x2B)
GHOST = SUN                      # back-compat alias
SEL = SUN

# state -> (glyph, color, label). Orange has ONE meaning: needs you.
# Working = ink (visible, calm); done/idle = ash (silence is data).
_STATE_STYLE = {
    "waiting":    ("●", SUN, "waiting"),
    "working":    ("●", INK, "working"),
    "error":      ("●", _ERR, "error"),
    "background": ("●", MUTE, "background"),
    "idle":       ("○", ASH, "idle"),
    "done":       ("○", ASH, "done"),
}
_UNKNOWN_STYLE = ("●", MUTE, "?")

# Sort priority by state — lower is higher on the list ("most-neglected first").
_PRIORITY = {"waiting": 0, "error": 1, "working": 2, "background": 3,
             "idle": 4, "done": 5}


def status_style(state: str) -> Tuple[str, str, str]:
    return _STATE_STYLE.get((state or "").lower(), _UNKNOWN_STYLE)


# ── pure data shaping ─────────────────────────────────────────────────────────

def sort_sessions(sessions: List[Dict]) -> List[Dict]:
    """Most-neglected first: waiting (longest-waiting) → working → … → done.

    Within a state, longer runtime sorts first, so the worker that has been
    blocked the longest is always at the top — the one you most need to clear.
    """
    def key(s):
        state = (s.get("state") or "").lower()
        return (_PRIORITY.get(state, 9), -int(s.get("runtime_secs") or 0),
                str(s.get("pane_id")))
    return sorted(sessions, key=key)


def fmt_runtime(secs: int) -> str:
    secs = max(0, int(secs or 0))
    if secs < 60:
        return "%ds" % secs
    if secs < 3600:
        return "%dm" % (secs // 60)
    return "%dh%02dm" % (secs // 3600, (secs % 3600) // 60)


def pane_events(events: List[Dict], pane) -> List[Dict]:
    return [e for e in events if e.get("pane") == pane]


def last_activity(events: List[Dict], pane) -> str:
    """A one-line summary of a pane's most recent meaningful event."""
    evs = pane_events(events, pane)
    if not evs:
        return ""
    e = evs[-1]
    ev = e.get("ev")
    if ev == "spawn":
        t = e.get("task") or ""
        return ("spawned: %s" % t) if t else "spawned"
    if ev == "dispatch":
        return "you sent: %s" % (e.get("text") or "")
    if ev == "state":
        return "→ %s" % (e.get("to") or "?")
    return ev or ""


def _visible_len(s: str) -> int:
    return len(s)


def _clip(s: str, n: int) -> str:
    """Clip a plain (un-colored) string to n columns with an ellipsis."""
    return s if len(s) <= n else (s[: max(0, n - 1)] + "…")


# ── rendering (pure) ──────────────────────────────────────────────────────────

def _c(text: str, color: str, color_on: bool) -> str:
    return (color + text + RESET) if color_on else text


def fmt_quota_line(quota: Optional[Dict]) -> str:
    """One plain line: per-harness tokens today + %-left where known."""
    if not quota:
        return ""
    parts = []
    for name in sorted(quota):
        info = quota.get(name) or {}
        if not isinstance(info, dict):
            continue
        tok = int(info.get("tokens_today") or 0)
        lim = info.get("limits") or {}
        fh = lim.get("five_hour_used_percent", lim.get("primary_used_percent"))
        sd = lim.get("seven_day_used_percent", lim.get("secondary_used_percent"))
        if not tok and fh is None and sd is None:
            continue
        seg = name
        if tok:
            seg += " %s" % ("%.1fM" % (tok / 1e6) if tok >= 1e6 else
                            "%dk" % (tok // 1000) if tok >= 1000 else str(tok))
        if fh is not None:
            seg += " 5h %d%%" % round(fh)
        if sd is not None:
            seg += " wk %d%%" % round(sd)
        parts.append(seg)
    return "   ".join(parts)


def render(sessions: List[Dict], events: List[Dict], selected: int = 0,
           width: int = 80, color: bool = True,
           quota: Optional[Dict] = None, loading: bool = False,
           transcript: Optional[List] = None) -> str:
    """Render one cockpit frame as a string. Pure — no I/O, no globals."""
    width = max(40, width)
    ordered = sort_sessions(sessions)
    n = len(ordered)
    sel = min(max(0, selected), n - 1) if n else 0
    out: List[str] = []

    # Header — one line: mark + brand + quota numbers (v3: no taglines).
    qline = fmt_quota_line(quota)
    head = _c("  ◉ ", SUN, color) + _c("KA", BOLD, color) + _c("JI", SUN, color)
    if qline:
        # Right-aligned, mirroring the phone header: brand left, numbers right.
        qtxt = _clip(qline, width - 12)
        pad = max(2, width - 10 - _visible_len(qtxt))
        head += " " * pad + _c(qtxt, MUTE, color)
    out.append(head)
    out.append(_c("  " + "─" * (width - 4), ASH, color))
    out.append("")

    if loading and not ordered:
        out.append(_c("  …", ASH, color))
        out.append("")
        return "\n".join(out)

    def emit_transcript():
        for who, text in (transcript or [])[-12:]:
            for j, line in enumerate(_wrap(text, width - 8)):
                if who == "you":
                    pre = _c("you ", MUTE, color) if j == 0 else "    "
                    out.append("  " + pre + _c(line, MUTE, color))
                elif who == "act":
                    out.append("  " + _c("    " + line, SUN, color))
                else:
                    # ◉ is the product's voice (one mark, one meaning: the
                    # wheel speaks). 舵 is reserved for the helm line you type
                    # into; KAJI is the wordmark in the header. See
                    # docs/design/KAJI_EMBER.md "Brand marks".
                    pre = _c("◉   ", SUN, color) if j == 0 else "    "
                    out.append("  " + pre + _c(line, INK, color))
        out.append("")

    if not ordered:
        # An empty fleet must NOT swallow the conversation — the mate's
        # explanation of a failed spawn is exactly what the captain needs.
        if transcript:
            emit_transcript()
        else:
            out.append(_c("  No active sessions.", MUTE, color))
            out.append(_c("  Spawn a worker (Cmd+Shift+K), or just ask for one below.", DIM, color))
            out.append("")
        return "\n".join(out)

    # Session list — one line per worker (v3: no event sub-lines).
    for i, s in enumerate(ordered):
        glyph, col, label = status_style(s.get("state"))
        state = (s.get("state") or "").lower()
        marker = _c("▌", SUN, color) if i == sel else " "
        dot = _c(glyph, col, color)
        proj = "%s · %s" % (s.get("harness", "?"), s.get("project", "?"))
        rt = fmt_runtime(s.get("runtime_secs"))
        ctx = int(s.get("context_pct") or 0)
        meta_txt = "%s %s%s" % (label, rt, (" · ctx %d%%" % ctx) if ctx else "")
        meta_col = SUN if state == "waiting" else (ASH if state in ("idle", "done") else MUTE)
        body_col = ASH if state in ("idle", "done") else INK
        # Name left, meta pinned right — same column rhythm as the phone list.
        ptxt = _clip(proj, max(16, width - 6 - len(meta_txt) - 4))
        gap = max(2, width - 6 - len(ptxt) - len(meta_txt) - 2)
        line = "  %s %s %s%s%s" % (marker, dot, _c(ptxt, body_col, color),
                                   " " * gap, _c(meta_txt, meta_col, color))
        if i == sel:
            line = _c(line, BOLD, color)
        out.append(line)
    out.append("")

    # The conversation — the captain and the First Mate, newest last. This is
    # the body of the screen now: the old per-pane event feed and compass-dot
    # footer are gone (the fleet list above already carries one dot per ship,
    # and history is something you ASK the mate for, not ambient noise).
    if transcript:
        emit_transcript()
    else:
        cur = ordered[sel]
        spawn = next((e.get("task") for e in reversed(pane_events(events, cur.get("pane_id")))
                      if e.get("ev") == "spawn" and e.get("task")), "")
        if spawn:
            out.append(_c("  ▸ " + _clip(str(spawn), width - 6), MUTE, color))
            out.append("")
    return "\n".join(out)


def _wrap(text: str, width: int) -> List[str]:
    import textwrap
    width = max(20, width)
    lines = []
    for raw in str(text).splitlines() or [""]:
        # word-aware for prose with spaces; still hard-cuts long unspaced
        # runs (CJK, paths) so nothing ever overflows.
        lines.extend(textwrap.wrap(raw, width, break_long_words=True,
                                   break_on_hyphens=False) or [""])
    return lines[:6]


# ── data acquisition (I/O) ────────────────────────────────────────────────────

def _helm_brain_argv() -> Optional[List[str]]:
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, "..", "kaji-brain", "kaji-brain")
    if os.path.exists(candidate):
        return [candidate]
    found = __import__("shutil").which("kaji-brain")
    return [found] if found else None


def _run_json(argv: List[str], default):
    try:
        out = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=10).stdout.decode("utf-8", "replace")
        return json.loads(out) if out.strip() else default
    except Exception:
        return default


def nl_plan(order: str) -> Dict:
    """One captain sentence → structured fleet action via `kaji-brain plan`."""
    hb = _helm_brain_argv()
    if not hb:
        return {"action": "none", "why": "kaji-brain not found"}
    try:
        out = subprocess.run(hb + ["plan", order], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=90)
        return json.loads(out.stdout.decode("utf-8", "replace").strip() or "{}")
    except Exception as e:
        return {"action": "none", "why": str(e)}


def fetch_live() -> Tuple[List[Dict], List[Dict], Dict]:
    """Pull sessions + events + quota from kaji-brain. Empty if unavailable."""
    hb = _helm_brain_argv()
    if not hb:
        return [], [], {}
    sessions = _run_json(hb + ["sessions"], [])
    events = _run_json(hb + ["timeline", "--json"], [])
    quota = _run_json(hb + ["quota"], {})
    return (sessions if isinstance(sessions, list) else [],
            events if isinstance(events, list) else [],
            quota if isinstance(quota, dict) else {})


def fetch_http(base: str, token: Optional[str] = None) -> Tuple[List[Dict], List[Dict], Dict]:
    """Pull sessions + events from a kaji-brain HTTP service (the spine).

    This is the same shape the phone app uses: the cockpit is just one client
    of `kaji-brain serve`. Empty lists if the server is unreachable.
    """
    import urllib.request

    def _get(path):
        req = urllib.request.Request(base.rstrip("/") + path)
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return None

    sessions = _get("/api/sessions")
    events = _get("/api/timeline")
    state = _get("/api/state") or {}
    quota = {}
    if isinstance(state, dict):
        toks = state.get("quota") or {}
        lims = state.get("limits") or {}
        for name in set(list(toks) + list(lims)):
            quota[name] = {"tokens_today": toks.get(name, 0)}
            if name in lims:
                quota[name]["limits"] = lims[name]
    return (sessions if isinstance(sessions, list) else [],
            events if isinstance(events, list) else [],
            quota)


def demo_data() -> Tuple[List[Dict], List[Dict], Dict]:
    """Built-in fake fleet so the layout can be previewed with no Kaji running."""
    sessions = [
        {"pane_id": 2, "harness": "claude", "project": "kaji", "state": "waiting",
         "runtime_secs": 1840, "tokens_today": 21000, "context_pct": 21},
        {"pane_id": 4, "harness": "kiro", "project": "mira", "state": "working",
         "runtime_secs": 320, "tokens_today": 8000, "context_pct": 8},
        {"pane_id": 5, "harness": "opencode", "project": "doabit", "state": "working",
         "runtime_secs": 95, "tokens_today": 0, "context_pct": 3},
        {"pane_id": 3, "harness": "claude", "project": "wu", "state": "done",
         "runtime_secs": 5400, "tokens_today": 44000},
    ]
    events = [
        {"ts": 1781000000, "pane": 2, "ev": "spawn", "harness": "claude", "cwd": "kaji", "task": "port upstream #452"},
        {"ts": 1781000100, "pane": 2, "ev": "state", "to": "working"},
        {"ts": 1781000600, "pane": 2, "ev": "dispatch", "text": "run the full test suite"},
        {"ts": 1781001200, "pane": 2, "ev": "state", "to": "waiting"},
        {"ts": 1781000300, "pane": 4, "ev": "spawn", "harness": "kiro", "cwd": "mira", "task": "draft release notes"},
        {"ts": 1781001100, "pane": 4, "ev": "state", "to": "working"},
        {"ts": 1781001500, "pane": 5, "ev": "spawn", "harness": "opencode", "cwd": "doabit", "task": "fix newsletter route"},
        {"ts": 1780990000, "pane": 3, "ev": "spawn", "harness": "claude", "cwd": "wu", "task": "letter view polish"},
        {"ts": 1780995400, "pane": 3, "ev": "state", "to": "done"},
    ]
    quota = {"claude": {"tokens_today": 73000},
             "codex": {"tokens_today": 50800,
                       "limits": {"secondary_used_percent": 38.0, "plan": "plus"}}}
    return sessions, events, quota


# ── actions (writes go through kaji-brain / serve, same as every client) ─────

def send_text(server: str, token: Optional[str], pane_id, text: str) -> Tuple[bool, str]:
    """Send an instruction to a worker. Returns (ok, errmsg)."""
    if server:
        return _post_http(server, token, "/api/send",
                          {"pane_id": pane_id, "text": text})
    hb = _helm_brain_argv()
    if not hb:
        return False, "kaji-brain not found"
    try:
        p = subprocess.run(hb + ["send", str(pane_id), text],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return p.returncode == 0, p.stderr.decode("utf-8", "replace").strip()
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def spawn_worker(server: str, token: Optional[str], harness: str, cwd: str,
                 task: str = "") -> Tuple[bool, str]:
    """Spawn a new worker. Returns (ok, errmsg)."""
    if server:
        body = {"harness": harness, "cwd": cwd}
        if task:
            body["task"] = task
        return _post_http(server, token, "/api/spawn", body)
    hb = _helm_brain_argv()
    if not hb:
        return False, "kaji-brain not found"
    argv = hb + ["spawn", harness, cwd] + ([task] if task else [])
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=30)
        return p.returncode == 0, p.stderr.decode("utf-8", "replace").strip()
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _post_http(base: str, token: Optional[str], path: str, body: Dict) -> Tuple[bool, str]:
    import urllib.request
    import urllib.error
    req = urllib.request.Request(base.rstrip("/") + path,
                                 data=json.dumps(body).encode("utf-8"),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
            return True, ""
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error", "")
        except Exception:
            msg = ""
        return False, msg or ("HTTP %d" % e.code)
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# ── interactive loop ──────────────────────────────────────────────────────────

def parse_key(buf: bytes) -> str:
    """Map raw stdin bytes to an action. Pure → unit-testable."""
    if not buf:
        return "none"
    if buf in (b"q", b"Q", b"\x03"):          # q / Ctrl-C
        return "quit"
    if buf in (b"\x1b[A", b"k"):
        return "up"
    if buf in (b"\x1b[B", b"j"):
        return "down"
    if buf in (b"\r", b"\n"):
        return "send"
    if buf in (b"s", b"S"):
        return "spawn"
    if buf in (b"r", b"R"):
        return "refresh"
    if buf in (b"i", b"I", b"/"):
        return "helm"
    return "none"


HINTS = "⏎ order · empty ⏎ reply selected · ⇥ mode · ^C quit"


def _prompt(line: str) -> str:
    """Cooked-mode one-line prompt at the bottom of the screen."""
    sys.stdout.write("\033[?25h")  # show cursor
    sys.stdout.flush()
    try:
        return input(line).strip()
    except (EOFError, KeyboardInterrupt):
        return ""
    finally:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()


def _choose(fd, options, default=0):
    """Inline arrow selector: ←→/↑↓ move, ⏎ pick, ESC cancel → None.
    Renders on one line (caller is on a fresh line, cbreak mode active)."""
    import select as _select
    sel = default
    while True:
        line = "   "
        for i, o in enumerate(options):
            line += ("\033[7m %s \033[0m" % o) if i == sel else ("  %s  " % o)
        sys.stdout.write("\r\033[K" + line)
        sys.stdout.flush()
        r, _, _ = _select.select([sys.stdin], [], [], 30.0)
        if not r:
            continue
        buf = os.read(fd, 8)
        if buf in (b"\x1b[C", b"\x1b[B", b"\t", b"l"):
            sel = (sel + 1) % len(options)
        elif buf in (b"\x1b[D", b"\x1b[A", b"h"):
            sel = (sel - 1) % len(options)
        elif buf in (b"\r", b"\n"):
            sys.stdout.write("\n")
            return sel
        elif buf in (b"\x1b", b"\x03", b"q", b"n", b"N"):
            sys.stdout.write("\n")
            return None


def _get_engine(box):
    """Lazy-load the conversational engine (engine.py, same dir). One try."""
    if not box["tried"]:
        box["tried"] = True
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import engine as _e
            box["mod"], box["eng"] = _e, _e.Engine()
        except Exception:
            pass
    return box["mod"], box["eng"]


def _engine_turn(em, eng, order, mode, fd, old_attrs):
    """舵 order → engine.turn() multi-step loop. The engine reads the fleet
    itself; DANGEROUS actions surface here for the confirm gate (or run
    straight through in auto mode). Returns flash."""
    import termios
    import tty
    sys.stdout.write("\n   …\n")
    sys.stdout.flush()
    done = 0
    for ev in eng.turn(order):
        if ev[0] == "say":
            for ln in _wrap(ev[1], 70):
                sys.stdout.write("   %s\n" % ln)
            sys.stdout.flush()
            continue
        _, name, act = ev
        sys.stdout.write(" → %s %s\n" % (name, em._brief(name, act)))
        sys.stdout.flush()
        if mode == "confirm":
            pick = _choose(fd, ["run", "cancel", "edit"])
            if pick is None or pick == 1:
                eng.feed(False, "captain cancelled")
                continue
            if pick == 2:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
                edited = _prompt("   edit: ")
                tty.setcbreak(fd)
                if not edited:
                    eng.feed(False, "captain cancelled")
                    continue
                act["text" if name == "send_to_worker" else "task"] = edited
        ok, res = em.execute_action(name, act)
        eng.feed(ok, res)
        done += 1
    return ("✓ %d action(s)" % done) if done else ""


def _dispatch(order, ordered, selected, mode, args, fd, old_attrs):
    """舵 order → plan → (confirm via arrows | auto) → execute. Returns flash."""
    import termios
    import tty
    sys.stdout.write("\n   …\n")
    sys.stdout.flush()
    plan = nl_plan(order)
    act = plan.get("action")
    if act == "send":
        line = "→ reply pane %s: %s" % (plan.get("pane_id"), plan.get("text", ""))
    elif act == "spawn":
        line = "→ spawn %s · %s: %s" % (
            plan.get("harness"), plan.get("cwd"), plan.get("task", ""))
    else:
        return "× " + (plan.get("why") or "no plan")
    sys.stdout.write(" %s\n" % line)
    sys.stdout.flush()

    if mode == "confirm":
        pick = _choose(fd, ["run", "cancel", "edit"])
        if pick is None or pick == 1:
            return "cancelled"
        if pick == 2:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
            edited = _prompt("   edit: ")
            tty.setcbreak(fd)
            if not edited:
                return "cancelled"
            if act == "send":
                plan["text"] = edited
            else:
                plan["task"] = edited

    if act == "send":
        ok, err = send_text(args.server, args.token or None,
                            plan.get("pane_id"), plan.get("text", ""))
    else:
        ok, err = spawn_worker(args.server, args.token or None,
                               plan.get("harness") or "claude",
                               plan.get("cwd") or "",
                               plan.get("task") or "")
    return "done ✓" if ok else ("failed: " + (err or "?"))


def interactive(args) -> int:
    """Full-screen loop: 2s auto-refresh, arrow selection, send + spawn."""
    import select as _select
    import termios
    import tty

    def fetch():
        if args.demo:
            return demo_data()
        if args.server:
            return fetch_http(args.server, args.token or None)
        return fetch_live()

    import threading

    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)
    sys.stdout.write("\033[?1049h\033[?25l")  # alt screen, hide cursor
    selected = 0
    flash = ""

    # Data arrives in the background so the frame paints INSTANTLY and the UI
    # never freezes on a slow fetch (first quota collect can take a second+).
    box = {"data": None, "busy": False}

    def _bg():
        try:
            box["data"] = fetch()
        except Exception:
            pass
        box["busy"] = False

    def kick():
        if not box["busy"]:
            box["busy"] = True
            threading.Thread(target=_bg, daemon=True).start()

    kick()
    sessions, events, quota = [], [], {}
    loaded = False
    helm_buf = [""]                  # the 舵 line, typed directly
    mode = ["confirm"]               # confirm ⇄ auto (Tab / Cmd+Shift+A)
    eng_box = {"mod": None, "eng": None, "tried": False}   # lazy First Mate
    # Incremental decoder: a multibyte char split across read() boundaries
    # (fast typing, IME, paste) must not be dropped — the old per-chunk
    # decode(errors="ignore") ate half-characters ("列一下" → "列一").
    import codecs
    decoder = codecs.getincrementaldecoder("utf-8")("ignore")
    try:
        tty.setcbreak(fd)
        while True:
            if box["data"] is not None:
                sessions, events, quota = box["data"]
                box["data"] = None
                loaded = True
            ordered = sort_sessions(sessions)
            selected = max(0, min(selected, max(0, len(ordered) - 1)))
            width = args.width or (os.get_terminal_size().columns if sys.stdout.isatty() else 80)
            frame = render(sessions, events, selected=selected, width=width,
                           color=not args.no_color, quota=quota, loading=not loaded,
                           transcript=(eng_box["eng"].transcript
                                       if eng_box["eng"] else None))
            tag = ("auto" if mode[0] == "auto" else "confirm")
            if not args.no_color:
                tag = (SUN if mode[0] == "auto" else MUTE) + tag + RESET
            hint = (ASH + (flash or HINTS) + RESET) if not args.no_color else (flash or HINTS)
            rud = (SUN + "舵" + RESET) if not args.no_color else "舵"
            cur = (INK + helm_buf[0] + RESET + (SUN + "▌" + RESET)) if not args.no_color \
                  else (helm_buf[0] + "▌")
            rule = "  " + "─" * (width - 4)
            if not args.no_color:
                rule = ASH + rule + RESET
            footer = "%s\n  %s  %s   ·%s\n  %s" % (rule, rud, cur, tag, hint)
            sys.stdout.write("\033[2J\033[H" + frame + "\n" + footer + "\n")
            sys.stdout.flush()
            flash = ""

            r, _, _ = _select.select([sys.stdin], [], [], 0.25 if not loaded else 2.0)
            if not r:
                kick()              # idle tick → refresh in the background
                continue
            buf = os.read(fd, 8)

            # ── typing-first: anything printable goes into the 舵 buffer ──
            if buf == b"\x1b[A":
                selected -= 1
                continue
            if buf == b"\x1b[B":
                selected += 1
                continue
            if buf == b"\t":          # mode toggle (also Cmd+Shift+A via kaku)
                mode[0] = "auto" if mode[0] == "confirm" else "confirm"
                flash = "mode: " + mode[0]
                continue
            if buf[:1] == b"\x1b":    # ESC (any non-arrow escape) clears
                helm_buf[0] = ""
                continue
            if buf == b"\x15":        # Ctrl-U: clear line (readline habit)
                helm_buf[0] = ""
                continue
            if buf in (b"\x7f", b"\x08"):
                helm_buf[0] = helm_buf[0][:-1]
                continue
            if buf == b"\x03":        # Ctrl-C always quits
                return 0
            if buf in (b"\r", b"\n"):
                order = helm_buf[0].strip()
                helm_buf[0] = ""
                if order:
                    em, eng = _get_engine(eng_box)
                    if eng:
                        # Repaint once with the buffer cleared so the turn's
                        # progress lines land under a frame that shows the
                        # order in the transcript, not stale in the helm line.
                        eng.transcript.append(("you", order))
                        frame = render(sessions, events, selected=selected,
                                       width=width, color=not args.no_color,
                                       quota=quota, loading=False,
                                       transcript=eng.transcript)
                        sys.stdout.write("\033[2J\033[H" + frame + "\n")
                        sys.stdout.flush()
                        eng.transcript.pop()   # turn() appends it itself
                        flash = _engine_turn(em, eng, order, mode[0], fd, old_attrs)
                    else:   # engine unavailable → old one-shot planner path
                        flash = _dispatch(order, ordered, selected, mode[0],
                                          args, fd, old_attrs)
                    kick()
                elif ordered:
                    # empty ⏎ → classic reply-to-selected
                    target = ordered[selected]
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
                    text = _prompt("\n → %s·%s (pane %s): " % (
                        target.get("harness"), target.get("project"), target.get("pane_id")))
                    tty.setcbreak(fd)
                    if text:
                        ok, err = send_text(args.server, args.token or None,
                                            target.get("pane_id"), text)
                        flash = "sent ✓" if ok else ("send failed: " + (err or "?"))
                    kick()
                continue
            # NO single-letter commands: typing is the interface. Letters are
            # text (an order may start with s/r/q — see the live misfire where
            # "spawn a claude…" opened the manual spawn form). Quit = Ctrl-C,
            # select = arrows, refresh = the 2s tick.
            # text: append to the 舵 buffer. The incremental decoder holds a
            # partial multibyte sequence until its tail arrives in the next read.
            chunk = decoder.decode(buf)
            helm_buf[0] += "".join(c for c in chunk if c.isprintable())
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
        sys.stdout.write("\033[?1049l\033[?25h")
        sys.stdout.flush()


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="render-only Brain cockpit (Cmd+1)")
    ap.add_argument("--demo", action="store_true", help="render built-in sample fleet")
    ap.add_argument("--once", action="store_true", help="render one frame and exit")
    ap.add_argument("--selected", type=int, default=0, help="selected row index")
    ap.add_argument("--width", type=int, default=0, help="override terminal width")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI color")
    ap.add_argument("--server", default="", help="fetch from a kaji-brain serve URL (e.g. http://127.0.0.1:8765) instead of shelling out")
    ap.add_argument("--token", default="", help="bearer token for --server")
    args = ap.parse_args(argv)

    if args.demo:
        sessions, events, quota = demo_data()
    elif args.server:
        sessions, events, quota = fetch_http(args.server, args.token or None)
    else:
        sessions, events, quota = fetch_live()
    width = args.width or (os.get_terminal_size().columns if sys.stdout.isatty() else 80)
    color = not args.no_color and (args.demo or sys.stdout.isatty())

    frame = render(sessions, events, selected=args.selected, width=width,
                   color=color, quota=quota)
    if args.once or not sys.stdout.isatty() or not sys.stdin.isatty():
        print(frame)
        return 0
    try:
        return interactive(args)
    except KeyboardInterrupt:
        # cbreak keeps ISIG on, so ^C lands as SIGINT wherever we are
        # (helm line, selector, mid-turn). It means quit — quietly.
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
