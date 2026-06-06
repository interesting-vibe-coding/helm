# Related Work

## 2. Related Work

### 2.1 Terminal Multiplexers

tmux and GNU Screen established the modern model of persistent terminal sessions: detachable processes, split panes, and background execution that survives network disconnects [CITATION: tmux]. These tools remain the backbone of server-side workflows. However, they were designed for human operators managing long-running processes, not for AI agents whose completion state, waiting behavior, and context requirements differ fundamentally. Session management in tmux is entirely manual—the user decides which pane to view, when to switch, and how to route input. There is no notion of agent state, no inference about which session needs attention, and no mechanism for sharing context between sessions. Helm builds on the same WezTerm multiplexer foundation but adds a scheduling layer that treats sessions as schedulable units rather than static pane slots.

### 2.2 AI-Augmented Terminals

Warp [CITATION: Warp] introduced inline AI completion and natural-language command generation directly in the terminal. Its AI block model tightly couples each AI interaction to a single shell session, and its intelligence layer is cloud-hosted, requiring network access and account authentication. The 1:1 session model means Warp does not address the problem of orchestrating multiple simultaneous agents.

Kaku [CITATION: Kaku] is our direct ancestor. Built on WezTerm, Kaku introduced an AI chat panel (Cmd+L), error recovery suggestions, and `#`-prefixed natural-language-to-command translation—all running locally. Kaku demonstrated that a terminal could be an AI-first interface rather than an AI-augmented one. Helm extends Kaku's local-first philosophy by adding the session scheduler, status awareness layer, and cross-harness context unification that Kaku does not address.

Neither Warp nor Kaku schedules sessions across multiple agents, surfaces per-session agent state in the UI, or shares context across different AI harnesses.

### 2.3 Agent Notification Systems

cmux (manaflow-ai/cmux) [CITATION: cmux] takes a Ghostty-based approach to agent awareness, providing notification rings, a sidebar overview, and an in-app browser for reviewing agent output without leaving the terminal. paws (interesting-vibe-coding/paws) [CITATION: paws] addresses the complementary problem of agent-induced distraction by gamifying wait time and displaying a HUD for a single running agent.

Both systems address the *when* dimension of human-agent interaction: they notify the user when an agent needs attention. Neither addresses *which* session should be brought to the foreground based on scheduling priority, nor *what context* the user needs to resume work. Helm's session scheduler handles both questions, treating visibility allocation as a resource management problem analogous to OS process scheduling.

### 2.4 Multi-Agent Orchestration

Claude Code [CITATION: Claude Code] supports spawning parallel headless subagents for decomposed tasks. cmux's `claude-teams` mode can launch multiple Claude Code sessions side by side. However, both approaches treat the terminal as a passive display surface. There is no attention routing—the user must manually track which agent is active, waiting, or blocked. There is no cross-harness context sharing, so switching from Claude Code to Kiro or opencode requires manual re-establishment of project memory.

Helm introduces an active scheduling layer that sits above individual harnesses, routing attention and context automatically as agents transition between working, waiting, and background states.

### 2.5 Human-AI Collaboration Frameworks

Slack et al. (2025) identify key design properties for productive human-AI agent collaboration, including representational compatibility—shared data structures that both humans and agents can read—and transparency of agent state [CITATION: arxiv:2603.10664]. The terminal inherently satisfies both properties: text is universally readable, and shell output is a natural audit trail. Helm extends this framework by elevating the terminal from an interface to a *scheduler*: it actively manages which agent has the user's attention based on recency and waiting state, reducing the coordination overhead that otherwise falls on the human.

### 2.6 OS Scheduling Analogy

Operating systems decouple physical memory from the virtual address space each process perceives, allowing more processes to run than physical RAM permits via demand paging and LRU eviction [CITATION: OS textbook]. Our core insight maps directly: just as virtual memory decouples physical pages from running processes, Helm decouples visible panes (M) from active sessions (N), where N >> M. LRU page replacement becomes LRU session eviction—a session not recently accessed is paged to the background, freeing a pane for the agent currently requiring attention. This framing makes Helm's design decisions principled rather than heuristic and opens a clear path to more sophisticated scheduling policies (priority queues, deadline-aware scheduling) as future work.
