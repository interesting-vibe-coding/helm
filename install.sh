#!/bin/bash
# Helm installer — curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
set -euo pipefail

REPO="interesting-vibe-coding/helm"
APP="Helm.app"
DEST="/Applications"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
say() { echo -e "$@"; }

say ""
say "${BOLD}  Installing Helm 🎯${NC}"
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

rm -rf "$TMP"

say ""
say "${GREEN}${BOLD}  ✓ Helm installed to $DEST/$APP${NC}"
say ""
say "  Open it:  ${BOLD}open -a Helm${NC}"
say "  On first launch, Helm sets up cross-harness memory and shell integration."
say ""
say "  Then press ${BOLD}Cmd+Shift+K${NC} to launch your first agent."
say ""

# Offer to open now
if [[ -t 0 ]]; then
  read -r -p "  Open Helm now? [Y/n] " ans
  [[ "${ans:-y}" =~ ^[Nn] ]] || open -a Helm
fi
