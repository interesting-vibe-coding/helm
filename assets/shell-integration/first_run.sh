#!/bin/bash
# Helm First Run Experience
set -euo pipefail

CONFIG_DIR="$HOME/.config/helm"
LEGACY_CONFIG_DIR="$HOME/.config/kaku"
# One-time, non-destructive migration: if Helm's config dir doesn't exist yet
# but a legacy Kaku dir does, copy it over so existing onboarding state
# (state.json, brain.conf, …) carries forward. The legacy dir is left intact so
# a real Kaku install is never disturbed. Runs at most once (helm dir absent).
if [[ ! -d "$CONFIG_DIR" && -d "$LEGACY_CONFIG_DIR" ]]; then
  if cp -R "$LEGACY_CONFIG_DIR" "$CONFIG_DIR" 2>/dev/null; then
    echo "Migrated config from $LEGACY_CONFIG_DIR to $CONFIG_DIR (legacy dir kept)." >&2
  fi
fi
STATE_FILE="$CONFIG_DIR/state.json"
# Helm's session-tracking dir, where the GUI writes runtime.json (the snapshot
# the Brain/Monitor read). Create it up front: the lua writer uses io.open(...,
# 'w') which silently fails if the parent dir is missing, leaving the Monitor
# permanently empty.
mkdir -p "$HOME/.helm/sessions" 2>/dev/null || true
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPT="$SCRIPT_DIR/state_common.sh"

[[ -f "$COMMON_SCRIPT" ]] && source "$COMMON_SCRIPT"

CURRENT_CONFIG_VERSION="$(read_bundled_config_version "$SCRIPT_DIR" 2>/dev/null || echo 0)"
trap 'persist_config_version 2>/dev/null || true' EXIT

# Resolve resources dir
if [[ -f "$SCRIPT_DIR/setup_zsh.sh" ]]; then
  RESOURCES_DIR="$SCRIPT_DIR"
elif [[ -f "/Applications/Helm.app/Contents/Resources/setup_zsh.sh" ]]; then
  RESOURCES_DIR="/Applications/Helm.app/Contents/Resources"
else
  echo "Warning: Helm resources not found, skipping shell setup."
  exit 0
fi

# ── Detect shell ──────────────────────────────────────────────────────────────
detect_shell() {
  local shell_path="${SHELL:-/bin/zsh}"
  case "$shell_path" in
    *fish) echo "fish" ;;
    *zsh)  echo "zsh"  ;;
    *bash) echo "bash" ;;
    *)     echo "zsh"  ;;
  esac
}
DETECTED_SHELL="$(detect_shell)"

# ── Helpers ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; PURPLE='\033[38;5;141m'; DIM='\033[2m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
info() { echo -e "  ${YELLOW}→${NC} $*"; }

# Purple ghost mascot — terminal-prompt face (round eyes + >_ mouth)
ghost() {
  printf "${PURPLE}"
  cat <<'GHOST'
    .-~~~~~~~~~-.
   |  (o)   (o)  |
   |     >_      |
   |             |
    `~-^-^-^-^-~`
GHOST
  printf "${NC}"
}

brew_install() {
  local pkg="$1"
  if command -v brew >/dev/null 2>&1; then
    brew install "$pkg" >/dev/null 2>&1 && ok "Installed $pkg" || info "$pkg install failed (continuing)"
  else
    info "Homebrew not found, skipping $pkg"
  fi
}

# ── Already configured? ───────────────────────────────────────────────────────
if should_skip_first_run 2>/dev/null; then
  check_and_apply_config_updates "$RESOURCES_DIR" "$DETECTED_SHELL" 2>/dev/null || true
  exit 0
fi

# ── Welcome ───────────────────────────────────────────────────────────────────
clear
echo ""
ghost
echo ""
echo -e "  ${BOLD}Helm${NC} — you steer, agents execute."
echo ""
echo -e "  Shell: ${BOLD}${DETECTED_SHELL}${NC} ✓"
echo ""

