# Helm Roadmap

> Agent-native terminal. You steer — agents execute.
> Last updated: 2026-06-06

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

## Current State (2026-06-06)

### ✅ Done
- Helm.app builds and runs (`PROFILE=debug ./scripts/build.sh --app-only`)
- Kaku strings replaced with Helm branding
- `Cmd+Shift+M` injects `/model` slash command → toggles sonnet ↔ opus in kiro chat
- `kc` abbr → `kiro-cli chat --trust-all-tools --agent default --effort medium`
- Ship helm-output-style skill (terminal output design spec)
- Cross-harness memory via symlink:
  - `~/.claude/CLAUDE.md → ~/.kiro/AGENTS.md` (Claude Code reads this)
  - `~/.kiro/AGENTS.md` = master memory file (steering/memory.md also symlinks here)

### 🟡 In Progress
- Logo (geometric gold helm wheel — needs more refinement)
- CI green on GitHub

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
- `Cmd+Shift+U` jumps to the pane needing attention

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
