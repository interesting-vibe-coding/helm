#!/usr/bin/env python3
"""helm-watch: live agent session monitor."""

import json
import os
import sys
import time
import select
import termios
import tty
from pathlib import Path
from datetime import datetime

RUNTIME_FILE = Path.home() / ".helm" / "sessions" / "runtime.json"

SYMLINKS = {
    "claude": Path.home() / ".claude",
    "opencode": Path.home() / ".config" / "opencode",
    "codex": Path.home() / ".codex",
}

HELM_APP = Path("/Applications/Helm.app")

STATE_ICONS = {
    "working": "🔵",
    "waiting": "🟠",
    "idle": "⚪",
    "error": "🔴",
}

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def fmt_runtime(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def shorten_path(p: str) -> str:
    home = str(Path.home())
    if p.startswith(home):
        p = "~" + p[len(home):]
    return p

def load_sessions():
    if not RUNTIME_FILE.exists():
        return []
    try:
        data = json.loads(RUNTIME_FILE.read_text())
        return data if isinstance(data, list) else data.get("sessions", [])
    except Exception:
        return []

def check_symlinks():
    results = {}
    for name, path in SYMLINKS.items():
        results[name] = path.exists() or path.is_symlink()
    return results

def render():
    sessions = load_sessions()
    symlinks = check_symlinks()
    helm_ok = HELM_APP.exists()
    now = time.time()

    lines = []
    lines.append("Helm Watch — live (press q to quit)")
    lines.append("=" * 52)
    lines.append(f"{'SESSION':<22} {'HARNESS':<12} {'RUNTIME':<9} {'STATE'}")
    lines.append("-" * 52)

    if sessions:
        for s in sessions:
            path = shorten_path(s.get("cwd", s.get("path", "unknown")))
            harness = s.get("harness", s.get("type", "unknown"))
            state = s.get("state", "idle").lower()
            started = s.get("started_at", now)
            runtime = fmt_runtime(now - started)
            icon = STATE_ICONS.get(state, "⚪")
            lines.append(f"ws: {path:<18} {harness:<12} {runtime:<9} {icon} {state}")
    else:
        lines.append("  (no active sessions — start an agent or check ~/.helm/)")

    lines.append("")

    sym_parts = []
    for name, ok in symlinks.items():
        sym_parts.append(("✓ " if ok else "✗ ") + name)
    lines.append(f"SYMLINKS: {' '.join(sym_parts)}")
    lines.append(f"BUILD:    /Applications/Helm.app {'✓' if helm_ok else '✗ (not found)'}")
    lines.append("")
    lines.append("Press q to quit")

    clear()
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()

def kbhit(timeout=0):
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    return bool(r)

def main():
    if not sys.stdin.isatty():
        # Non-interactive: render once and exit
        render()
        return

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        while True:
            render()
            deadline = time.time() + 2.0
            while time.time() < deadline:
                remaining = deadline - time.time()
                if kbhit(min(remaining, 0.1)):
                    ch = sys.stdin.read(1)
                    if ch.lower() == "q":
                        clear()
                        return
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    main()