# -- Cross-harness memory setup
# ~/.kiro/AGENTS.md is the master memory file.
# Symlink it into every harness's convention path so they all share context.
MASTER_MEMORY="$HOME/.kiro/AGENTS.md"
if [[ -f "$MASTER_MEMORY" ]]; then
  # Claude Code
  mkdir -p "$HOME/.claude"
  [[ ! -e "$HOME/.claude/CLAUDE.md" ]] && ln -sf "$MASTER_MEMORY" "$HOME/.claude/CLAUDE.md"
  # opencode
  mkdir -p "$HOME/.config/opencode"
  [[ ! -e "$HOME/.config/opencode/AGENTS.md" ]] && ln -sf "$MASTER_MEMORY" "$HOME/.config/opencode/AGENTS.md"
  # Codex
  mkdir -p "$HOME/.codex"
  [[ ! -e "$HOME/.codex/AGENTS.md" ]] && ln -sf "$MASTER_MEMORY" "$HOME/.codex/AGENTS.md"
  ok "Cross-harness memory linked ($(ls -1 $HOME/.claude $HOME/.config/opencode $HOME/.codex 2>/dev/null | grep -c AGENTS)/${MASTER_MEMORY:+3} harnesses)"
fi

# ── Cross-harness skills (open Agent Skills standard) ─────────────────────────
# Install the bundled helm-first-mate skill into each harness's skill dir.
# This skill is Helm-specific and lives ONLY in the Helm app bundle (the single
# source of truth) — it is intentionally NOT added to the personal skills hub
# (~/workspace/My-Skills), since a product-specific skill should stay in its own
# repo and not be loaded by every unrelated session. We link each harness dir
# DIRECTLY at the bundled skill (no inter-dir hop), so this works regardless of
# where the personal hub lives or whether ~/.agents exists.
FIRST_MATE_SKILL="$RESOURCES_DIR/skills/helm-first-mate"
if [[ -d "$FIRST_MATE_SKILL" ]]; then
  skill_target="$(cd "$FIRST_MATE_SKILL" && pwd -P)"
  link_first_mate() {
    local dir="$1" src="$2"
    mkdir -p "$dir" 2>/dev/null || return 0
    if [[ -e "$dir/helm-first-mate/SKILL.md" \
          && "$(cd "$dir/helm-first-mate" 2>/dev/null && pwd -P)" == "$skill_target" ]]; then
      return 0  # already resolves to our skill (directly or via a dir symlink)
    fi
    ln -sfn "$src" "$dir/helm-first-mate" 2>/dev/null \
      && ok "First Mate skill linked ($dir/helm-first-mate)"
  }
  # All link directly at the bundled skill (single source of truth).
  link_first_mate "$HOME/.agents/skills" "$FIRST_MATE_SKILL"   # Codex user-scope
  [[ -d "$HOME/.kiro"   ]] && link_first_mate "$HOME/.kiro/skills"   "$FIRST_MATE_SKILL"
  [[ -d "$HOME/.claude" ]] && link_first_mate "$HOME/.claude/skills" "$FIRST_MATE_SKILL"
fi

# ── Choose your Brain ─────────────────────────────────────────────────────────
# The Brain is the First Mate that orchestrates all your agents. Let the user
# pick which harness powers it; persist to ~/.config/helm/brain.conf so the
# launcher (tools/helm-brain/launch-brain.sh) can honor the choice.
# Read a single keypress into the global REPLY_KEY. Decodes escape sequences
# (arrow keys arrive as ESC [ A/B). Empty result = Enter. bash 3.2 safe.
# Guarded with `|| true` so a timed-out/EOF read never trips `set -e`.
read_key() {
  local key="" rest=""
  IFS= read -rsn1 key 2>/dev/null || true
  if [[ "$key" == $'\x1b' ]]; then
    read -rsn2 -t 0.01 rest 2>/dev/null || true
    key+="$rest"
  fi
  REPLY_KEY="$key"
}

