# Changelog

All notable changes to Helm are documented here.
Format: [version] - date - description

## [0.2.0] - 2026-06-07

### Added (Agent OS features)
- **Session Scheduler**: LRU-based session virtualization. Cmd+Shift+B to background.
- **Harness Launcher**: Cmd+Shift+K to spawn kiro/claude-code/opencode/codex in new pane.
- **Agent Notifications**: macOS notifications when agent needs input. Cmd+Shift+U to jump to waiting agent.
- **Session List**: Cmd+Shift+S to view all active sessions with runtime and state.
- **Model Toggle**: Cmd+Shift+M to switch between claude-sonnet-4.6 and claude-opus-4.8.
- **Project-aware naming**: Tab bar shows `🔵 kiro:projectname (MM:SS)`.
- **Window title**: Shows `Helm — N agents (M waiting)` when agents are active.
- **Session persistence**: Sessions saved to ~/.helm/sessions/runtime.json across restarts.
- **Cross-harness memory**: AGENTS.md symlinked to claude-code, opencode, codex automatically.

### Tools Added
- `helm-history`: Index and search chat history across all harnesses (282+ sessions).
- `helm-status`: Unified dashboard with sessions, symlinks, build status.
- `helm-watch`: Live session monitor (htop for agents).
- `helm-quota`: Per-harness usage awareness.
- `helm-telemetry`: Local-only usage metrics.
- `helm-init`: One-shot setup script.
- `helm-doctor`: Diagnose setup issues.
- `helm-harness-status`: Check which harnesses are installed.
- `helm-session-replay`: Export past session as context for new agent.

### Paper
- Draft submitted to IUI 2027 (target). Sections: Abstract, Introduction, Related Work, System Design, Implementation, User Study, Evaluation.
- UIST 2026 Demo abstract ready (deadline Jul 10, 2026).
- HAI 2026 Osaka poster/demo planned (deadline Aug 7, 2026).

## [0.1.0] - 2026-06-06

### Added
- Fork of Kaku (WezTerm) with Helm branding (dev.helm.app).
- Interactive first_run.sh: shell detection, required tools, optional tools.
- Helm logo: geometric gold helm wheel icon.
- CI: macos-latest runner + luac syntax check.
