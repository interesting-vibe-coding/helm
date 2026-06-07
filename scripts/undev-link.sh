#!/usr/bin/env bash
# undev-link.sh — revert dev-link.sh: replace the repo symlinks with real copies,
# restoring a normal (shippable) install. Run before testing the real install flow.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BREPO="$REPO/assets/macos/Helm.app/Contents/Resources"
APP="/Applications/Helm.app/Contents/Resources"

green() { printf '\033[0;32m%s\033[0m\n' "$*"; }

# kaku.lua: replace symlink with a real copy
if [[ -L "$HOME/.config/kaku/kaku.lua" ]]; then
  rm -f "$HOME/.config/kaku/kaku.lua"
  cp "$BREPO/kaku.lua" "$HOME/.config/kaku/kaku.lua"
  green "✓ ~/.config/kaku/kaku.lua is now a real copy"
fi

# App resources: replace symlinks with real copies from repo
if [[ -d "$APP" ]]; then
  for entry in tools first_run.sh skills; do
    if [[ -L "$APP/$entry" ]]; then
      rm -f "$APP/$entry"
      case "$entry" in
        first_run.sh) cp "$REPO/assets/shell-integration/first_run.sh" "$APP/first_run.sh" ;;
        tools)        cp -R "$REPO/tools" "$APP/tools" ;;
        skills)       [[ -d "$REPO/assets/skills" ]] && cp -R "$REPO/assets/skills" "$APP/skills" ;;
      esac
    fi
  done
  green "✓ Helm.app resources are now real copies"
fi

green "Dev mode off (normal install restored)."
