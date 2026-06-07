#!/usr/bin/env bash
# reload.sh — hot-reload Helm's kaku.lua config (sends Cmd+R to Helm).
# After dev-link.sh, edit the repo's kaku.lua then run this to see changes
# instantly — no rebuild, no reinstall.
osascript -e 'tell application "Helm" to activate' >/dev/null 2>&1
osascript -e 'tell application "System Events" to keystroke "r" using {command down}' >/dev/null 2>&1
echo "↻ reloaded Helm config"
