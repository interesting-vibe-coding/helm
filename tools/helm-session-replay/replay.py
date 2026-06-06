#!/usr/bin/env python3
"""helm-session-replay: Export a past session as context for a new agent."""
import argparse, json, os, subprocess, sys
from pathlib import Path
from datetime import datetime

INDEX = Path.home() / ".helm/sessions/index.json"
KIRO_DIR = Path.home() / ".kiro/sessions/cli"


def load_index():
    if not INDEX.exists():
        return []
    with open(INDEX) as f:
        return json.load(f)


def find_session(sessions, query):
    # Exact match first
    for s in sessions:
        if s.get("session_id") == query:
            return s
    # Fuzzy title match
    q = query.lower()
    for s in sessions:
        if q in s.get("title", "").lower() or q in s.get("session_id", "").lower():
            return s
    return None


def extract_kiro_messages(session_id):
    jsonl = KIRO_DIR / f"{session_id}.jsonl"
    if not jsonl.exists():
        return []
    messages = []
    with open(jsonl) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Kiro format: {version, kind, data}; kind="Prompt" = user message
                if obj.get("kind") == "Prompt":
                    content = obj.get("data", {}).get("content", [])
                    if isinstance(content, list):
                        text = " ".join(c.get("data", "") for c in content if c.get("kind") == "text")
                    else:
                        text = str(content)
                    if text.strip():
                        messages.append(text.strip())
            except json.JSONDecodeError:
                continue
    return messages


def format_summary(session, messages):
    sid = session.get("session_id", "unknown")
    harness = session.get("harness", "unknown")
    title = session.get("title", sid)
    started = session.get("started_at", "")
    date = started[:10] if started else "unknown"
    count = session.get("message_count", len(messages))

    # First 2 and last 2 user messages (deduplicated)
    if len(messages) <= 4:
        key_msgs = messages
    else:
        seen = set()
        key_msgs = []
        for m in messages[:2] + messages[-2:]:
            snippet = m[:120]
            if snippet not in seen:
                seen.add(snippet)
                key_msgs.append(snippet)

    topics = "\n".join(f"- {m[:120]}{'...' if len(m) > 120 else ''}" for m in key_msgs) or "- (no messages extracted)"

    return f"""=== Session Context: {title} ===
Harness: {harness} | Date: {date} | Messages: {count}

Key topics discussed:
{topics}

Session ID: {sid}

Paste this at the start of a new session to give the agent context."""


def main():
    parser = argparse.ArgumentParser(description="Export past session as agent context")
    parser.add_argument("session_id", help="Session ID or fuzzy title")
    parser.add_argument("--harness", choices=["kiro", "claude-code", "opencode"], default=None)
    args = parser.parse_args()

    sessions = load_index()
    if not sessions:
        print("No sessions found in ~/.helm/sessions/index.json", file=sys.stderr)
        sys.exit(1)

    session = find_session(sessions, args.session_id)
    if not session:
        print(f"Session not found: {args.session_id}", file=sys.stderr)
        print("Available sessions:")
        for s in sessions[-5:]:
            print(f"  {s['session_id'][:8]}... | {s.get('harness')} | {s.get('title')} | {s.get('started_at','')[:10]}")
        sys.exit(1)

    harness = args.harness or session.get("harness", "")
    messages = []
    if harness == "kiro" or (not args.harness and harness == "kiro"):
        messages = extract_kiro_messages(session["session_id"])

    summary = format_summary(session, messages)
    subprocess.run(["pbcopy"], input=summary.encode(), check=True)
    print(summary)
    print("\n✓ Copied to clipboard.")


if __name__ == "__main__":
    main()
