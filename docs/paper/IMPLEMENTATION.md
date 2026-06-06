# Implementation

Helm is implemented as a macOS-only fork of WezTerm/Kaku, combining a Rust terminal
core with a 550+ line Lua orchestration layer (`kaku.lua`). This architecture lets us
extend terminal behavior through WezTerm's stable Lua event API without recompiling
native code.

## Session Scheduler

Session state is maintained in a Lua global table
`wezterm.GLOBAL.helm_sessions`, keyed by pane ID:

```
helm_sessions[pane_id] = {
  harness, cwd, start_time, last_accessed, state
}
```

The `update-right-status` hook fires approximately once per second. On each tick,
`helm_track()` is called on the currently active pane. It calls `detect_harness()`,
which matches the pane's foreground process name against a registry of known harness
labels (`kiro-cli`, `claude`, `opencode`, `codex`, `aider`). If a harness is detected,
the session entry is created or updated with the current timestamp as `last_accessed`.

Persistence is handled by serializing the sessions table to JSON and writing it to
`~/.helm/sessions/runtime.json` on every update tick. On startup, the file is read
back and the table is restored, so sessions survive terminal restarts.

LRU eviction is applied when the active session count exceeds six: sessions are sorted
by `last_accessed` in descending order, and any beyond the sixth position are marked
`state = 'background'`, suspending their HUD representation without killing the
underlying process.

## Status Awareness

Tab titles are formatted by the `format-tab-title` event handler, producing labels of
the form `🔵 kiro:projectname (MM:SS)`, where the clock shows elapsed runtime for that
agent session. The icon changes to `🟠` when the session enters the waiting state.

Waiting detection runs inside the `update-right-status` handler: it reads the last
three lines of pane output via `pane:get_lines_as_text(3)` and pattern-matches for
shell prompt characters (`>`, `$`, `?`) or the literal string `waiting`. A state
transition to `waiting` triggers a macOS system notification via
`os.execute('osascript -e ...')`. Notification spam is suppressed by a per-session
`last_notified` timestamp; a second notification is not sent unless at least 30 seconds
have elapsed since the last one.

## Shared Context

All supported harnesses are directed to the same context file through symlinks
established at setup time:

```
~/.claude/CLAUDE.md        → ~/.kiro/AGENTS.md
~/.config/opencode/AGENTS.md → ~/.kiro/AGENTS.md
~/.codex/AGENTS.md         → ~/.kiro/AGENTS.md
```

These symlinks are created automatically by `first_run.sh` and
`tools/helm-init/helm-init.sh`, requiring no manual configuration from the user.
A Python-based history indexer reads session logs from three harness-specific formats
and merges them into a unified JSON index at `~/.helm/sessions/index.json`, enabling
cross-harness session search via `helm-history`.

## Tools Ecosystem

Six CLI tools ship with Helm: `helm-history` (cross-harness session search),
`helm-quota` (token and cost tracking), `helm-status` (live session summary),
`helm-watch` (real-time session monitor), `helm-telemetry` (usage analytics), and
`helm-init` (one-command setup). Together they expose the session data collected by
the Lua layer to shell scripts and external tooling.
