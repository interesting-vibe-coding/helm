<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Kaji" />
  <h1>Kaji</h1>
  <p><em>The agent-native terminal. You steer — agents execute.</em></p>

  <p>
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/macOS-Apple%20Silicon%20%2B%20Intel-lightgrey?style=flat-square" alt="macOS">
  </p>
</div>

<div align="center">
  <b>English</b> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.pt-BR.md">Português</a>
</div>

---

Most terminals assume one human, one session. **Kaji assumes you are orchestrating a fleet of agents** — they do the work, surface what needs you, and wait for your call.

### Zero friction

You shouldn't babysit a terminal. No hunting for which pane needs input, no losing your place between tools, no setup before you can start. Install, open, and you're already talking to your agents. **You make the calls; they do everything in between.**

### Meet your First Mate

Running ten agents still means watching ten panes. Kaji's **Brain** removes that last bit of friction: instead of juggling N agents, you talk to **one**.

The Brain is a Sonnet orchestrator. It watches every session for you — who's working, who's waiting, what they're costing — reports only when something actually needs you, and relays your orders to the right agent, always asking before anything lands.

> **N agents → one conversation.** You stop scanning a wall of terminals and start steering through a mate who knows the whole crew.

### Three views, one keystroke each

**Brain** — talk to your First Mate.  
**Work** — every agent tiled in one place; jump in when you need to.  
**Terminal** — a plain shell, always there.

Flip between them instantly. Kaji surfaces the keys when you need them — nothing to memorize.

---

## Why Kaji?

**舵** (kaji) is Japanese for *helm* — the rudder that steers the ship.

The name is deliberate. You are not another agent in the system; you are the one holding the rudder. Kaji keeps that distinction physical: every session opens into the Brain, every agent reports back to you, and the Work view tiles their output so you see the whole crew at a glance — without steering each one yourself.

The lineage runs deep: Kaku → Kaji, both named after Japanese concepts, both rooted in WezTerm's GPU rendering. Kaji picks up where Kaku left off and goes further — toward a terminal built around *directing* rather than *doing*.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

Open Kaji and it walks you through a quick setup, then drops you straight into the Brain. Tell it what to work on.

<details>
<summary>Build from source</summary>

```bash
git clone https://github.com/interesting-vibe-coding/helm
cd helm
PROFILE=debug ./scripts/build.sh --app-only
open dist/Kaji.app
```
</details>

---

<div align="center">
  <sub>A focused fork of <a href="https://github.com/tw93/Kaku">Kaku</a> · built on <a href="https://wezfurlong.org/wezterm/">WezTerm</a> · MIT</sub><br/>
  <sub>Part of <a href="https://github.com/interesting-vibe-coding">interesting-vibe-coding</a></sub>
</div>
