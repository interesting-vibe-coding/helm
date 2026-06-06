# Helm: A Session-Scheduled Terminal for Human-in-the-Loop Orchestration of Parallel AI Agents

---

## 1. Introduction

A developer running five Claude Code sessions today manually checks each pane every few minutes, cycling through split-screen windows to see which agent has finished, which is blocked on a prompt, and which has been silently idle for the past half hour. This is not a productivity strategy — it is the absence of one. The terminal, unchanged in its fundamental interaction model since the introduction of tmux and GNU Screen, has no concept of agent state. The human serves as the scheduler.

The core mismatch is structural. Classical terminal emulators operate on a 1:1 assumption: one human, one foreground session. Split panes and tab bars extend this model superficially, giving the human more to watch rather than less to manage. This was appropriate when terminal latency was human-dominated — a session blocked on the developer's next keystroke. Agentic workflows invert this relationship. Modern AI coding agents (Claude Code, Kiro, opencode) spend the majority of their wall-clock time waiting on LLM inference or tool execution, with human decision points measured in seconds against agent execution windows measured in minutes. The human's role shifts from *doing* to *directing*, yet the terminal still requires constant manual polling.

We argue that human attention is the bottleneck in parallel agentic workflows, and that the terminal is the right place to address it. The insight draws from a classical OS analogy: just as virtual memory decouples program address space from physical RAM — allowing more programs to run than fit in memory by paging idle data out — a terminal scheduler can decouple session count from pane count, surfacing active sessions while hiding idle ones. The human's attention, like physical frames, is a scarce resource that should be allocated to sessions that need it.

We present **Helm**, an agent-native terminal built on WezTerm that realizes this insight through three coordinated layers:

- **Session Scheduler.** Virtualizes N background agent sessions onto M visible panes using an LRU eviction policy. Sessions transition to background automatically when idle; active or waiting sessions are promoted to foreground. Manual override preserves user control.
- **Status Awareness.** Tracks per-session state (Working / Waiting / Idle) in real time by monitoring stdout activity and harness-specific signals (token quotas, rate limit indicators). A compact status bar surfaces actionable state across all sessions without requiring the user to read terminal output.
- **Shared Context.** Unifies cross-harness memory and chat history under a single schema, so that switching agents mid-task — whether due to quota exhaustion or model preference — does not require the user to re-explain context from scratch.

Together, these layers reduce human-in-the-loop latency (time from agent-ready to human response) and increase agent utilization rate (fraction of time agents spend working rather than waiting on human attention). A controlled user study (N=16) on three representative multi-agent task designs quantifies these gains against a standard tmux baseline.

---

## 2. Related Work

**Terminal multiplexers.** tmux [CITATION] and GNU Screen [CITATION] introduced persistent session management and split-pane layouts to the terminal, enabling a single user to monitor multiple shell sessions. These tools remain the de facto baseline for developers running parallel workloads. However, they are passive viewports: pane layout is manually configured, session state is not tracked, and no mechanism exists to surface or prioritize sessions based on activity. Helm adopts the session persistence model from tmux but adds a scheduling layer that acts on semantic state rather than user-defined layout.

**AI-augmented terminals.** Warp [CITATION] modernizes the terminal with block-structured output, command history search, and inline AI completions. It substantially improves the single-session experience but preserves the 1:1 human-session model. Kaku (the upstream project Helm forks from) exposes a Lua scripting API and programmable pane management, providing the substrate Helm builds on. Neither system models agent state or schedules pane visibility in response to agent activity. Helm is orthogonal to these improvements: it operates at the session management layer, not the output rendering or completion layer.

**Agent notification and presence systems.** cmux [CITATION] introduces notification rings that alert the user when an agent session requires attention, addressing the polling problem at the notification layer. Paws [CITATION] explores giving persistent visual presence to background agents — allowing the user to play a game while an agent works — framing idle time as an opportunity rather than dead time. Both systems detect agent waiting states but do not schedule sessions or share context across agents. Helm treats notification as a byproduct of scheduling: by promoting waiting sessions to foreground, the scheduler itself serves as the notification mechanism, while the Shared Context layer addresses the cross-agent coordination gap that neither system tackles.

**Human-AI collaboration frameworks.** Recent work on the design properties of human-AI agent collaboration [CITATION: arXiv 2603.10664] argues that the terminal represents the most natural interface for human oversight of AI agents, owing to its low latency, scriptability, and alignment with developer mental models. That work identifies attention management and context continuity as open challenges in collaborative agent workflows. Helm can be understood as a systems-level instantiation of these design principles: the Session Scheduler operationalizes attention management, and the Shared Context layer operationalizes context continuity.

**OS scheduling analogies.** The analogy between session scheduling and OS virtual memory management is deliberate. LRU page replacement [CITATION] evicts the least recently used physical frame when a new page fault occurs; Helm's scheduler evicts the least recently active session from the visible pane set when a higher-priority session transitions to Working or Waiting state. Prior work in window management [CITATION] and attention-aware computing [CITATION] has applied scheduling concepts to UI layer problems, but not to the specific challenge of managing parallel long-running agent sessions in a terminal environment.
