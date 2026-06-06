# System Design

## Architecture Overview

Helm is organized into three layers that together bridge the user's intent to agent execution.

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  WezTerm GUI · Tab bar · HUD overlay · Keybinding surface   │
├─────────────────────────────────────────────────────────────┤
│                  Session Scheduler Layer                     │
│  Session tracker · LRU policy · State machine · Persistence │
├─────────────────────────────────────────────────────────────┤
│                  Shared Context Layer                        │
│  AGENTS.md · Skills · Session index · Format translation    │
└─────────────────────────────────────────────────────────────┘
```

The User Interface Layer exposes Helm's status and controls through WezTerm's native tab bar and a compact right-status HUD. The Session Scheduler Layer manages the lifecycle of all running agent sessions, deciding which sessions are visible and signaling state transitions. The Shared Context Layer provides the memory substrate that is read by every harness, ensuring a consistent view of the user's identity, preferences, and past interactions regardless of which agent is active.

## Session Scheduler

The session scheduler maintains a bounded pool of agent sessions governed by a Least Recently Used (LRU) eviction policy. The pool holds up to N concurrent sessions, of which at most M are rendered as visible terminal panes (default M=2). Sessions beyond the visible window are moved to the background, freeing pane real estate while preserving process state. The scheduler selects candidates for backgrounding either automatically, when an agent emits an idle or waiting signal, or on explicit user command via Cmd+Shift+B.

Each session progresses through a four-state machine:

```
Working ──(idle signal / Cmd+Shift+B)──▶ Waiting
Waiting ──(confirmed idle)──────────────▶ Background
Background ──(Cmd+Shift+U / selector)──▶ Active
Active ──(focus acquired)───────────────▶ Working
```

The Working state indicates an agent is actively processing; Waiting means the agent has reached a prompt boundary and is awaiting user input. Background sessions remain alive in the PTY but are hidden from the pane layout. The Active transition reattaches a backgrounded session to a visible pane and updates its `last_accessed` timestamp, which governs future LRU ordering. Session records are persisted to `~/.helm/sessions/runtime.json` on every state transition and restored on startup, with entries older than 24 hours pruned at load time.

## Status Awareness

Helm infers the current state of each session from three complementary data sources. The primary source is the PTY process tree: Helm queries the foreground process name of each pane to detect when a known harness binary (e.g., `kiro-cli`, `claude`, `opencode`) is running. The secondary source is output pattern matching: the last three lines of each pane's scrollback are scanned for shell prompt patterns (`>`, `$`) and the literal string `waiting`, which reliably indicate that an agent has returned control to the user. Harness-specific signals, such as status annotations emitted by certain agents to stderr, serve as a tertiary source and take precedence when present.

The status subsystem updates at approximately one-second intervals, driven by WezTerm's `update-right-status` hook, which fires once per active window on each repaint cycle. Inferred states are reflected immediately in two surfaces: the tab bar, where each agent pane displays a colored emoji indicator (🔵 Working, 🟠 Waiting, ⏸ Background), and the compact HUD rendered in the window's right-status region. The HUD displays each working session as `<harness> <emoji> <HH:MM:SS>`, with a trailing `N bg` token when backgrounded sessions exist, for example `[Kiro 🔵 00:02:34 | 2 bg]`.

## Shared Context

All harnesses that run inside Helm share a single memory file, `AGENTS.md`, which resides at `~/.kiro/AGENTS.md` and is symlinked to each harness's conventional discovery path: `~/.claude/CLAUDE.md` for Claude Code, `~/.config/opencode/AGENTS.md` for opencode, and `~/.codex/AGENTS.md` for Codex CLI. Because the file is a symlink rather than a copy, any edit propagates immediately to all harnesses without a synchronization step. The shared memory encodes user identity, behavioral rules, active project context, and API credentials, giving every agent the same starting knowledge state.

Skills — reusable instruction modules — are stored under `~/.kiro/skills/` and similarly symlinked into each harness's skills directory. The unified session index at `~/.helm/sessions/index.json` records all agent interactions across harnesses in a common schema, enabling cross-harness history queries. Because each harness persists conversation history in a different format — Claude Code uses newline-delimited JSON (JSONL), kiro emits per-session JSON objects, and opencode writes per-message JSON fragments — Helm applies a thin translation layer when writing to the unified index:

| Harness     | Native Format       | Unified Field Mapping                        |
|-------------|---------------------|----------------------------------------------|
| Claude Code | JSONL per exchange  | `session_id`, `role`, `content`, `timestamp` |
| kiro        | Session JSON object | `session_id`, `messages[]`, `started_at`     |
| opencode    | Per-message JSON    | `session_id`, `role`, `text`, `created_at`   |

This translation preserves enough fidelity for session search and timeline reconstruction while discarding harness-specific metadata that has no cross-harness equivalent.
