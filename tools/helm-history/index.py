#!/usr/bin/env python3
"""Helm session history indexer — scans Claude Code, Kiro, and opencode."""
import json, os, glob, re
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()
OUT = HOME / ".helm" / "sessions" / "index.json"
OUT.parent.mkdir(parents=True, exist_ok=True)


def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def scan_claude_code():
    sessions = []
    for p in glob.glob(str(HOME / ".claude/projects/**/*.jsonl"), recursive=True):
        if "/subagents/" in p:
            continue
        try:
            lines = [json.loads(l) for l in open(p) if l.strip()]
        except Exception:
            continue
        msgs = [l for l in lines if l.get("type") in ("user", "assistant")]
        if not msgs:
            continue
        timestamps = [l["timestamp"] for l in msgs if "timestamp" in l]
        cwd = next((l.get("cwd") for l in msgs if l.get("cwd")), None)
        session_id = Path(p).stem
        # derive title from cwd: last path segment
        title = Path(cwd).name if cwd else session_id[:8]
        sessions.append({
            "session_id": session_id,
            "harness": "claude-code",
            "cwd": cwd or "",
            "title": title,
            "started_at": min(timestamps) if timestamps else "",
            "message_count": len(msgs),
            "last_message_at": max(timestamps) if timestamps else "",
        })
    return sessions


def scan_kiro():
    sessions = []
    for p in glob.glob(str(HOME / ".kiro/sessions/cli/*.json")):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        sessions.append({
            "session_id": d.get("session_id", Path(p).stem),
            "harness": "kiro",
            "cwd": d.get("cwd", ""),
            "title": (d.get("title") or "")[:80],
            "started_at": d.get("created_at", ""),
            "message_count": 0,  # not stored in session file
            "last_message_at": d.get("updated_at", ""),
        })
    return sessions


def scan_opencode():
    sessions = []
    sess_dir = HOME / ".local/share/opencode/storage/session/global"
    msg_dir  = HOME / ".local/share/opencode/storage/message"
    if not sess_dir.exists():
        return sessions
    for p in sess_dir.glob("*.json"):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        sid = d.get("id", p.stem)
        t = d.get("time", {})
        started = ms_to_iso(t["created"]) if "created" in t else ""
        updated = ms_to_iso(t["updated"]) if "updated" in t else started
        msg_count = 0
        sdir = msg_dir / sid
        if sdir.is_dir():
            msg_count = sum(1 for _ in sdir.glob("*.json"))
        sessions.append({
            "session_id": sid,
            "harness": "opencode",
            "cwd": d.get("directory", ""),
            "title": d.get("title", d.get("slug", ""))[:80],
            "started_at": started,
            "message_count": msg_count,
            "last_message_at": updated,
        })
    return sessions


def last_date(sessions):
    dates = [s["last_message_at"][:10] for s in sessions if s.get("last_message_at")]
    return max(dates) if dates else "—"


all_sessions = scan_claude_code() + scan_kiro() + scan_opencode()
OUT.write_text(json.dumps(all_sessions, indent=2))

# Summary table
harnesses = ["claude-code", "kiro", "opencode"]
print(f"{'harness':<14} {'sessions':>8}  {'last_active'}")
print("-" * 36)
for h in harnesses:
    subset = [s for s in all_sessions if s["harness"] == h]
    print(f"{h:<14} {len(subset):>8}  {last_date(subset)}")
print(f"\nIndex written → {OUT}  ({len(all_sessions)} total sessions)")
