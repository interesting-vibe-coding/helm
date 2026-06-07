# Helm Roadmap

> Agent-native terminal. You steer — agents execute.
> Last updated: 2026-06-07

---

## Competitive Landscape

| Product | Base | Agent Features | Status |
|---------|------|----------------|--------|
| **Helm** | WezTerm/Kaku (Rust) | Memory sharing, shortcut→slash cmd, harness launcher | 🟡 Early |
| **cmux** | Ghostty (Swift/AppKit) | Notification rings, sidebar, in-app browser, hooks setup, session restore | 🟢 21k stars, active |
| **Ghostty** | Native (Zig) | None — just fast terminal | 🟢 Baseline |
| **Kaku** | WezTerm (Rust) | AI chat (Cmd+L), error recovery, # nl→cmd | 🟢 Our fork |
| **Warp** | Electron | AI completions | 🔴 Not our direction |

**Key insight**: cmux nailed the *notification* layer (when an agent needs you). Helm's edge should be the *memory + skills* layer (what agents know) and the *orchestration* layer (multiple harnesses as one workspace). These are complementary, not competing.

---

## Current State — v0.3.1 (2026-06-07)

Helm is in **V0 — daily-usable, actively iterating**. Public repo, CI green.

### ✅ Shipped
- **The Brain (First Mate)** — a Sonnet orchestrator. Watches all workers (state + token usage), reports only when something needs you, routes instructions with a confirm gate, and can **spawn worker sessions itself** (split work by project). Backend harness is picked during onboarding (claude / kiro / opencode / codex; claude is the default).
- **3-view shell** — `Cmd+1` Brain · `Cmd+2` Workspace · `Cmd+3` Monitor (htop-style session list). `Cmd+/` toggles the help bar.
- **Boot into the Brain** on launch + **session restore** (rebuilds last run's panes: same dirs + harnesses; `claude --continue` where supported).
- **Guided onboarding** that actually runs on first launch: animated ghost mascot, shell setup, cross-harness memory symlink, and the Choose-your-Brain picker.
- **One-line install** — `curl … | bash` from the latest release.
- **Ghost logo** (terminal-prompt face) + clean namespaced `kaku.lua`.
- **Tools** (all bundled in the .app): `helm-brain` (sessions/send/notify/spawn), `helm-top` (monitor), `helm-quota`, plus CLI utilities.

### 🛣️ Road to V1
V1 ships when Helm is something we use **daily and comfortably** — then we tag it, announce, and promote. Criteria:
- [ ] Brain day-to-day: spawn / report / route confirm-gate all smooth, zero noise
- [ ] 3-view navigation feels natural in real use
- [ ] Session restore reliable across reboots
- [ ] Onboarding polished and truly out-of-the-box
- [ ] No visible bugs or terminal noise
- [ ] Several days of comfortable daily driving

Until then we keep iterating in the **V0.x** series.

---

## Helm Vision: The Agent OS

> Four layers that together make Helm an operating system for AI agents.

### The View Shell (current UX)

The Agent OS layers are driven through **three views** — the navigation shell you live in. Each is one keystroke away, and `Cmd+/` toggles a bottom help bar with the current key bindings:

- **`Cmd+1` Brain** — your First Mate orchestrator (Layer 4). One conversation, N agents.
- **`Cmd+2` Workspace** — where you and your agents actually work (the panes themselves).
- **`Cmd+3` Monitor** — an htop-style overview of every session: state, runtime, tokens (the visible face of Layers 1–2).

The views are the UX shell; the four layers below are the machinery they expose. Zero friction, out of the box — you flip between steering (Brain), doing (Workspace), and overseeing (Monitor) without thinking about it.

```
┌─────────────────────────────────────────────────┐
│  Layer 4: The Brain (First Mate)  ⭐ headline    │
│  Sonnet orchestrator — 1 conversation, N agents │
├─────────────────────────────────────────────────┤
│  Layer 3: Shared Context                        │
│  chat history + memory + skills across harnesses│
├─────────────────────────────────────────────────┤
│  Layer 2: Status Awareness                      │
│  runtime, active sessions, quota per harness    │
├─────────────────────────────────────────────────┤
│  Layer 1: Session Scheduler                     │
│  N sessions, M visible panes, LRU swap          │
└─────────────────────────────────────────────────┘
```

### Layer 4 — The Brain / First Mate (current headline feature)

**The idea**: You shouldn't have to watch N panes. Talk to one Sonnet orchestrator — the **First Mate** — and let it watch the crew. It builds on Layers 1–3: it reads worker **state** from the Session Scheduler and **token usage** from Status Awareness, and acts through the same mux CLI the scheduler uses.

**What it does**:
- **Watches** — polls every worker session's state (working / waiting / background) and tokens-today, surfacing only what needs you.
- **Reports** — a single feed: who's blocked, who's burning quota, who finished. macOS notifications when a worker needs input.
- **Routes** — you give one instruction in natural language; the First Mate picks the right pane and injects it, behind a **confirm gate** so nothing lands without your nod.

**Plumbing** (shipped): `helm-brain` CLI under `tools/helm-brain/` —
`helm-brain sessions` (merges `kaku cli list` + `runtime.json` state + `quota.py` tokens → JSON), `helm-brain send <pane> "<text>"`, `helm-brain notify`, `helm-brain watch`. These are the Brain's eyes and hands; the Sonnet orchestrator is the mind on top.

**Toggle**: `Cmd+Shift+Return` switches between the Brain view and your workers.

**Why it matters**: every other agent terminal scales attention linearly — more agents, more panes to scan. The Brain collapses that to **O(1)**: one conversation regardless of fleet size.

### Layer 3 — Shared Context

**The idea**: Like an emperor reviewing memorials — 20 sessions running in the background, 2 panes visible. Sessions swap in/out based on LRU/LFU, like OS virtual memory.

**Design**:
- `SessionScheduler` in mux layer: maintains `active_set` (2-3 visible panes) + `background_pool` (N PTY processes, alive but hidden)
- Trigger to swap in: agent emits waiting signal → scheduler brings it to foreground, pushes idle session to background
- PTY process stays alive in background (no state lost), just pane is hidden
- LRU: least-recently-interacted session gets swapped out first
- User sees: a compact session list (like phone notifications), taps one to bring to front

**Why it matters**: Today every terminal is 1:1 between sessions and visible panes. This breaks that constraint.

### Layer 2 — Status Awareness

**Per-session data to show**:
- Runtime (PTY spawn timestamp → now)
- State: Working / Waiting / Idle / Done (harness output pattern detection, reuse paws hooks)
- Quota remaining: parse `~/.claude/` usage JSON, opencode session metadata

**Implementation**: Lua-side HUD overlay on each pane, updated every few seconds.

### Layer 3 — Shared Context

**Memory + Skills**: ✅ Already done via symlinks.

**Chat History**: Three formats, all convertible to unified schema:

```
Claude Code: ~/.claude/projects/<path>/<session>.jsonl
             {"type":"user/assistant", "content": ...}

kiro:        ~/.kiro/sessions/cli/<session>.json + .jsonl
             {session_id, cwd, title, messages: [...]}

opencode:    ~/.local/share/opencode/storage/message/<ses>/<msg>.json
             {id, sessionID, role, model, summary}
```

**Unified schema**:
```json
{
  "session_id": "...",
  "harness": "claude-code|kiro|opencode|codex",
  "cwd": "/path/to/project",
  "started_at": "...",
  "messages": [
    {"role": "user|assistant", "content": "...", "timestamp": "..."}
  ]
}
```

A background converter indexes all harness histories into `~/.helm/sessions/`. Any harness can then read recent context from any other harness's session.

---

## Next Steps (Priority Order)

### 1. Cross-Harness Memory — Bake Into Helm (HIGH)

**Current state**: Manually symlinked on your machine. Not automatic for new users.

**What to do**: In `first_run.sh`, auto-create the symlinks:
```bash
# Claude Code
mkdir -p ~/.claude
ln -sf ~/.kiro/AGENTS.md ~/.claude/CLAUDE.md

# opencode  
mkdir -p ~/.config/opencode
ln -sf ~/.kiro/AGENTS.md ~/.config/opencode/AGENTS.md

# Codex
mkdir -p ~/.codex
ln -sf ~/.kiro/AGENTS.md ~/.codex/AGENTS.md
```
And create `~/.kiro/AGENTS.md` with a starter template if it doesn't exist.

**Why symlink is the right approach**: Each harness has a convention path. A single source of truth (`~/.kiro/AGENTS.md`) propagates everywhere. This is exactly what cmux's `cmux hooks setup` does, but we do it automatically on first run. ✅ Correct design.

**Skills**: Same pattern — symlink `~/.kiro/skills/` → `~/.config/opencode/skills/` etc.

---

### 2. Agent Notification System (HIGH — cmux's killer feature)

cmux uses **OSC 9/99/777 terminal sequences** + a sidebar with notification rings.

For Helm (simpler first version):
- Detect when a pane's agent prints "waiting for input" / prompt appears
- Flash the tab / add a visual indicator
- Surface it in the Brain (`Cmd+1`) and Monitor (`Cmd+3`) views rather than auto-jumping the user

Kaku already has `Alert::SetUserVar` in mux — this is the hook to build on.

---

### 3. Harness Launcher (MEDIUM)

One shortcut to spawn a new pane with a chosen harness:
- `Cmd+Shift+K` → picker: kiro / claude-code / opencode
- Uses `kaku cli split-pane -- kiro-cli chat`

---

### 4. Logo (LOW — aesthetic, not functional)

Current: geometric gold helm wheel, needs refinement.
Direction: cute/minimal character (user likes ghost-like mascots), dark theme, high contrast.
Options to try: minimalist ghost with helm wheel, or abstract geometric that reads as both a wheel and something playful.

---

### 5. Ghostty — What's Worth Learning

Ghostty's technical advantages over WezTerm:
- **2-5x faster rendering** (Metal on macOS vs WebGPU)
- **Better macOS native feel** (AppKit integration)
- **Kitty Graphics Protocol** (image display in terminal)
- Simpler config (plain text, no Lua)

**For Helm**: Not worth forking Ghostty now. WezTerm's Lua API is essential for our agent orchestration layer. Consider adopting libghostty for rendering in a future version (cmux does this).

---

## Credits

Helm is built on:
- [Kaku](https://github.com/tw93/Kaku) by Tw93 — the immediate foundation (thank you 🙏)
- [WezTerm](https://wezfurlong.org/wezterm/) by Wez Furlong — the terminal engine
- [Ghostty](https://ghostty.org) by Mitchell Hashimoto — inspired fast native terminal design
- [cmux](https://github.com/manaflow-ai/cmux) — showed the way for agent notifications
