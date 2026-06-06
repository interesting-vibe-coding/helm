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
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
info() { echo -e "  ${YELLOW}→${NC} $*"; }

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
if [[ "${HELM_LANG:-en}" == "zh" ]]; then
  echo -e "${BOLD}  🎯 欢迎使用 Helm${NC}"
  echo ""
  echo -e "  Shell: ${BOLD}${DETECTED_SHELL}${NC} ✓"
else
  echo -e "${BOLD}  🎯 Welcome to Helm${NC}"
  echo ""
  echo -e "  Shell: ${BOLD}${DETECTED_SHELL}${NC} ✓"
fi
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

# ── Shell integration ─────────────────────────────────────────────────────────
echo -e "${BOLD}  Setting up shell integration...${NC}"
if [[ "$DETECTED_SHELL" == "fish" ]]; then
  if [[ -f "$RESOURCES_DIR/setup_fish.sh" ]]; then
    bash "$RESOURCES_DIR/setup_fish.sh" && ok "Fish shell integration done"
  fi
else
  # zsh (or bash fallback)
  if [[ -f "$RESOURCES_DIR/setup_zsh.sh" ]]; then
    bash "$RESOURCES_DIR/setup_zsh.sh" && ok "Zsh shell integration done"
  fi
fi
echo ""

# ── Required tools (auto-install, no prompt) ──────────────────────────────────
echo -e "${BOLD}  Installing required tools...${NC}"
# Starship — smart prompt
if ! command -v starship >/dev/null 2>&1; then
  brew_install starship
else
  ok "starship (already installed)"
fi
if [[ "$DETECTED_SHELL" == "fish" ]]; then
  FISH_CONFIG="$HOME/.config/fish/config.fish"
  if [[ -f "$FISH_CONFIG" ]] && ! grep -q 'starship init fish' "$FISH_CONFIG"; then
    echo '' >> "$FISH_CONFIG"
    echo 'starship init fish | source' >> "$FISH_CONFIG"
    ok "starship init added to fish config"
  fi
fi
# Zoxide — smart cd
if ! command -v zoxide >/dev/null 2>&1; then
  brew_install zoxide
else
  ok "zoxide (already installed)"
fi
if [[ "$DETECTED_SHELL" == "fish" ]]; then
  FISH_CONFIG="$HOME/.config/fish/config.fish"
  if [[ -f "$FISH_CONFIG" ]] && ! grep -q 'zoxide init fish' "$FISH_CONFIG"; then
    echo '' >> "$FISH_CONFIG"
    echo 'zoxide init fish | source' >> "$FISH_CONFIG"
    ok "zoxide init added to fish config"
  fi
fi
# Delta — better git diff
if ! command -v delta >/dev/null 2>&1; then
  brew_install git-delta
else
  ok "delta (already installed)"
fi
echo ""

# ── Optional tools (ask) ──────────────────────────────────────────────────────
if [[ -t 0 && -t 1 ]]; then
  echo -e "${BOLD}  Optional tools:${NC}"
  echo "    lazygit  — terminal git UI        (Cmd+Shift+G)"
  echo "    yazi     — terminal file manager  (Cmd+Shift+Y)"
  echo ""
  read -r -p "  Install optional tools? [y/N] " OPT_ANSWER
  echo ""
  if [[ "${OPT_ANSWER,,}" == "y" ]]; then
    command -v lazygit >/dev/null 2>&1 && ok "lazygit (already installed)" || brew_install lazygit
    command -v yazi    >/dev/null 2>&1 && ok "yazi (already installed)"    || brew_install yazi
  else
    info "Skipped. You can install later: brew install lazygit yazi"
  fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
if [[ "${HELM_LANG:-en}" == "zh" ]]; then
  echo -e "${GREEN}${BOLD}  ✓ Helm 已就绪${NC}"
  echo ""
  echo -e "  \033[2m快捷键: Cmd+L → AI 对话  ·  Cmd+Shift+M → 切换模型  ·  Cmd+Shift+S → 会话列表\033[0m"
else
  echo -e "${GREEN}${BOLD}  ✓ Helm is ready${NC}"
  echo ""
  echo -e "  \033[2mCmd+L → AI chat  ·  Cmd+Shift+M → switch model  ·  Cmd+Shift+S → session list\033[0m"
fi
echo ""

persist_config_version 2>/dev/null || true
