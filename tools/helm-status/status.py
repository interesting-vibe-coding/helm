#!/usr/bin/env python3
"""Helm unified status dashboard."""
import json, os, sys
from pathlib import Path
from datetime import datetime, date

HOME = Path.home()

def section(title):
    print(f"\n{title}")

def check_symlink(path, target):
    p = Path(path).expanduser()
    t = Path(target).expanduser()
    if p.is_symlink():
        resolved = p.resolve()
        mark = "✓" if resolved == t.resolve() else f"→ {p.readlink()}"
    elif p.exists():
        mark = "(not a symlink)"
    else:
        mark = "✗ missing"
    print(f"  {path} -> {target}  {mark}")

def sessions_summary():
    idx = HOME / ".helm" / "sessions" / "index.json"
    if not idx.exists():
        print("  (no index.json found)")
        return
    with open(idx) as f:
        sessions = json.load(f)
    counts = {}
    last_dates = {}
    for s in sessions:
        h = s.get("harness", "unknown")
        counts[h] = counts.get(h, 0) + 1
        ts = s.get("last_message_at") or s.get("started_at", "")
        d = ts[:10] if ts else ""
        if d > last_dates.get(h, ""):
            last_dates[h] = d
    for h in sorted(counts):
        n = counts[h]
        ld = last_dates.get(h, "?")
        print(f"  {h:<16} {n:>4} sessions  last: {ld}")

def claude_usage():
    # Try to find cost info in ~/.claude — no standard file, report N/A
    stats_file = HOME / ".claude" / "stats.json"
    if stats_file.exists():
        with open(stats_file) as f:
            d = json.load(f)
        today = str(date.today())
        cost = d.get(today, {}).get("cost_usd")
        tokens = d.get(today, {}).get("tokens")
        print(f"  Cost today:   ${cost:.4f}" if cost else "  Cost today:   N/A")
        print(f"  Tokens today: ~{tokens//1000}k" if tokens else "  Tokens today: N/A")
    else:
        print("  Cost today:   N/A")
        print("  Tokens today: N/A")

def helm_build():
    app = Path("/Applications/Helm.app")
    lua = HOME / "workspace" / "helm-terminal" / "assets" / "macos" / "Helm.app" / "Contents" / "Resources" / "kaku.lua"
    mark = "exists ✓" if app.exists() else "not found ✗"
    print(f"  /Applications/Helm.app  {mark}")
    if lua.exists():
        lines = sum(1 for _ in open(lua))
        print(f"  kaku.lua lines: {lines}")
    else:
        print("  kaku.lua: not found")

now = datetime.now().strftime("%Y-%m-%d %H:%M")
print(f"Helm Status — {now}")
print("=" * 32)

section("ACTIVE SESSIONS (from ~/.helm/sessions/index.json)")
sessions_summary()

section("CLAUDE USAGE (from ~/.claude/)")
claude_usage()

section("SYMLINKS")
check_symlink("~/.claude/CLAUDE.md", "~/.kiro/AGENTS.md")
check_symlink("~/.config/opencode/AGENTS.md", "~/.kiro/AGENTS.md")
check_symlink("~/.codex/AGENTS.md", "~/.kiro/AGENTS.md")

section("HELM BUILD")
helm_build()
