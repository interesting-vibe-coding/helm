# Helm Tools

Standalone CLI tools for agent-native workflows.
Each tool is in its own directory with a Python script and shell wrapper.

## Install all tools

```bash
export PATH="$PATH:$(pwd)/tools/helm-history"
export PATH="$PATH:$(pwd)/tools/helm-quota"
export PATH="$PATH:$(pwd)/tools/helm-status"
export PATH="$PATH:$(pwd)/tools/helm-watch"
export PATH="$PATH:$(pwd)/tools/helm-telemetry"
```

Or add to your shell config after installing Helm:
```bash
export PATH="$PATH:/Applications/Helm.app/Contents/Resources/tools"
```
(Tools will be bundled in a future release)

## Available Tools

### helm-history
Index and search chat history across all harnesses.
```bash
helm-history list                        # show all sessions by harness
helm-history recent                      # last 10 sessions
helm-history search <query>              # search by title
helm-history show <id>                   # show session messages
helm-history export <id> <output.md>     # export session to markdown
helm-history export-all <harness> <dir>  # export all sessions from one harness
```

### helm-quota
Show per-harness usage and quota status.
```bash
helm-quota
```

### helm-status
Unified dashboard: sessions + symlinks + build status.
```bash
helm-status
```

### helm-watch
Live session monitor (like top for agents).
```bash
helm-watch  # updates every 2s, q to quit
```

### helm-telemetry
Local-only usage metrics. No data leaves your machine.
```bash
helm-telemetry
```

### helm-init
One-shot setup for new users.
```bash
bash tools/helm-init/helm-init.sh
```
