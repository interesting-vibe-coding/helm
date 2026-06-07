#!/usr/bin/env python3
"""helm-quota: per-harness session/token usage summary.

Default: human-readable table.   `--json`: compact machine-readable JSON
(consumed by Helm's bottom status bar in kaku.lua).

────────────────────────────────────────────────────────────────────────
Usage sources investigated (2026-06) — what's actually available per harness:

  claude-code : No non-interactive CLI usage command. The interactive
                session has /cost and /usage, but nothing scriptable.
                `ccusage` (npm) is the popular community tool, but it just
                parses the same ~/.claude/projects/**/*.jsonl `message.usage`
                fields we read here — so our local parse IS the canonical
                source (accurate input+output token counts per turn).

  kiro        : No `kiro-cli usage` subcommand. Session files under
                ~/.kiro/sessions/cli/*.json carry NO token counts. Usage is
                only visible on the kiro.dev account dashboard. => session
                COUNT is the best local signal; tokens = N/A.

  opencode    : `opencode stats` exists but prints an all-time ASCII table
                (not today-scoped, not JSON) — too fragile to scrape. BUT the
                per-message JSON under
                ~/.local/share/opencode/storage/message/<ses>/<msg>.json
                contains tokens.{input,output,reasoning,cache} + cost +
                time.created. We sum those for today => accurate tokens.

Conclusion: local-file parsing gives the best today-scoped numbers for
claude-code + opencode; kiro stays session-count only until a CLI/API exists.
────────────────────────────────────────────────────────────────────────
"""
import json, os, sys, time
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
    """Returns (sessions_today, tokens_today, last_active_ts)."""
    base = HOME / ".claude" / "projects"
    if not base.exists():
        return 0, 0, None
    tokens_today, last = 0, None
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
                            tokens_today += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        except Exception:
            pass
    return len(session_ids_today), tokens_today, last


def kiro():
    """Returns (sessions_today, tokens_today=None, last_active_ts). No token data."""
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
    """Returns (sessions_today, tokens_today, last_active_ts).

    sessions_today from storage/session; tokens_today summed from per-message
    JSON (tokens.input + tokens.output for assistant turns created today)."""
    storage = HOME / ".local" / "share" / "opencode" / "storage"
    sess_base = storage / "session"
    msg_base = storage / "message"
    sessions_today, last = 0, None
    if sess_base.exists():
        for f in sess_base.rglob("*.json"):
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
    tokens_today = 0
    if msg_base.exists():
        for f in msg_base.rglob("*.json"):
            try:
                d = json.loads(f.read_text())
                created = (d.get("time", {}) or {}).get("created")
                if not created:
                    continue
                ts = created / 1000.0
                if ts < TODAY_START:
                    continue
                tk = d.get("tokens") or {}
                tokens_today += (tk.get("input", 0) or 0) + (tk.get("output", 0) or 0)
            except Exception:
                pass
    return sessions_today, (tokens_today if tokens_today else None), last


def fmt_tokens(n):
    if n is None: return "N/A"
    if n == 0: return "N/A"
    return f"~{n//1000}k" if n >= 1000 else str(n)


def fmt_last(ts):
    if ts is None: return "N/A"
    return ago(ts)


def collect():
    """Return the raw per-harness tuples."""
    return [
        ("claude", *claude_code()),
        ("kiro",   *kiro()),
        ("opencode", *opencode()),
    ]


def emit_json():
    rows = collect()
    out = {}
    for name, sess, tok, _last in rows:
        out[name] = {
            "tokens_today": tok if tok is not None else 0,
            "sessions_today": sess,
        }
    # compact, no spaces — small payload for run_child_process
    sys.stdout.write(json.dumps(out, separators=(",", ":")))
    sys.stdout.write("\n")


def emit_table():
    # human table uses the 'claude-code' label for clarity
    rows = collect()
    label = {"claude": "claude-code"}
    print("Helm Quota Status")
    print("=================")
    print(f"{'harness':<14} {'sessions_today':<16} {'tokens_today':<13} {'last_active'}")
    print(f"{'-'*14} {'-'*14} {'-'*11} {'-'*12}")
    for name, sess, tok, last in rows:
        print(f"{label.get(name, name):<14} {str(sess):<16} {fmt_tokens(tok):<13} {fmt_last(last)}")
    print()
    print("Note: claude-code tokens summed from message.usage (today only).")
    print("      opencode tokens summed from storage/message/*.json (today).")
    print("      kiro session files store no token counts (sessions only).")


def main():
    if "--json" in sys.argv[1:]:
        emit_json()
    else:
        emit_table()


if __name__ == "__main__":
    main()
