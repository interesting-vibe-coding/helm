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

# Resolve latest release asset URL
say "  → fetching latest release"
URL=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
  | grep '"browser_download_url"' \
  | grep 'Helm.app.zip' \
  | head -1 \
  | cut -d'"' -f4)

if [[ -z "${URL:-}" ]]; then
  say "  ${YELLOW}No release asset found. Build from source instead:${NC}"
  say "    git clone https://github.com/$REPO && cd helm"
  say "    PROFILE=debug ./scripts/build.sh --app-only && open dist/Helm.app"
  exit 1
fi

# Download + unpack
TMP=$(mktemp -d)
say "  → downloading"
curl -fsSL "$URL" -o "$TMP/Helm.app.zip"
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
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/kaku"
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
