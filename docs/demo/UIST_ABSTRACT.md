# Helm: A Session-Scheduled Terminal for Parallel AI Agent Orchestration
## UIST 2026 Demo Abstract

---

### Abstract

We demonstrate Helm, an agent-native terminal that virtualizes N background AI agent sessions onto M visible panes using LRU scheduling. Helm comprises three layers: (1) a **Session Scheduler** that manages session visibility based on recency and waiting state; (2) **Status Awareness** that displays real-time agent state (Working / Waiting / Background) in the tab bar with macOS notifications; and (3) **Shared Context** that unifies memory and chat history across harnesses (kiro, Claude Code, opencode, Codex) via a symlinked AGENTS.md and a cross-harness session index. In our demonstration, we run four parallel AI agents, background idle sessions, receive notifications when agents need input, and hand off context between harnesses—all without leaving the terminal.

---

### 1. Introduction

Modern software development increasingly relies on AI coding agents—tools such as Claude Code, Kiro, opencode, and Codex—that autonomously execute multi-step tasks lasting minutes to hours. A developer running several agents in parallel quickly faces a coordination problem: terminals offer no mechanism to track which agent is active, which is blocked waiting for input, or which has been idle in the background. The dominant workaround is to manually tile windows or switch tmux panes, a process that demands constant attention and interrupts the developer's own focus. The result is that most practitioners run agents sequentially rather than in parallel, leaving significant throughput on the table.

Helm reframes the terminal as an *agent OS*: a scheduler that allocates visible panes to sessions the way an operating system allocates CPU time to threads. Borrowing from virtual memory design, Helm decouples the M panes a developer can physically observe from the N sessions running in the background (N >> M). Sessions are promoted to visible panes when they transition to a waiting state—requiring human input—and demoted back to the background on a least-recently-used basis when they resume autonomous work. The developer's attention becomes the scarce resource that Helm manages, not terminal real estate.

This paper describes the design and a live demonstration of Helm. We show that a three-layer architecture—Session Scheduler, Status Awareness, and Shared Context—is sufficient to enable a single developer to orchestrate four or more parallel AI agents with the same cognitive overhead previously required for one.

---

### 2. System

Helm is built on WezTerm (GPU-accelerated, Lua-configurable) and inherits Kaku's local-first AI interaction model. Three layers compose the system.

**Layer 1 — Session Scheduler.** Helm maintains a session registry mapping each agent session to one of three states: *Working* (agent running autonomously), *Waiting* (agent blocked, requires human input), or *Background* (session deprioritized by LRU policy). When a session transitions to Waiting, the scheduler promotes it to a visible pane, triggering a macOS notification if the developer is not looking at that pane. When the developer responds and the agent resumes, the session is marked Working; if it remains idle past a configurable threshold, it is evicted to Background, freeing the pane slot. The eviction policy is LRU: the session least recently accessed is the first to be paged out.

**Layer 2 — Status Awareness.** The WezTerm tab bar is extended with per-tab status glyphs: `⚙` Working, `⏳` Waiting, `○` Background. The window title displays the aggregate count of active agents (`Helm [4 agents]`). macOS UserNotifications fire when any session transitions to Waiting while the Helm window is not frontmost, ensuring developers working in other applications are not blocked. A `/status` slash command prints a full session table—harness, state, last activity timestamp, and current task—without requiring the developer to visit each pane.

**Layer 3 — Shared Context.** Each AI harness reads its project memory from a file at a conventional path (`~/.kiro/AGENTS.md`, `~/.claude/CLAUDE.md`, etc.). Helm's setup script symlinks all harness memory files to a single canonical `~/.kiro/AGENTS.md`, ensuring every harness shares the same project context, coding conventions, and identity facts without duplication. A cross-harness session index at `~/.helm/sessions.json` records the last-active session per harness, enabling `/handoff` to inject the prior session's summary as context when switching harnesses mid-task.

**[Figure placeholder: Three-panel diagram — left: session registry state machine (Working → Waiting → Background → Working); center: annotated tab bar screenshot showing status glyphs and window title; right: shared context symlink graph across harnesses.]**

---

### 3. Demonstration

The demonstration runs for approximately three minutes and proceeds in four phases.

*Setup (30 s).* The demonstrator opens Helm with four tabs, each running a different harness: Claude Code, Kiro CLI, opencode, and Codex CLI. A single `helm setup` command symlinks all harness memory files to the shared AGENTS.md. The `/status` command confirms all four sessions are in the Working state.

*Scheduling in action (60 s).* Two agents complete their current tasks and transition to Waiting. Helm automatically promotes both sessions to visible panes and fires macOS notifications. The demonstrator responds to each in turn; the agents resume autonomously and are demoted to Background. The tab bar updates in real time throughout.

*Notification and context handoff (60 s).* The demonstrator switches focus to a text editor. A third agent finishes and sends a macOS notification. Clicking the notification brings Helm to the foreground with the relevant pane already active. The demonstrator then uses `/handoff` to move the task from Claude Code to Kiro CLI mid-flight, demonstrating that the new session inherits full context from the session index.

*Parallel throughput comparison (30 s).* A side-by-side benchmark shows four tasks completing in the elapsed time previously required for one, illustrating the throughput multiplier that session scheduling provides.

---

### 4. Availability

Helm is open source and available at [https://github.com/interesting-vibe-coding/helm](https://github.com/interesting-vibe-coding/helm). The repository includes installation instructions, Lua configuration examples, and the `helm setup` script for cross-harness memory linking. Helm requires macOS and WezTerm; AI harness CLIs (Claude Code, Kiro CLI, opencode, Codex) are optional and detected automatically at runtime.

---

### References

[1] WezTerm. *WezTerm — GPU-accelerated terminal emulator*. https://wezfurlong.org/wezterm/, 2024.

[2] manaflow-ai. *cmux: Ghostty-based multi-agent terminal with notification rings and sidebar*. https://github.com/manaflow-ai/cmux, 2025.

[3] interesting-vibe-coding. *paws: Game-based distraction and HUD for single AI agent sessions*. https://github.com/interesting-vibe-coding/paws, 2025.

[4] Slack, A., et al. *Design Properties for Human-AI Agent Collaboration*. arXiv:2603.10664, 2026.

[5] Anthropic. *Claude Code: Agentic coding in your terminal*. https://docs.anthropic.com/claude-code, 2025.