choose_brain() {
  local keys=() labels=()
  command -v claude   >/dev/null 2>&1 && { keys+=("claude");   labels+=("Claude Code"); }
  command -v kiro-cli >/dev/null 2>&1 && { keys+=("kiro");     labels+=("Kiro"); }
  command -v opencode >/dev/null 2>&1 && { keys+=("opencode"); labels+=("opencode"); }
  command -v codex    >/dev/null 2>&1 && { keys+=("codex");    labels+=("Codex"); }

  if [[ ${#keys[@]} -eq 0 ]]; then
    info "No agent harness found — install one later, then it powers your Brain:"
    echo -e "    ${DIM}brew install claude · npm i -g opencode-ai${NC}"
    return
  fi

  echo -e "${BOLD}  Choose your Brain${NC}"
  echo -e "  ${DIM}Your Brain is the First Mate that orchestrates all your agents.${NC}"

  # Default selection (0-based): prefer claude, else the first installed harness.
  local n=${#keys[@]} sel=0 default_idx=0 i
  for i in "${!keys[@]}"; do
    [[ "${keys[$i]}" == "claude" ]] && { sel=$i; default_idx=$i; }
  done

  # Persist the choice + report. Shared by the interactive and fallback paths.
  _brain_commit() {
    local picked="${keys[$1]}"
    mkdir -p "$CONFIG_DIR"
    printf 'BRAIN_HARNESS=%s\n' "$picked" > "$CONFIG_DIR/brain.conf"
    ok "Brain: ${BOLD}${picked}${NC} ${DIM}(~/.config/helm/brain.conf)${NC}"
  }

  # NON-TTY / piped: pick the default silently, no interaction, no hang.
  if [[ ! -t 0 || ! -t 1 ]]; then
    _brain_commit "$default_idx"
    return
  fi

  echo -e "  ${DIM}↑/↓ move · Enter select · q keep default${NC}"
  echo ""

  # Hide cursor; restore it even on Ctrl-C.
  printf '\033[?25l'
  trap 'printf "\033[?25h"; exit 130' INT

  local first=1
  while true; do
    [[ $first -eq 0 ]] && printf '\033[%dA' "$n"
    first=0
    for i in "${!keys[@]}"; do
      local tag=""
      [[ "${keys[$i]}" == "claude" ]] && tag=" ${DIM}(recommended)${NC}"
      printf '\033[2K'
      if [[ $i -eq $sel ]]; then
        echo -e "  ${PURPLE}›${NC} ${PURPLE}${labels[$i]}${NC}${tag}"
      else
        echo -e "    ${labels[$i]}${tag}"
      fi
    done

    read_key
    case "$REPLY_KEY" in
      $'\x1b[A'|k) sel=$(( (sel - 1 + n) % n )) ;;
      $'\x1b[B'|j) sel=$(( (sel + 1) % n )) ;;
      q|Q)         sel=$default_idx; break ;;
      '')          break ;;   # Enter
    esac
  done

  trap - INT
  printf '\033[?25h'
  _brain_commit "$sel"
}
choose_brain
echo ""

# ── Shell + tools ─────────────────────────────────────────────────────────────
echo -e "${BOLD}  Setting up your shell…${NC}"

# Shell integration (quiet)
if [[ "$DETECTED_SHELL" == "fish" && -f "$RESOURCES_DIR/setup_fish.sh" ]]; then
  bash "$RESOURCES_DIR/setup_fish.sh" >/dev/null 2>&1 || true
elif [[ -f "$RESOURCES_DIR/setup_zsh.sh" ]]; then
  bash "$RESOURCES_DIR/setup_zsh.sh" >/dev/null 2>&1 || true
fi

