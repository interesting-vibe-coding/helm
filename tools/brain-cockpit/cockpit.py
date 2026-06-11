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


def _hms(ts) -> str:
    import time
    try:
        return time.strftime("%H:%M", time.localtime(int(ts)))
    except Exception:
        return "--:--"


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
           quota: Optional[Dict] = None, loading: bool = False) -> str:
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
        pad = max(2, width - 8 - _visible_len(qline))
        head += " " * 2 + _c(_clip(qline, width - 10), MUTE, color)
    out.append(head)
    out.append(_c("  " + "─" * (width - 4), ASH, color))
    out.append("")

    # Footer compass: one dot per session, in display order, colored by state.
    def compass() -> str:
        if not ordered:
            return _c("  (no live sessions)", DIM, color)
        dots = []
        for i, s in enumerate(ordered):
            glyph, col, _ = status_style(s.get("state"))
            d = _c(glyph, SEL if i == sel else col, color)
            dots.append(d)
        return "  " + " ".join(dots)

    if loading and not ordered:
        out.append(_c("  …", ASH, color))
        out.append("")
        return "\n".join(out)

    if not ordered:
        out.append(_c("  No active sessions.", MUTE, color))
        out.append(_c("  Spawn a worker (Cmd+Shift+K) and it shows up here.", DIM, color))
        out.append("")
        out.append(compass())
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
        head = "%s %s %s" % (marker, dot, _c(_clip(proj, 30).ljust(30), body_col, color))
        line = "  %s  %s" % (head, _c(meta_txt, meta_col, color))
        if i == sel:
            line = _c(line, BOLD, color)
        out.append(line)
    out.append("")

    # Selected session detail — its recent history (newest first).
    cur = ordered[sel]
    out.append(_c("  ── pane %s · %s/%s ──" % (
        cur.get("pane_id"), cur.get("harness", "?"), cur.get("project", "?")),
        SEL, color))
    hist = pane_events(events, cur.get("pane_id"))
    if not hist:
        out.append(_c("    (no history yet)", DIM, color))
    else:
        for e in reversed(hist[-6:]):
            ev = e.get("ev", "?")
            if ev == "spawn":
                detail = e.get("task") or "(no task)"
            elif ev == "dispatch":
                detail = e.get("text") or ""
            elif ev == "state":
                detail = e.get("to") or "?"
            else:
                detail = ""
            row = "    %s  %-9s %s" % (_hms(e.get("ts")), ev, _clip(detail, width - 24))
            out.append(_c(row, INK, color))
    out.append("")
    out.append(compass())
    return "\n".join(out)


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
    return "none"


HINTS = "↑↓ select · ⏎ send · s spawn · r refresh · q quit"


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
                           color=not args.no_color, quota=quota, loading=not loaded)
            footer = (MUTE + (flash or HINTS) + RESET) if not args.no_color else (flash or HINTS)
            sys.stdout.write("\033[2J\033[H" + frame + "\n\n " + footer + "\n")
            sys.stdout.flush()
            flash = ""

            r, _, _ = _select.select([sys.stdin], [], [], 0.25 if not loaded else 2.0)
            if not r:
                kick()              # idle tick → refresh in the background
                continue
            buf = os.read(fd, 8)
            action = parse_key(buf)
            if action == "quit":
                return 0
            if action == "up":
                selected -= 1
            elif action == "down":
                selected += 1
            elif action == "refresh":
                kick()
            elif action == "send" and ordered:
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
            elif action == "spawn":
                termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
                harness = _prompt("\n harness [claude/kiro/opencode/codex]: ") or "claude"
                cwd = _prompt(" cwd: ")
                task = _prompt(" first task (optional): ") if cwd else ""
                tty.setcbreak(fd)
                if cwd:
                    ok, err = spawn_worker(args.server, args.token or None,
                                           harness, cwd, task)
                    flash = "spawned ✓" if ok else ("spawn failed: " + (err or "?"))
                kick()
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
    return interactive(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
