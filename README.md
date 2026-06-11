<div align="center">
  <img src="assets/kaji-logo.png" width="110" alt="Kaji" />
  <h1>Kaji</h1>
  <p><em>Mission control for your AI coding agents — in the terminal, and in your pocket.</em></p>
  <p><a href="README.zh.md">中文</a></p>
</div>

---

Kaji runs a crew of coding agents — Claude Code, Kiro, opencode, Codex — side by side, and gives you one calm surface to steer them all: every worker visible at once, quota at a glance, and a phone page that works from anywhere. You hold the rudder (舵, *kaji*); the agents row.

> Your prefrontal cortex is finite.
> Stop spending it switching context between agents. `(ᴗ‿ᴗ)`

<!-- ![Kaji fleet — phone cockpit and Work view](assets/screenshot.png) -->

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/kaji/main/install.sh | bash
```

Open Kaji. The Brain greets you. Tell it what to build.

## What you get

**One terminal, every agent.** Workers tile automatically in a single Work view
(`Cmd+2`) — claude next to codex next to kiro, no tab hunting. Each harness
boots with your shared memory and skills already loaded.

**A fleet you can read at a glance.** The cockpit (`Cmd+1`) orders sessions
most-neglected first: amber means a worker is waiting on you, teal means it's
working. Select a worker, press ⏎, type — your instruction lands in its pane.

**Quota where you can see it.** Tokens spent today per harness, and real
remaining-quota percentages where the harness exposes them — before you burn
an evening's budget on the wrong model.

**Your fleet, from your phone.** `kaji-brain serve` + the built-in relay put
the same cockpit in your phone's browser — state, quota, send, spawn — over
plain HTTPS. No inbound ports on your Mac, no VPN slot on your phone, works
behind any proxy. See [docs/remote.md](docs/remote.md).

**Engine-agnostic by design.** The Brain is a thin service (CLI + HTTP + MCP)
over an append-only event substrate — not a model. Any harness can be a
worker; any client (terminal cockpit, phone, a script, an LLM if you want one)
can hold the rudder.

## Why this shape

Remote-control-your-agent is a crowded space — but every player locks you to
one vendor's agent. Kaji's bet is the opposite: the hard part isn't talking to
one agent, it's *running a fleet of different ones* without shredding your
attention. So the trunk is harness-agnostic fleet control with shared
memory — and the terminal it lives in is built for exactly that.

---

Built on the shoulders of [Kaku](https://github.com/tw93/Kaku),
[WezTerm](https://wezfurlong.org/wezterm/), and the push from
[Ghostty](https://ghostty.org). MIT — see [LICENSE.md](LICENSE.md).

<div align="center">
  <sub>Part of <a href="https://github.com/interesting-vibe-coding">interesting-vibe-coding</a> · MIT</sub>
</div>