# Required tools — install only what's missing, quietly
if command -v brew >/dev/null 2>&1; then
  command -v starship >/dev/null 2>&1 || brew install starship  >/dev/null 2>&1 || true
  command -v zoxide   >/dev/null 2>&1 || brew install zoxide    >/dev/null 2>&1 || true
  command -v delta    >/dev/null 2>&1 || brew install git-delta >/dev/null 2>&1 || true
fi

# Wire prompt + zoxide into fish
if [[ "$DETECTED_SHELL" == "fish" ]]; then
  FC="$HOME/.config/fish/config.fish"
  if [[ -f "$FC" ]]; then
    grep -q 'starship init fish' "$FC" || printf '\nstarship init fish | source\n' >> "$FC"
    grep -q 'zoxide init fish'   "$FC" || printf 'zoxide init fish | source\n'   >> "$FC"
  fi
fi
ok "Shell ready ${DIM}· starship · zoxide · delta${NC}"
echo ""

# ── Optional tools ────────────────────────────────────────────────────────────
# A visible, transparent multi-select. Nothing is pre-checked (opt-in): the user
# decides what gets installed. SPACE toggles, Enter confirms.
optional_tools() {
  local names=("lazygit")
  local descs=("lazygit — terminal git UI")
  local n=${#names[@]} checked=() i
  for i in "${!names[@]}"; do checked+=(0); done

  echo -e "${BOLD}  Optional tools${NC}"

  # NON-TTY / piped: skip silently with a one-line hint.
  if [[ ! -t 0 || ! -t 1 ]]; then
    echo -e "  ${DIM}Optional: brew install lazygit${NC}"
    echo ""
    return
  fi

  echo -e "  ${DIM}↑/↓ move · Space toggle · Enter confirm${NC}"
  echo ""

  printf '\033[?25l'
  trap 'printf "\033[?25h"; exit 130' INT

  local sel=0 first=1
  while true; do
    [[ $first -eq 0 ]] && printf '\033[%dA' "$n"
    first=0
    for i in "${!names[@]}"; do
      local box="[ ]"
      [[ "${checked[$i]}" -eq 1 ]] && box="[x]"
      printf '\033[2K'
      if [[ $i -eq $sel ]]; then
        echo -e "  ${PURPLE}›${NC} ${PURPLE}${box}${NC} ${descs[$i]}"
      else
        echo -e "    ${box} ${descs[$i]}"
      fi
    done

    read_key
    case "$REPLY_KEY" in
      $'\x1b[A'|k) sel=$(( (sel - 1 + n) % n )) ;;
      $'\x1b[B'|j) sel=$(( (sel + 1) % n )) ;;
      ' ')         checked[$sel]=$(( 1 - checked[$sel] )) ;;
      '')          break ;;   # Enter
      q|Q)         break ;;
    esac
  done

  trap - INT
  printf '\033[?25h'

  # Install each checked tool that's missing; skipped ones stay silent.
  for i in "${!names[@]}"; do
    if [[ "${checked[$i]}" -eq 1 ]]; then
      if command -v "${names[$i]}" >/dev/null 2>&1; then
        ok "${names[$i]} already installed"
      else
        info "installing ${names[$i]}"
        brew_install "${names[$i]}"
      fi
    fi
  done
}
optional_tools
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────
if [[ "${HELM_LANG:-en}" == "zh" ]]; then
  echo -e "${GREEN}${BOLD}  ✓ 一切就绪${NC}"
  echo ""
  echo -e "  ${DIM}打开 Helm 直接进入 Brain，告诉它做什么就好。${NC}"
  echo -e "  ${DIM}⌘1 Brain   ⌘2 Work   ⌘3 Monitor   ⌘/ 帮助${NC}"
else
  echo -e "${GREEN}${BOLD}  ✓ You're all set${NC}"
  echo ""
  echo -e "  ${DIM}Helm opens straight into the Brain — just tell it what to build.${NC}"
  echo -e "  ${DIM}⌘1 Brain   ⌘2 Work   ⌘3 Monitor   ⌘/ Help${NC}"
fi
echo ""

persist_config_version 2>/dev/null || true
