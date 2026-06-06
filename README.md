<div align="center">
  <img src="assets/logo.icns" width="120" />
  <h1>Helm 🎯</h1>
  <p><em>The first agent-native terminal. You steer — agents execute.</em></p>
</div>

<p align="center">
  <a href="https://github.com/interesting-vibe-coding/helm/releases"><img src="https://img.shields.io/github/v/tag/interesting-vibe-coding/helm?label=version&style=flat-square" alt="Version"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
</p>

---

## What is Helm?

Helm is an **agent-native terminal** — built from the ground up around AI agents, not as an afterthought.

Most terminals put you in front of a command line. Helm puts you at the helm: your agents do the work, surface what matters, and wait for your call. You review and sign off. Zero friction.

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

## Built On

Helm is a focused fork of [Kaku](https://github.com/tw93/Kaku) (itself a fork of [WezTerm](https://wezfurlong.org/wezterm/)), with Helm-specific agent orchestration layered on top. GPU rendering, Lua config, multiplexer — all inherited and battle-tested.

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

## License

MIT — see [LICENSE.md](LICENSE.md)
