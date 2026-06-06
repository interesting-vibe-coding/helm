# PAPER OUTLINE — Helm

## Title
**Helm: A Session-Scheduled Terminal for Human-in-the-Loop Orchestration of Parallel AI Agents**

*Alt titles:*
- *Beyond the Single Session: Virtual Terminal Management for AI Agent Workflows*
- *Helm: Decoupling Human Attention from Agent Execution in Multi-Agent Terminals*

---

## Abstract

Modern AI coding agents (Claude Code, Kiro, opencode) are increasingly used in parallel, yet terminal emulators remain designed around the 1-person-1-session model inherited from interactive shell use. We present Helm, an agent-native terminal that decouples human attention from agent execution through three coordinated layers: (1) a Session Scheduler that virtualizes N background agent sessions onto M visible panes using an LRU policy, analogous to OS virtual memory; (2) a Status Awareness layer that tracks real-time per-session state (Working/Waiting/Idle, runtime, harness quota) to inform scheduling and surface actionable signals to the user; and (3) a Shared Context layer that unifies cross-harness memory and chat history under a single schema, eliminating redundant re-orientation cost as users switch between agents. A controlled user study (N=16) on three representative multi-agent tasks shows that Helm reduces human-in-the-loop latency by X%, increases agent utilization rate by Y%, and cuts manual context-switch count by Z% compared to a standard tmux baseline. Helm demonstrates that the bottleneck in agentic workflows is attention routing, not agent capability, and that terminal-level scheduling can close this gap.

---

## 1. Problem Statement

**Assumption mismatch.** Classical terminal emulators (xterm, iTerm2, tmux, WezTerm) model one human operating one foreground session at a time. Split panes and tab bars are manual layout tools, not schedulers — the human must remember which agent is running what, poll each pane for completion, and manually copy context between sessions.

**Why this breaks with agents.** AI coding agents introduce a new regime:
- Agent wall-clock time per task: minutes to tens of minutes (mostly LLM inference wait)
- Human decision time per checkpoint: seconds
- Typical parallel workload: 3–8 concurrent agents on a feature branch or review cycle

The result: agents sit Idle or Waiting while the human is occupied elsewhere; the human returns to stale output with no state summary; context (memory files, prior chat) must be re-fed manually per harness.

**Gap.** No existing terminal system models session state, schedules pane visibility by agent activity, or unifies cross-harness context. The human becomes a manual scheduler and context bus — high friction, high error rate.

---

## 2. Key Insight

> **Agent wait time >> human attention time → decouple them.**

In a classical interactive shell, latency is human-dominated (typing speed ~60 WPM). In an agentic workflow, latency is agent-dominated (LLM round-trip + tool execution). The human's job shifts from *doing* to *directing and deciding*.

This inversion enables a scheduling analogy with OS virtual memory:
- Sessions = virtual pages
- Visible panes = physical frames
- LRU eviction = hide idle sessions, surface active ones
- Page fault = user manually promotes a session

The terminal can thus act as a scheduler rather than a passive viewport, maximizing the fraction of human attention spent on sessions that actually need it.

---

