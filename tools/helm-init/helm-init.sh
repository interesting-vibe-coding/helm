#!/bin/bash
# helm-init: one-shot Helm setup
# Usage: curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/tools/helm-init/helm-init.sh | bash

set -euo pipefail
echo ''
echo '  Helm Setup'
echo ''

# 1. Check Helm.app
if [[ -d /Applications/Helm.app ]]; then
  echo '  ✓ Helm.app found'
else
  echo '  ⚠ Helm.app not found. Build from source or download from GitHub Releases.'
fi

# 2. Create ~/.kiro/AGENTS.md if missing
mkdir -p ~/.kiro
if [[ ! -f ~/.kiro/AGENTS.md ]]; then
  cat > ~/.kiro/AGENTS.md << 'AGENTS'
# AGENTS.md — Helm shared memory
# This file is shared across all AI harnesses via symlinks.
# Edit here; changes propagate everywhere.

## About me
# Add your name, role, preferences here

## Current projects
# List your active projects

## Preferences
# Coding style, language preferences, etc.
AGENTS
  echo '  ✓ Created ~/.kiro/AGENTS.md'
else
  echo '  ✓ ~/.kiro/AGENTS.md exists'
fi

# 3. Symlink to all harnesses
mkdir -p ~/.claude ~/.config/opencode ~/.codex
[[ ! -e ~/.claude/CLAUDE.md ]] && ln -sf ~/.kiro/AGENTS.md ~/.claude/CLAUDE.md && echo '  ✓ Linked claude'
[[ ! -e ~/.config/opencode/AGENTS.md ]] && ln -sf ~/.kiro/AGENTS.md ~/.config/opencode/AGENTS.md && echo '  ✓ Linked opencode'
[[ ! -e ~/.codex/AGENTS.md ]] && ln -sf ~/.kiro/AGENTS.md ~/.codex/AGENTS.md && echo '  ✓ Linked codex'

# 4. Skills symlink
mkdir -p ~/.kiro/skills
[[ ! -e ~/.config/opencode/skills ]] && ln -sf ~/.kiro/skills ~/.config/opencode/skills && echo '  ✓ Linked skills'

# 5. Create ~/.helm directory
mkdir -p ~/.helm/sessions
echo '  ✓ Created ~/.helm/'

echo ''
echo '  Setup complete! Open Helm.app and press:'
echo '    Cmd+Shift+K — launch an AI agent'
echo '    Cmd+Shift+S — view all sessions'
echo '    Cmd+Shift+U — jump to waiting agent'
echo ''
