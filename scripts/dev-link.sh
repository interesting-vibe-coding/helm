#!/usr/bin/env bash
# dev-link.sh — wire an installed Helm.app + your user config to THIS repo so you
# see changes instantly, without rebuilding:
#   • kaku.lua          → edit repo, press Cmd+R in Helm to hot-reload (0 build)
#   • tools/ first_run/ skills/ → edit repo, takes effect immediately (next run)
#   • Rust code         → still needs `./scripts/build.sh` (low frequency)
#
# Run once after installing Helm. Re-run safely (idempotent). Use ./scripts/undev-link.sh to revert.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BREPO="$REPO/assets/macos/Helm.app/Contents/Resources"
APP="/Applications/Helm.app/Contents/Resources"

green() { printf '\033[0;32m%s\033[0m\n' "$*"; }

# 1) kaku.lua: user config → repo (the file Helm actually loads). Cmd+R reloads it.
mkdir -p "$HOME/.config/kaku"
ln -sfn "$BREPO/kaku.lua" "$HOME/.config/kaku/kaku.lua"
green "✓ ~/.config/kaku/kaku.lua → repo  (edit repo, Cmd+R to hot-reload)"

# 2) App bundle resources → repo (scripts/tools/skills resolve from the bundle first).
if [[ -d "$APP" ]]; then
  ln -sfn "$REPO/tools"                              "$APP/tools"
  ln -sfn "$REPO/assets/shell-integration/first_run.sh" "$APP/first_run.sh"
  [[ -d "$REPO/assets/skills" ]] && ln -sfn "$REPO/assets/skills" "$APP/skills"
  green "✓ Helm.app Resources (tools/ first_run.sh/ skills/) → repo  (instant)"
else
  printf '  (Helm.app not installed; skipped bundle links)\n'
fi

echo
green "Dev mode on. Edit files in $REPO directly."
echo "  • kaku.lua  → ./scripts/reload.sh  (or Cmd+R in Helm)"
echo "  • tools / first_run / skills → just re-trigger them"
echo "  • Rust      → ./scripts/build.sh"
