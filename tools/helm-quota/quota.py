#!/usr/bin/env python3
"""helm-quota: per-harness session/token usage summary."""
import json, os, time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
NOW = time.time()
TODAY_START = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def ago(ts: float) -> str:
    d = NOW - ts
    if d < 60: return f"{int(d)}s ago"
    if d < 3600: return f"{int(d/60)}m ago"
    if d < 86400: return f"{int(d/3600)}h ago"
    return f"{int(d/86400)}d ago"


def claude_code():
    base = HOME / ".claude" / "projects"
    if not base.exists():
        return 0, 0, None
    sessions_today, tokens, last = 0, 0, None
    session_ids_today = set()
    for jsonl in base.rglob("*.jsonl"):
        if "subagents" in str(jsonl):
            continue
        try:
            with open(jsonl) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    ts_str = d.get("timestamp")
                    if not ts_str:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        continue
                    if last is None or ts > last:
                        last = ts
                    if ts >= TODAY_START:
                        sid = d.get("sessionId")
                        if sid:
                            session_ids_today.add(sid)
                    usage = d.get("message", {}).get("usage") if isinstance(d.get("message"), dict) else None
                    if usage:
                        tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        except Exception:
            pass
    return len(session_ids_today), tokens, last


def kiro():
    base = HOME / ".kiro" / "sessions" / "cli"
    if not base.exists():
        return 0, None, None
    sessions_today, last = 0, None
    for f in base.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            ts_str = d.get("updated_at") or d.get("created_at")
            if not ts_str:
                continue
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
            if last is None or ts > last:
                last = ts
            if ts >= TODAY_START:
                sessions_today += 1
        except Exception:
            pass
    return sessions_today, None, last  # no token data in kiro session files


def opencode():
    base = HOME / ".local" / "share" / "opencode" / "storage" / "session"
    if not base.exists():
        return 0, None, None
    sessions_today, tokens, last = 0, 0, None
    for f in base.rglob("*.json"):
        try:
            d = json.loads(f.read_text())
            t = d.get("time", {})
            updated = t.get("updated") or t.get("created")
            if not updated:
                continue
            ts = updated / 1000.0
            if last is None or ts > last:
                last = ts
            if ts >= TODAY_START:
                sessions_today += 1
        except Exception:
            pass
    # opencode stores parts per message; no token counts in session files
    return sessions_today, None, last


def fmt_tokens(n):
    if n is None: return "N/A"
    if n == 0: return "N/A"
    return f"~{n//1000}k" if n >= 1000 else str(n)


def fmt_last(ts):
    if ts is None: return "N/A"
    return ago(ts)


def main():
    rows = [
        ("claude-code", *claude_code()),
        ("kiro",        *kiro()),
        ("opencode",    *opencode()),
    ]

    print("Helm Quota Status")
    print("=================")
    print(f"{'harness':<14} {'sessions_today':<16} {'tokens_est':<13} {'last_active'}")
    print(f"{'-'*14} {'-'*14} {'-'*11} {'-'*12}")
    for name, sess, tok, last in rows:
        print(f"{name:<14} {str(sess):<16} {fmt_tokens(tok):<13} {fmt_last(last)}")

    print()
    print("Note: token counts from claude-code message.usage fields.")
    print("      kiro/opencode session files do not store token counts.")
    print("      For kiro usage, see: https://kiro.dev (account dashboard)")
    print("      For opencode usage, check provider dashboard (OpenRouter etc.)")


if __name__ == "__main__":
    main()
