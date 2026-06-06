# Contributing to Helm

Helm is an agent-native terminal. We welcome contributions that make
human-agent workflows faster and less friction-filled.

## Architecture

Helm has three layers (see docs/ROADMAP.md for details):
- **Layer 1** (kaku.lua): Session Scheduler, LRU, keyboard shortcuts
- **Layer 2** (kaku.lua + tools/): Status awareness, notifications
- **Layer 3** (tools/): Shared context, history indexer, status dashboard

Most Layer 1+2 changes are in `assets/macos/Helm.app/Contents/Resources/kaku.lua`.
Layer 3 changes are standalone Python tools in `tools/`.

## Building

```bash
PROFILE=debug ./scripts/build.sh --app-only
open dist/Helm.app
```

## Adding a new harness

1. Add detection in `detect_harness()` in kaku.lua
2. Add to the launcher choices in Cmd+Shift+K handler
3. Add symlink in `tools/helm-init/helm-init.sh` if the harness has a convention path
4. Add to helm-history indexer if the harness stores session history

## Tools

All tools in `tools/` are standalone Python scripts with a shell wrapper.
Standard structure: `tools/<name>/<name>.py` + `tools/<name>/<name>` (shell wrapper).

## Lua syntax check

```bash
luac -p assets/macos/Helm.app/Contents/Resources/kaku.lua
```

## PR process

Create a branch, commit, push, open PR to main. We squash-merge.
