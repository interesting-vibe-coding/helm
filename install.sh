#!/bin/bash
# Helm installer — curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
set -euo pipefail

REPO="interesting-vibe-coding/helm"
APP="Helm.app"
DEST="/Applications"

PURPLE='\033[0;35m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
say() { printf "%b\n" "$@"; }

say ""
say "${PURPLE}${BOLD}  ᗣ  Installing Helm${NC}"
say ""

# macOS only
if [[ "$(uname)" != "Darwin" ]]; then
  say "  Helm is macOS-only."
  exit 1
fi

URL="https://github.com/$REPO/releases/latest/download/Helm.app.zip"
TMP=$(mktemp -d)

# Spinner — purple dots, writes to /dev/tty so it works in | bash
# Spinner with percentage — monitors file size during download
_spin() {
  local file="$1" total="$2"
  local p=$'\033[0;35m' n=$'\033[0m'
  local frames=("${p}●${n}○○" "○${p}●${n}○" "○○${p}●${n}" "○${p}●${n}○")
  local i=0 pct=0
  while true; do
    if [[ -f "$file" && "$total" -gt 0 ]]; then
      local cur
      cur=$(wc -c < "$file" 2>/dev/null | tr -d ' ')
      pct=$((cur * 100 / total))
      [[ $pct -gt 100 ]] && pct=100
    fi
    printf '\r  → downloading  %s  %3d%%' "${frames[$((i % 4))]}" "$pct" > /dev/tty
    i=$((i + 1))
    sleep 0.15
  done
}

# Get file size for percentage display
# Get file size for percentage display (follow redirects, grab Content-Length)
TOTAL_SIZE=$(curl -fsSLI "$URL" 2>/dev/null | grep -i '^content-length' | tail -1 | tr -dc '0-9')
[[ -z "$TOTAL_SIZE" || "$TOTAL_SIZE" == "0" ]] && TOTAL_SIZE=84000000  # fallback ~80MB

DL_FILE="$TMP/Helm.app.zip"
_spin "$DL_FILE" "$TOTAL_SIZE" &
SPIN_PID=$!
trap 'kill "$SPIN_PID" 2>/dev/null; wait "$SPIN_PID" 2>/dev/null; printf "\r\033[K" > /dev/tty' EXIT

curl -fLs "$URL" -o "$DL_FILE"

kill "$SPIN_PID" 2>/dev/null; wait "$SPIN_PID" 2>/dev/null || true
trap - EXIT
printf '\r\033[K' > /dev/tty
say "  → downloaded   ${PURPLE}✓${NC}"

say "  → unpacking"
ditto -x -k "$TMP/Helm.app.zip" "$TMP"

if [[ -d "$DEST/$APP" ]]; then
  say "  → removing old version"
  rm -rf "$DEST/$APP"
fi
cp -R "$TMP/$APP" "$DEST/"
xattr -dr com.apple.quarantine "$DEST/$APP" 2>/dev/null || true

# Seed config
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/helm"
LEGACY_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/kaku"
if [[ ! -d "$CONFIG_DIR" && -d "$LEGACY_CONFIG_DIR" ]]; then
  cp -R "$LEGACY_CONFIG_DIR" "$CONFIG_DIR" 2>/dev/null && \
    say "  → migrated config from ~/.config/kaku"
fi
if [[ ! -f "$CONFIG_DIR/kaku.lua" && -f "$DEST/$APP/Contents/Resources/kaku.lua" ]]; then
  mkdir -p "$CONFIG_DIR"
  cp "$DEST/$APP/Contents/Resources/kaku.lua" "$CONFIG_DIR/kaku.lua"
fi

rm -rf "$TMP"

say ""
say "${PURPLE}${BOLD}  ✓ Helm installed${NC}"
say ""

# Shell integration — auto-write, no prompt needed (idempotent)
# Detect shell from $SHELL env (works even in | bash pipe)
_shell_name="$(basename "${SHELL:-bash}")"

_setup_fish() {
  local fn="$HOME/.config/fish/functions/helm.fish"
  [[ -f "$fn" ]] && grep -q "open -a Helm" "$fn" 2>/dev/null && {
    say "  ${DIM}helm command already in fish${NC}"; return; }
  mkdir -p "$(dirname "$fn")"
  printf 'function helm\n    open -a Helm $argv\nend\n' > "$fn"
  say "  ${PURPLE}✓${NC} Added ${BOLD}helm${NC} command to fish"
}

_setup_posix() {
  local marker="# --- helm-launcher ---"
  local rc="${HOME}/.zshrc"
  [[ ! -f "$rc" && -f "${HOME}/.bashrc" ]] && rc="${HOME}/.bashrc"
  grep -q "$marker" "$rc" 2>/dev/null && {
    say "  ${DIM}helm command already in $(basename "$rc")${NC}"; return; }
  printf '\n%s\nhelm() { open -a Helm "$@"; }\n%s\n' "$marker" "$marker" >> "$rc"
  say "  ${PURPLE}✓${NC} Added ${BOLD}helm${NC} command  ${DIM}(source $rc to activate)${NC}"
}

case "$_shell_name" in
  fish) _setup_fish ;;
  *)    _setup_posix ;;
esac

say ""
say "  Type ${PURPLE}${BOLD}helm${NC} to launch."
say "  ${DIM}First launch runs setup, then drops you into the Brain.${NC}"
say "  ${DIM}Cmd+1 Brain · Cmd+2 Work · Cmd+3 Monitor · Cmd+/ Help${NC}"
say ""
