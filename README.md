<div align="center">
  <img src="assets/kaji-logo.png" width="120" alt="Kaji" />
  <h1>Kaji</h1>
  <p><em>The agent-native terminal. You steer — agents execute.</em></p>
  <p>
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/macOS-Apple%20Silicon%20%2B%20Intel-lightgrey?style=flat-square" alt="macOS">
  </p>
</div>

---

> Your prefrontal cortex is finite.  
> Stop spending it on switching context between agents. `(ᴗ‿ᴗ)`
>
> Kaji solves this by giving every agent its own pane, a First Mate to watch them all, and a single conversation to steer the crew.

---

<!-- screenshot -->
<!-- ![Kaji](assets/screenshot.png) -->

---

## Why Kaji?

**舵** (kaji) — Japanese for *rudder*.

Most terminals are built for one human, one session. Kaji is built for the moment after that — when you have a crew of agents running in parallel and the real work is *directing* them, not *doing* their work yourself.

The name says it all: you hold the rudder. Kaji keeps the friction between you and your agents as close to zero as possible, so your focus stays on decisions — not on tabs. ⛵

## Features

- **Brain** — a Sonnet First Mate that watches every worker session. Reports only when something needs you; relays your orders to the right agent.
- **Work view** — all worker panes tiled automatically in one place (`Cmd+2`). No hunting.
- **Multi-harness** — Claude Code, Kiro, opencode, Codex. One terminal, any agent.
- **Session restore** — on restart, Brain offers to bring back your last crew with a single `y`.
- **Shared memory** — every harness boots with your skills and context already loaded.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/kaji-terminal/main/install.sh | bash
```

Open Kaji. The Brain greets you. Tell it what to build.

---

## Thanks

Built on the shoulders of:

- [Kaku](https://github.com/tw93/Kaku) — the beautiful macOS terminal this is forked from
- [WezTerm](https://wezfurlong.org/wezterm/) — the GPU-accelerated terminal engine underneath
- [Ghostty](https://ghostty.org) — for pushing the terminal space forward

---

<div align="center">
  <sub>Part of <a href="https://github.com/interesting-vibe-coding">interesting-vibe-coding</a> · MIT</sub>
</div>
