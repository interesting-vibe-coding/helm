# Helm Roadmap

> Agent-native terminal. You steer — agents execute.
> Last updated: 2026-06-09

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

## V1 Execution Plan (updated 2026-06-08)

Concrete, prioritized task list toward V1. Tiers by impact: **P0** = correctness / data-loss prevention, **P1** = core UX, **P2** = polish.

### ✅ Shipped this week
- **Scroll no longer crashes** — `mouse_common` called `[NSEvent clickCount]` on scroll-wheel events, raising an uncaught NSException that aborted the app. Now guarded to press/release only. (PR #92)
- **Brain TCC prompt gone** — `claude --strict-mcp-config` + empty mcp-config so the Brain stops reading Claude Desktop's config (the cross-app read that triggered the macOS "access other apps' data" popup). (PR #92)
- **4-dot view compass** — top bar shows a centered Brain · Work · Monitor · Terminal compass; active view lit in Helm purple. Dropped the verbose cheat-sheet and redundant per-tab dots. (PR #93)
- **Cmd+1/2/3/4 are view SLOTS, not new sessions** — Cmd+4 Terminal is a dedicated free shell (same pane each press); Cmd+2 Work is agent-sessions-only and shows a calm "No active session" hint when nothing runs. Work / Terminal / empty are distinct slots. (PR #93)
- **Dark-only colors fixed** — pinned `color_scheme = 'Kaku Dark'`. Following macOS appearance referenced an undefined `Kaku Light` in Light/Auto mode, erroring the whole config and dropping warm colors + fonts. (PR #93)

### ✅ Shipped 2026-06-08 (evening)
- **Cmd+W close semantics + dynamic compass** — per-view close (Brain→quit w/ confirm, Work→close session, Monitor/Terminal→close); compass draws one dot per live view. (PR #95)
- **Brain session-tracking crash fixed** — `helm-brain` track called `table.concat` on `get_lines_as_text` (which returns a String), erroring every tick on any agent pane and breaking session tracking + tab fallback. (PR #96)
- **Kaku Light / Auto fully adapted** — ported `Kaku Light` palette + appearance-resolve; theme-aware window_frame / tab_bar / status compass; settings TUI (`helm config`) now recovers theme intent from the config file when `color_scheme` is unevaluated (was painting pure black on light systems); config_tui title `Kaku`→`Helm`; active compass dot is Anthropic orange on cream; `foreground_color_overrides` for legible Claude text on cream. (PR #97)
- **Blank tab titles (no cwd leak)** — the compass is the single source of tab identity; the engine no longer falls back to the pane cwd (which surfaced `Users/Users/Users/` after the settings window closed). (PR #101)
- **Upstream Kaku fixes ported** — #448 scroll snap-to-bottom (no more jump-to-top during long AI output, PR #101); #446/#450 powerline separators keep their color, exempt block glyphs from min-contrast (PR #102); #449 Cmd+Q close-confirmation scoped to the foreground process group, so background daemons like gitstatusd don't force a prompt at an idle shell (PR #103); #452 repaint after resize + suppress phantom second window on cold start (PR #104).
- **Helm ⟂ Kaku isolation confirmed** — distinct bundle id (`dev.helm.app` vs `fun.tw93.kaku`), config dirs, bundled binary; Kaku.app untouched. Reinstalled upstream Kaku V0.12.1 cleanly.

### P0 — correctness / prevent loss
- [x] **Close-confirmation guard.** (PR #95) Was `window_close_confirmation = NeverPrompt` and there's no Cmd+W binding — a misclick can kill running agents with no prompt. Add a Helm-branded confirm, only when an agent session is actually running. (gated on the Cmd+W discussion below)
- [ ] **Core agent loop, end-to-end.** Manually walk the whole chain: spawn worker → Monitor (helm-top) shows it → Brain `notify_waiting` fires → session restore after restart. List and fix what's broken.

### P1 — core UX
- [ ] **Window geometry persistence** — remember last size/position instead of the fixed 110×22 on every launch.
- [x] **Cmd+W semantics** — per-view close defined + implemented (Brain quits w/ confirm, Work closes session, Monitor/Terminal close). (PR #95)
- [ ] **First-run onboarding + boot-into-Brain** — confirm the cold-start flow is smooth, first_run clean, no stray permission popups.

### P2 — polish
- [x] **Scroll regression test in CI** — `term`-crate scrollback unit tests wired into Cargo CI. (PR #94)
- [ ] **Compass centering** — `BUTTON_CELLS=8` fudge for the integrated-buttons offset; good enough now, revisit if it drifts at other window sizes.
- [ ] **Empty Work state** — currently a non-interactive branded hint; option to make it input-capable (minus the generic fish greeting) if that reads better.

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

> ⚠️ **Under redesign** — see [`BRAIN_DESIGN.md`](BRAIN_DESIGN.md). Open
> question: is the Brain an LLM orchestrator (the differentiator) or a
> rules-only visualization layer (marginal over DIY multi-session)? Planning is
> out of scope (the user always decides next steps). The no-regret move is the
> shared substrate — per-session state + an append-only event log — under either
> framing; the top layer is an experiment pending a token-cost measurement.

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

> **Roadmap endgame — mobile remote control.** The desktop becomes a controlled
> endpoint; a phone app steers it (cf. Anthropic's remote control). This is why
> the Brain is designed as a *client of a headless engine* (see
> [`BRAIN_DESIGN.md`](BRAIN_DESIGN.md)) — the phone is just another client of the
> same engine API. It favors an engine whose server already serves network
> clients (Goose's `goosed`), and needs a relay/tunnel + auth (`kaku-relay`).

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
