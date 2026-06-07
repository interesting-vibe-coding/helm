#!/bin/bash
# Helm First Run Experience
set -euo pipefail

CONFIG_DIR="$HOME/.config/kaku"
STATE_FILE="$CONFIG_DIR/state.json"
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

# ── Choose your Brain ─────────────────────────────────────────────────────────
# The Brain is the First Mate that orchestrates all your agents. Let the user
# pick which harness powers it; persist to ~/.config/kaku/brain.conf so the
# launcher (tools/helm-brain/launch-brain.sh) can honor the choice.
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
  echo ""

  # Default index: prefer claude, else the first installed harness.
  local default_idx=1 i
  for i in "${!keys[@]}"; do
    [[ "${keys[$i]}" == "claude" ]] && default_idx=$(( i + 1 ))
  done

  for i in "${!keys[@]}"; do
    local n=$(( i + 1 )) tag=""
    [[ "${keys[$i]}" == "claude" ]] && tag=" ${DIM}(recommended)${NC}"
    echo -e "    ${PURPLE}${n}${NC}  ${labels[$i]}${tag}"
  done
  echo ""

  local choice=""
  if [[ -t 0 && -t 1 ]]; then
    read -r -p "  Pick a number [${default_idx}]: " choice
    echo ""
  fi
  if [[ -z "$choice" || ! "$choice" =~ ^[0-9]+$ || "$choice" -lt 1 || "$choice" -gt ${#keys[@]} ]]; then
    choice="$default_idx"
  fi

  local picked="${keys[$(( choice - 1 ))]}"
  mkdir -p "$CONFIG_DIR"
  printf 'BRAIN_HARNESS=%s\n' "$picked" > "$CONFIG_DIR/brain.conf"
  ok "Brain: ${BOLD}${picked}${NC} ${DIM}(~/.config/kaku/brain.conf)${NC}"
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

# ── Done ──────────────────────────────────────────────────────────────────────
if [[ "${HELM_LANG:-en}" == "zh" ]]; then
  echo -e "${GREEN}${BOLD}  ✓ 一切就绪${NC}"
  echo ""
  echo -e "  ${DIM}打开 Helm 直接进入 Brain，告诉它做什么就好。${NC}"
  echo -e "  ${DIM}⌘1 Brain   ⌘2 Work   ⌘3 Monitor   ⌘/ 帮助${NC}"
  echo -e "  ${DIM}可选：brew install lazygit yazi${NC}"
else
  echo -e "${GREEN}${BOLD}  ✓ You're all set${NC}"
  echo ""
  echo -e "  ${DIM}Helm opens straight into the Brain — just tell it what to build.${NC}"
  echo -e "  ${DIM}⌘1 Brain   ⌘2 Work   ⌘3 Monitor   ⌘/ Help${NC}"
  echo -e "  ${DIM}Optional: brew install lazygit yazi${NC}"
fi
echo ""

persist_config_version 2>/dev/null || true
