# Abstract

Modern software development increasingly relies on parallel AI coding agents — multiple
autonomous sessions running concurrently across repositories, tasks, and tools. Yet the
terminal, the primary interface through which developers interact with these agents,
remains anchored to a 1:1 human-to-session model. Developers must manually track session
states, context-switch between panes, and respond to agent requests — a bottleneck we
term the *Human-in-the-Loop (HiL) attention problem*.

We present **Helm**, a session-scheduled terminal designed for orchestrating parallel AI
agents. Helm introduces three architectural layers: a *Session Scheduler* that surfaces
the highest-priority agent requiring attention; a *Status Awareness* layer that detects
and classifies agent states (working, waiting, error) via pattern matching and macOS
notifications; and a *Shared Context* layer that propagates memory and tool configurations
across all active sessions. A preliminary user study with professional developers suggests
Helm reduces HiL response latency by X% and improves agent utilization by Y% compared to
standard terminal workflows. Our findings reframe the terminal not as a command executor
but as an *attention scheduler*, and demonstrate that attention routing — not compute or
context length — is the primary bottleneck in multi-agent developer workflows.
