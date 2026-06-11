# Quota data sources per harness (investigated 2026-06-11)

Zero-keystroke local sources for "tokens today" + "quota remaining". No pane
scraping needed for any harness.

| harness | tokens today | quota remaining | confidence |
|---------|--------------|-----------------|------------|
| claude-code | `~/.claude/projects/**/*.jsonl` → `message.usage.input+output`, timestamp filter (already implemented) | none exposed locally | high / none |
| kiro | session count only (`~/.kiro/sessions/cli/*.json` by `updated_at`) — no token data, no `usage` subcommand | none | low |
| codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` → last `token_count` event per file → `total_token_usage.total_tokens` | **`rate_limits.{primary,secondary}.used_percent` + `resets_at` + `plan_type`** from the same event — real quota %! primary window 300min, secondary 10080min (weekly) | high / high |
| opencode | `~/.local/share/opencode/storage/message/**/*.json` → `tokens.input+output`, `time.created` is **ms** (already implemented) | none; `cost` field gives $ today | high / none |

## Implementation order

1. **codex()** — highest value (only harness exposing quota %).
   Walk today's date dir; per file take the LAST `token_count` event
   (`total_token_usage` is a session-cumulative value, NOT a delta — never
   sum all events). Same event carries `rate_limits`.
2. claude-code fast path — `~/.claude/stats-cache.json` has
   `dailyModelTokens` (100x faster than jsonl scan) but `lastComputedDate`
   lags until Claude Code next runs: use cache iff `lastComputedDate ==
   today`, else fall back to jsonl scan.
3. kiro — session count stays the best available signal; recheck
   `kiro-cli --help-all` for a future usage subcommand.

## Gotchas

- Codex `token_count` events are cumulative per session — take last, not sum.
- Codex session dirs are UTC-date-named; sessions crossing midnight split
  across two dirs. quota.py's "today" is UTC midnight — consistent.
- opencode `time.created` is milliseconds (divide by 1000).
- Only assistant messages carry `tokens` in opencode (user msgs don't).
