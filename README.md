> **Status**: Early / MVP — usable daily. Actively developed. [Join the discussion →](https://github.com/interesting-vibe-coding/helm/discussions)

<div align="center">
  <img src="assets/logo.icns" width="120" />
  <h1>Helm 🎯</h1>
  <p><em>The first agent-native terminal. You steer — agents execute.</em></p>
</div>

<p align="center">
  <a href="https://github.com/interesting-vibe-coding/helm/releases"><img src="https://img.shields.io/github/v/tag/interesting-vibe-coding/helm?label=version&style=flat-square" alt="Version"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/platform-macOS-lightgrey?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/built%20on-WezTerm-orange?style=flat-square" alt="Built on WezTerm">
</p>

---

## What is Helm?

Helm is the **first agent-native terminal** for macOS. Run 10 AI agents in parallel; Helm handles the scheduling, notifications, and context sharing.

Built from the ground up around AI agents, not as an afterthought. Most terminals put you in front of a command line. Helm puts you at the helm: your agents do the work, surface what matters, and wait for your call. You review and sign off. Zero friction.

> "You steer. Agents execute."

Part of the [interesting-vibe-coding](https://github.com/interesting-vibe-coding) family: [paws](https://github.com/interesting-vibe-coding/paws) 🐾 · [paws-dock](https://github.com/interesting-vibe-coding/paws-dock) · Helm 🎯

---

## Why Agent-Native?

Every terminal today treats AI as a plugin bolted on top. Helm is different:

- **Agent workflows are first-class** — spawn, monitor, and switch between AI harnesses (Claude Code, Kiro, opencode, Codex) from a unified workspace
- **Keyboard-driven agent control** — bind shortcuts to slash commands; switch models, effort levels, and sessions without touching the mouse
- **Shared memory & skills** — all agents share the same context, memory files, and skill library out of the box
- **Status-aware layout** — Helm knows when an agent needs you and surfaces it automatically

---

## Features

- 🎯 **Agent harness launcher** — spawn any AI CLI in a new pane with one keystroke
- ⌨️ **Slash command shortcuts** — `Cmd+Shift+M` switches AI model mid-session, more mappable
- 🧠 **Cross-agent memory** — `PACK_MEMORY_FILE` + `PACK_SKILLS_DIR` injected into every harness on spawn
- 🐚 **Best-in-class shell** — GPU-accelerated (WezTerm core), Starship prompt, zoxide, delta, fish/zsh auto-detected
- 🎨 **Dark, minimal aesthetic** — tuned defaults, no config needed to look good
- 🔑 **Interactive first-run** — detects your shell, installs required tools silently, asks about optional ones

---

## Architecture: The Agent OS

```
┌─────────────────────────────────────────────────┐
│  Layer 3: Shared Context                        │
│  AGENTS.md → all harnesses  |  unified history  │
├─────────────────────────────────────────────────┤
│  Layer 2: Status Awareness                      │
│  tab bar status  |  HUD overlay  |  notifications│
├─────────────────────────────────────────────────┤
│  Layer 1: Session Scheduler                     │
│  LRU swap  |  N background  |  M visible panes   │
└─────────────────────────────────────────────────┘
              WezTerm / Kaku core
```

---

## Why Helm?

| Feature | Helm | tmux | cmux | Warp |
|---------|------|------|------|------|
| Session scheduling (LRU) | ✅ | ❌ | ❌ | ❌ |
| Agent status in tab bar | ✅ | ❌ | ✅ notification | ❌ |
| Cross-harness memory | ✅ auto | manual | ❌ | ❌ |
| Chat history unified | ✅ | ❌ | ❌ | ❌ |
| macOS native GPU render | ✅ | ❌ | ✅ (libghostty) | ❌ |
| Open source | ✅ | ✅ | ✅ (GPL) | ❌ |
| Lua configurable | ✅ | ❌ | ❌ | ❌ |

---

## Quick Start
```bash
# Build from source (macOS)
git clone https://github.com/interesting-vibe-coding/helm
cd helm
PROFILE=debug ./scripts/build.sh --app-only
open dist/Helm.app
```

---

## 5-Minute Demo

```bash
# After installing Helm.app:

# 1. Run helm-init to set up cross-harness memory
bash tools/helm-init/helm-init.sh

# 2. Open Helm.app and press Cmd+Shift+K
#    → Choose kiro, opencode, or claude-code
#    → A new pane spawns with the agent

# 3. Press Cmd+Shift+S to see all active sessions
# 4. Press Cmd+Shift+U when an agent needs your input
```

---

## Keyboard Shortcuts
| Shortcut | Action |
|---|---|
| `Cmd+Shift+S` | Session list — all active agents with runtime |
| `Cmd+Shift+M` | Toggle AI model (sonnet ↔ opus) in kiro chat |
| `Cmd+Shift+B` | Background current agent session |
| `Cmd+Shift+U` | Jump to waiting agent |
| `Cmd+Shift+K` | Launch new harness |
| `Cmd+L` | AI chat panel |
| `Cmd+Shift+G` | lazygit |

---

## Built On

Helm is a focused fork of [Kaku](https://github.com/tw93/Kaku) (itself a fork of [WezTerm](https://wezfurlong.org/wezterm/)), with Helm-specific agent orchestration layered on top. GPU rendering, Lua config, multiplexer — all inherited and battle-tested. Helm adds three layers on top: Session Scheduler (virtual session management), Status Awareness (real-time agent state), and Shared Context (cross-harness memory + history) — forming an Agent OS.

---

## Status

🟡 **Early / MVP** — usable daily, agent orchestration features actively being built.

macOS only (Apple Silicon + Intel). Built with Rust + Lua.

---

## Build

```bash
# Debug build (fast)
PROFILE=debug ./scripts/build.sh --app-only
# Opens dist/Helm.app
open dist/Helm.app
```

---

## Credits

Helm is built on the shoulders of:

- **[Kaku](https://github.com/tw93/Kaku)** by [Tw93](https://github.com/tw93) — our immediate foundation. Thank you 🙏
- **[WezTerm](https://wezfurlong.org/wezterm/)** by Wez Furlong — the terminal engine powering Helm
- **[Ghostty](https://ghostty.org)** by Mitchell Hashimoto — inspired fast, native terminal design
- **[cmux](https://github.com/manaflow-ai/cmux)** — pioneered agent notification rings and the hooks model

---

## License

MIT — see [LICENSE.md](LICENSE.md)
