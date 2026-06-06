# Helm Demo: UIST 2026

## Title
Helm: A Session-Scheduled Terminal for Parallel AI Agent Orchestration

## One-sentence summary
Helm virtualizes N background AI agent sessions onto M visible panes using LRU scheduling,
shows real-time agent state in the tab bar, and shares memory/context across all harnesses.

## Demo scenario (3 minutes)

### Setup (30s)
- Open Helm.app, show the clean default terminal
- Press Cmd+Shift+K → launch kiro in right pane
- Press Cmd+Shift+K again → launch opencode in another pane

### Layer 1: Session Scheduling (60s)
- Launch 4 agents total (kiro ×2, opencode, claude-code)
- Show Cmd+Shift+S: session list with runtimes
- Background one session with Cmd+Shift+B
- Show [BG] indicator in session list

### Layer 2: Status Awareness (45s)
- Show 🔵 kiro:project (01:23) in tab bar
- Trigger agent waiting state (ask agent a question)
- Show macOS notification + 🟠 indicator
- Press Cmd+Shift+U to jump to waiting agent

### Layer 3: Shared Context (45s)
- Show ~/.kiro/AGENTS.md (master memory file)
- Show symlinks to ~/.claude/CLAUDE.md, ~/.config/opencode/AGENTS.md
- Run helm-history recent to show cross-harness session index
- Switch from kiro to claude-code — agent immediately has context from AGENTS.md

## Submission checklist
- [ ] 2-minute video
- [ ] 2-page extended abstract (ACM format)
- [ ] Deadline: July 10, 2026