## 3. System Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        HELM                             │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Layer 3: Shared Context                         │  │
│  │  • Unified memory (symlinks: ~/.kiro/skills →    │  │
│  │    ~/.claude/skills → opencode config)           │  │
│  │  • Chat history bridge                           │  │
│  │    Claude Code (.jsonl) ─┐                       │  │
│  │    Kiro (.json)          ├─→ unified schema      │  │
│  │    opencode (per-msg)   ─┘    {role,content,ts,  │  │
│  │                                harness,session}  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Layer 2: Status Awareness                       │  │
│  │  • Per-session state machine:                    │  │
│  │    Working → Waiting → Idle                      │  │
│  │  • Tracked signals: runtime, stdout δ/s,         │  │
│  │    harness-specific quota (tokens/min remaining) │  │
│  │  • Status bar: [●W 2:34 | ○W | ○I] per pane     │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Layer 1: Session Scheduler                      │  │
│  │                                                  │  │
│  │  N background sessions (virtual pool)            │  │
│  │  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                 │  │
│  │  │ S1│ │ S2│ │ S3│ │ S4│ │ S5│  ...SN           │  │
│  │  └─┬─┘ └─┬─┘ └─┬─┘ └───┘ └───┘                 │  │
│  │    │     │     │  LRU scheduler                  │  │
│  │    ▼     ▼     ▼                                 │  │
│  │  ┌─────────────────────────────┐                 │  │
│  │  │  M visible panes (viewport) │                 │  │
│  │  │  [Pane A] [Pane B] [Pane C] │                 │  │
│  │  └─────────────────────────────┘                 │  │
│  │  Eviction: Idle sessions → background            │  │
│  │  Promotion: Working/Waiting → foreground         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  User input: slash commands injected via pane:send_text │
└─────────────────────────────────────────────────────────┘
```

### Layer 1 — Session Scheduler
- Maintains pool of N PTY sessions (persistent, never killed)
- M visible pane slots (M << N, e.g. M=3, N=8)
- LRU policy: sessions with longest Idle time evicted from viewport first
- Scheduler runs every T seconds (default 5s); re-evaluates on status change events
- Manual override: Cmd+number to pin/promote any session

### Layer 2 — Status Awareness
- Monitors stdout stream per session: δ bytes/s classifies Working vs Waiting vs Idle
- Harness-specific quota probes: parse Claude Code/Kiro/opencode status lines for token/rate limits
- Exposes `SessionState { id, harness, state, runtime_s, quota_pct, last_active_ts }`
- Status bar renders compact per-pane indicator; overflow sessions shown as notification badge

### Layer 3 — Shared Context
- Memory unification: symlinks already established (`~/.kiro/skills ↔ ~/.claude/skills`)
- Chat history schema:
  ```
  { session_id, harness, role, content, timestamp_ms, tokens?, tool_calls? }
  ```
- Importers: Claude Code JSONL parser, Kiro JSON parser, opencode per-message JSON parser
- Unified history queryable by session or cross-session (for handoff prompts)

---

## 4. User Study Design

**Participants:** 16 developers who regularly use AI coding agents (screened for ≥3 sessions/week)

**Baseline:** tmux with 3 panes, one agent per pane, no status tooling (representative of current practice)

**Helm condition:** same tasks, same agents, Helm with all three layers enabled

### Task 1 — Parallel Feature Development
Implement two independent features (UI component + API endpoint) simultaneously using two agent sessions. Dependent subtask arrives mid-task requiring output from both.

*Measures:* time-to-completion, number of pane switches, idle agent time (agent waiting while user occupied elsewhere)

### Task 2 — Review + Fix Cycle
Run a code review agent on 3 PRs in parallel. For each PR, agent produces a report; user reads and decides fix/defer; fix agent executes.

*Measures:* human-in-the-loop latency (time from agent-ready to human-action), missed-completion events (agent finished but user didn't notice)

### Task 3 — Context Handoff
Start a task in Claude Code, hand off to Kiro mid-session (simulating quota exhaustion or model preference switch). Continue without re-explaining context.

*Measures:* handoff time, number of re-orientation prompts issued by user, subjective continuity rating (7-pt Likert)

---

## 5. Metrics

| Metric | Definition | Collection |
|--------|-----------|------------|
| **Human-in-the-loop latency** | Time from agent entering Waiting/Idle state to user next interaction with that session | Logged from status state transitions + input events |
| **Agent utilization rate** | Fraction of wall-clock time each session spends in Working state | Aggregated from per-session state logs |
| **Context switch count** | Number of manual pane/tab switches user performs | Keyboard/mouse event log |
| **Handoff re-orientation cost** | Token count of user prompts that re-explain prior context (Task 3) | Chat history diff |
| **Subjective workload** | NASA-TLX post-task | Self-report |

---

## 6. Venue Recommendation

**Primary: UIST** (ACM Symposium on User Interface Software and Technology)
- Helm is fundamentally a *systems artifact* with a novel interaction model — UIST rewards novel UI systems with strong technical contributions and user studies
- Session scheduling + status-aware pane management is the kind of systems-level UI innovation UIST values
- Precedent: terminal/IDE interaction papers (e.g., Codeon, Whyline, live programming systems)

**Secondary: CHI** (ACM CHI Conference on Human Factors in Computing Systems)
- If framed around the human-agent collaboration angle and the attention-decoupling insight
- CHI accepts more theory-forward framing; stronger emphasis on user study N and statistical rigor
- Risk: CHI reviewers may ask for larger N and more ecological validity; systems contribution weighted less

---

## 7. Related Work

**tmux / screen** — classic terminal multiplexers that provide manual session management with no awareness of session state or agent activity.

**Warp** — modernizes the terminal with block-based output and AI command suggestions, but still assumes a single-user-foreground-session interaction model.

**WezTerm** — highly programmable terminal (Lua API, pane:send_text) that Helm builds on; provides the substrate for slash-command injection but no scheduling or status layer.

**paw / Paws** — explores giving persistent visual presence to background agents, complementary to Helm's scheduling focus (presence vs. scheduling).

**Claude Code / Kiro / opencode** — AI coding agents that Helm orchestrates; each has its own session/memory format, motivating the Shared Context layer.

---

## 8. Contributions Summary

1. **Problem framing**: agent wait time >> human attention time → terminal scheduling as a first-class concern
2. **System**: Helm — three-layer architecture (Session Scheduler, Status Awareness, Shared Context)
3. **Implementation**: working prototype on WezTerm/Lua with real harness integrations
4. **Evaluation**: controlled user study on parallel agentic workflows with three concrete task designs
