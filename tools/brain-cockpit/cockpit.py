#!/usr/bin/env python3
"""brain-cockpit — the render-only Brain (Cmd+1).

A pure-visualization cockpit for the fleet: brand + session list + status dots +
"most-neglected first" ordering + the selected session's history. NO model —
see docs/BRAIN_DESIGN.md § "Visualization first". It reads the substrate
(`helm-brain sessions` for the live snapshot, `helm-brain timeline --json` for
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


GHOST = _fg(0xD9, 0x77, 0x57)   # Anthropic-ish warm orange — brand
INK = _fg(0xE8, 0xE0, 0xD4)     # warm paper-white text
MUTE = _fg(0x9A, 0x8F, 0x80)    # muted label
SEL = _fg(0xC8, 0xA8, 0xFF)     # Kaji purple — selection accent

# state -> (glyph, color, label). Order in this dict is the display priority
# (most-neglected first): waiting on top, done/idle at the bottom.
_STATE_STYLE = {
    "waiting":    ("●", _fg(0xE8, 0xB3, 0x39), "waiting"),   # amber: needs you
    "working":    ("●", _fg(0x4F, 0xC8, 0xA8), "working"),   # teal
    "error":      ("●", _fg(0xE0, 0x6C, 0x6C), "error"),     # red
    "background": ("●", _fg(0x6C, 0x9C, 0xE0), "background"), # blue
    "idle":       ("○", MUTE, "idle"),
    "done":       ("○", DIM,  "done"),
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


def _clip(s: str, n: int) -> str:
    """Clip a plain (un-colored) string to n columns with an ellipsis."""
    return s if len(s) <= n else (s[: max(0, n - 1)] + "…")


# ── rendering (pure) ──────────────────────────────────────────────────────────

def _c(text: str, color: str, color_on: bool) -> str:
    return (color + text + RESET) if color_on else text


def render(sessions: List[Dict], events: List[Dict], selected: int = 0,
           width: int = 80, color: bool = True) -> str:
    """Render one cockpit frame as a string. Pure — no I/O, no globals."""
    width = max(40, width)
    ordered = sort_sessions(sessions)
    n = len(ordered)
    sel = min(max(0, selected), n - 1) if n else 0
    out: List[str] = []

    # Header — brand.
    out.append(_c("  ᗣ  ", GHOST, color) + _c("KAJI", BOLD, color) +
               _c("  ·  you steer · agents execute", MUTE, color))
    out.append(_c("  the fleet — most-neglected first", DIM, color))
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

    if not ordered:
        out.append(_c("  No active sessions.", MUTE, color))
        out.append(_c("  Spawn a worker (Cmd+Shift+K) and it shows up here.", DIM, color))
        out.append("")
        out.append(compass())
        return "\n".join(out)

    # Session list.
    for i, s in enumerate(ordered):
        glyph, col, label = status_style(s.get("state"))
        marker = _c("▸", SEL, color) if i == sel else " "
        dot = _c(glyph, col, color)
        proj = "%s/%s" % (s.get("harness", "?"), s.get("project", "?"))
        rt = fmt_runtime(s.get("runtime_secs"))
        head = "%s %s %s" % (marker, dot, _clip(proj, 26).ljust(26))
        meta = _c("%-10s %5s" % (label, rt), col if i == sel else MUTE, color)
        line = "  %s  %s" % (head, meta)
        if i == sel:
            line = _c(line, BOLD, color)
        out.append(line)
        act = last_activity(events, s.get("pane_id"))
        if act:
            out.append(_c("        %s" % _clip(act, width - 10), DIM, color))
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
    candidate = os.path.join(here, "..", "helm-brain", "helm-brain")
    if os.path.exists(candidate):
        return [candidate]
    found = __import__("shutil").which("helm-brain")
    return [found] if found else None


def _run_json(argv: List[str], default):
    try:
        out = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=10).stdout.decode("utf-8", "replace")
        return json.loads(out) if out.strip() else default
    except Exception:
        return default


def fetch_live() -> Tuple[List[Dict], List[Dict]]:
    """Pull sessions + events from helm-brain. Empty lists if unavailable."""
    hb = _helm_brain_argv()
    if not hb:
        return [], []
    sessions = _run_json(hb + ["sessions"], [])
    events = _run_json(hb + ["timeline", "--json"], [])
    return (sessions if isinstance(sessions, list) else [],
            events if isinstance(events, list) else [])


def fetch_http(base: str, token: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
    """Pull sessions + events from a helm-brain HTTP service (the spine).

    This is the same shape the phone app uses: the cockpit is just one client
    of `helm-brain serve`. Empty lists if the server is unreachable.
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
    return (sessions if isinstance(sessions, list) else [],
            events if isinstance(events, list) else [])


def demo_data() -> Tuple[List[Dict], List[Dict]]:
    """Built-in fake fleet so the layout can be previewed with no Kaji running."""
    sessions = [
        {"pane_id": 2, "harness": "claude", "project": "kaji", "state": "waiting",
         "runtime_secs": 1840, "tokens_today": 21000},
        {"pane_id": 4, "harness": "kiro", "project": "mira", "state": "working",
         "runtime_secs": 320, "tokens_today": 8000},
        {"pane_id": 5, "harness": "opencode", "project": "doabit", "state": "working",
         "runtime_secs": 95, "tokens_today": 0},
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
    return sessions, events


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="render-only Brain cockpit (Cmd+1)")
    ap.add_argument("--demo", action="store_true", help="render built-in sample fleet")
    ap.add_argument("--once", action="store_true", help="render one frame and exit")
    ap.add_argument("--selected", type=int, default=0, help="selected row index")
    ap.add_argument("--width", type=int, default=0, help="override terminal width")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI color")
    ap.add_argument("--server", default="", help="fetch from a helm-brain serve URL (e.g. http://127.0.0.1:8765) instead of shelling out")
    ap.add_argument("--token", default="", help="bearer token for --server")
    args = ap.parse_args(argv)

    if args.demo:
        sessions, events = demo_data()
    elif args.server:
        sessions, events = fetch_http(args.server, args.token or None)
    else:
        sessions, events = fetch_live()
    width = args.width or (os.get_terminal_size().columns if sys.stdout.isatty() else 80)
    color = not args.no_color and (args.demo or sys.stdout.isatty())

    frame = render(sessions, events, selected=args.selected, width=width, color=color)
    if args.once or not sys.stdout.isatty():
        print(frame)
        return 0
    # Minimal interactive loop placeholder: full-screen curses with arrow-key
    # selection + a "send to selected" line lands next (and needs a real tty /
    # macOS run). For now, --once / non-tty renders a single frame.
    print(frame)
    print("\n(interactive loop TODO — see docs/BRAIN_DESIGN.md § cockpit)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
