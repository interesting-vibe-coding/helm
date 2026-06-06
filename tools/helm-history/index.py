#!/usr/bin/env python3
"""Helm session history indexer — scans Claude Code, Kiro, and opencode."""
import json, os, glob, re, argparse
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
            "message_count": 0,
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


def build_index():
    sessions = scan_claude_code() + scan_kiro() + scan_opencode()
    OUT.write_text(json.dumps(sessions, indent=2))
    return sessions


def cmd_list(sessions):
    harnesses = ["claude-code", "kiro", "opencode"]
    print(f"{'harness':<14} {'sessions':>8}  {'last_active'}")
    print("-" * 36)
    for h in harnesses:
        subset = [s for s in sessions if s["harness"] == h]
        print(f"{h:<14} {len(subset):>8}  {last_date(subset)}")
    print(f"\nIndex written → {OUT}  ({len(sessions)} total sessions)")


def cmd_search(sessions, query):
    q = query.lower()
    results = [s for s in sessions if q in s.get("title", "").lower() or q in s.get("cwd", "").lower()]
    if not results:
        print(f"No sessions matching '{query}'")
        return
    print(f"{'harness':<14} {'session_id':<40} {'title'}")
    print("-" * 80)
    for s in results:
        print(f"{s['harness']:<14} {s['session_id']:<40} {s['title']}")
    print(f"\n{len(results)} result(s)")


def cmd_recent(sessions):
    sorted_s = sorted(
        [s for s in sessions if s.get("last_message_at")],
        key=lambda s: s["last_message_at"],
        reverse=True
    )[:10]
    print(f"{'harness':<14} {'last_active':<26} {'title'}")
    print("-" * 80)
    for s in sorted_s:
        ts = s["last_message_at"][:19].replace("T", " ")
        print(f"{s['harness']:<14} {ts:<26} {s['title'][:38]}")


def cmd_show(session_id):
    # Find kiro session .jsonl file
    pattern = str(HOME / ".kiro/sessions/cli" / f"{session_id}.jsonl")
    matches = glob.glob(pattern)
    # Also try partial match
    if not matches:
        matches = glob.glob(str(HOME / ".kiro/sessions/cli/*.jsonl"))
        matches = [m for m in matches if session_id in m]
    if not matches:
        print(f"No kiro .jsonl found for session_id '{session_id}'")
        return
    path = matches[0]
    try:
        lines = [json.loads(l) for l in open(path) if l.strip()]
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return
    msgs = [l for l in lines if l.get("type") in ("user", "assistant")][:5]
    print(f"Session: {session_id}  ({len(msgs)} of first 5 messages shown)\n")
    for i, m in enumerate(msgs, 1):
        role = m.get("type", "?")
        ts = m.get("timestamp", "")[:19]
        content = m.get("message", {})
        if isinstance(content, dict):
            text = content.get("content", "")
            if isinstance(text, list):
                text = " ".join(c.get("text", "") for c in text if isinstance(c, dict))
        else:
            text = str(content)
        print(f"[{i}] {role} @ {ts}")
        print(f"    {str(text)[:200]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Helm session history indexer")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list", help="Show summary table (default)")
    p_search = sub.add_parser("search", help="Search session titles")
    p_search.add_argument("query")
    sub.add_parser("recent", help="Last 10 sessions sorted by last_active")
    p_show = sub.add_parser("show", help="Show first 5 messages from a kiro session")
    p_show.add_argument("session_id")

    args = parser.parse_args()
    sessions = build_index()

    if args.cmd == "search":
        cmd_search(sessions, args.query)
    elif args.cmd == "recent":
        cmd_recent(sessions)
    elif args.cmd == "show":
        cmd_show(args.session_id)
    else:
        cmd_list(sessions)


if __name__ == "__main__":
    main()
