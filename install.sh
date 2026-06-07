#!/bin/bash
# Helm installer — curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
set -euo pipefail

REPO="interesting-vibe-coding/helm"
APP="Helm.app"
DEST="/Applications"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
say() { echo -e "$@"; }

say ""
say "${BOLD}  Installing Helm${NC}"
say ""

# macOS only
if [[ "$(uname)" != "Darwin" ]]; then
  say "  ${YELLOW}Helm is macOS-only.${NC}"
  exit 1
fi

# Latest-release asset via GitHub's stable redirect — NO api.github.com call,
# so no unauthenticated rate-limit 403s. /releases/latest/download/<asset>
# always redirects to the newest release's asset.
URL="https://github.com/$REPO/releases/latest/download/Helm.app.zip"

# Download + unpack
TMP=$(mktemp -d)
say "  → downloading (~80MB)"
curl -fL --progress-bar "$URL" -o "$TMP/Helm.app.zip"
say "  → unpacking"
ditto -x -k "$TMP/Helm.app.zip" "$TMP"

# Replace any existing install
if [[ -d "$DEST/$APP" ]]; then
  say "  → removing old version"
  rm -rf "$DEST/$APP"
fi
cp -R "$TMP/$APP" "$DEST/"

# Remove quarantine (ad-hoc signed, not notarized yet)
xattr -dr com.apple.quarantine "$DEST/$APP" 2>/dev/null || true

# Seed the Helm config on first install. Helm's features (the Brain, 3-view nav,
# help bar, onboarding) all live in kaku.lua — without this a fresh install would
# fall back to a bare terminal. Only seeds if the user has no config yet.
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/helm"
LEGACY_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/kaku"
# One-time, non-destructive migration from the legacy Kaku config dir so existing
# users keep their config. Leaves the legacy dir intact.
if [[ ! -d "$CONFIG_DIR" && -d "$LEGACY_CONFIG_DIR" ]]; then
  cp -R "$LEGACY_CONFIG_DIR" "$CONFIG_DIR" 2>/dev/null && \
    say "  → migrated config from ~/.config/kaku to ~/.config/helm"
fi
if [[ ! -f "$CONFIG_DIR/kaku.lua" && -f "$DEST/$APP/Contents/Resources/kaku.lua" ]]; then
  mkdir -p "$CONFIG_DIR"
  cp "$DEST/$APP/Contents/Resources/kaku.lua" "$CONFIG_DIR/kaku.lua"
  say "  → seeded default config"
fi

rm -rf "$TMP"

say ""
say "${GREEN}${BOLD}  ✓ Helm installed to $DEST/$APP${NC}"
say ""
say "  Open it:  ${BOLD}open -a Helm${NC}"
say "  First launch runs a quick guided setup, then drops you into the Brain."
say "  ${BOLD}Cmd+1${NC} Brain · ${BOLD}Cmd+2${NC} Work · ${BOLD}Cmd+3${NC} Monitor · ${BOLD}Cmd+/${NC} Help"
say ""

# Offer to open now
if [[ -t 0 ]]; then
  read -r -p "  Open Helm now? [Y/n] " ans
  [[ "${ans:-y}" =~ ^[Nn] ]] || open -a Helm
fi
