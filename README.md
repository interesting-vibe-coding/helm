<div align="center">
  <img src="assets/helm-logo.png" width="128" alt="Helm" />
  <h1>Helm 🎯</h1>
  <p><em>The first agent-native terminal. You steer — agents execute.</em></p>

  <p>
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/platform-macOS-lightgrey?style=flat-square" alt="Platform">
    <img src="https://img.shields.io/badge/built%20on-WezTerm-orange?style=flat-square" alt="Built on WezTerm">
    <img src="https://img.shields.io/badge/status-early%2FMVP-yellow?style=flat-square" alt="Status">
  </p>
</div>

---

## What is Helm?

Helm is the **first agent-native terminal** for macOS. Run many AI agents in parallel; Helm handles the scheduling, status, and shared context so you only do the deciding.

Most terminals assume one human, one session. Helm assumes you are orchestrating a fleet of agents: they do the work, surface what needs you, and wait. You review and sign off. Zero friction.

## Philosophy: less friction

Helm exists to remove the friction between you and your agents. You shouldn't babysit a terminal, hunt for which pane needs your input, or lose your place switching tools. Agents do the work and surface what needs you; you stay at the helm and make the calls.

---

## The Agent OS

Helm adds three layers on top of a fast GPU terminal:

```mermaid
flowchart TB
    L3["🧠 <b>Shared Context</b><br/>one AGENTS.md → every harness · unified chat history"]
    L2["📊 <b>Status Awareness</b><br/>per-agent state in tab bar · HUD · macOS notifications"]
    L1["🔀 <b>Session Scheduler</b><br/>LRU virtualization · N background ⇄ M visible panes"]
    CORE["⚡ WezTerm core · GPU render · Lua config"]
    L3 --> L2 --> L1 --> CORE
    style L3 fill:#2d1b4e,stroke:#a855f7,color:#fff
    style L2 fill:#1e2a4a,stroke:#60a5fa,color:#fff
    style L1 fill:#1a3a2e,stroke:#34d399,color:#fff
    style CORE fill:#1a1a24,stroke:#666,color:#aaa
```

- **Session Scheduler** — keep 10 agents alive, show 2. Idle ones swap to the background; the one that needs you surfaces automatically.
- **Status Awareness** — every pane knows if its agent is working 🔵, waiting 🟠, or idle ⏸. Get notified the moment one needs input.
- **Shared Context** — one memory file, symlinked to every harness. Switch from Kiro to Claude Code mid-task; the context follows.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

That's it. On first launch, Helm guides you through shell integration and sets up
cross-harness memory automatically. Then press `Cmd+Shift+K` to launch your first agent.

<details>
<summary>Build from source</summary>

```bash
git clone https://github.com/interesting-vibe-coding/helm
cd helm
PROFILE=debug ./scripts/build.sh --app-only
open dist/Helm.app
```
</details>

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Shift+K` | Launch an agent (kiro / claude-code / opencode / codex) in a new pane |
| `Cmd+Shift+S` | Session list — all active agents with runtime + state |
| `Cmd+Shift+U` | Jump to the agent that's waiting for you |
| `Cmd+Shift+B` | Background the current session |
| `Cmd+Shift+M` | Toggle model (sonnet ↔ opus) in kiro |

---

## Why Helm?

| | Helm | tmux | cmux | Warp |
|---|:---:|:---:|:---:|:---:|
| Session scheduling (LRU) | ✅ | ❌ | ❌ | ❌ |
| Agent state in tab bar | ✅ | ❌ | 🔔 | ❌ |
| Cross-harness memory | ✅ auto | manual | ❌ | ❌ |
| Unified chat history | ✅ | ❌ | ❌ | ❌ |
| Native GPU render | ✅ | ❌ | ✅ | ❌ |
| Open source | ✅ | ✅ | ✅ | ❌ |

---

## Tools

Helm ships CLI tools for agent workflows (see [`tools/`](tools/)): `helm-history`, `helm-status`, `helm-watch`, `helm-doctor`, and more. Run `helm-doctor` to check your setup.

---

## Built On & Credits

Helm is a focused fork of **[Kaku](https://github.com/tw93/Kaku)** by [Tw93](https://github.com/tw93) (itself built on **[WezTerm](https://wezfurlong.org/wezterm/)**). Thank you 🙏 Inspired by **[Ghostty](https://ghostty.org)** and **[cmux](https://github.com/manaflow-ai/cmux)**.

macOS only (Apple Silicon + Intel). Rust + Lua. MIT licensed.

---

<div align="center">
  <sub>Part of <a href="https://github.com/interesting-vibe-coding">interesting-vibe-coding</a> — more fun agent tooling over there 🐾</sub>
</div>
