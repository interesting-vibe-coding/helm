#!/usr/bin/env bash
# launch-brain.sh — start the Helm "First Mate", a Sonnet orchestrator agent.
#
# The Brain is a normal coding-agent session given the BRAIN_PROMPT.md system
# prompt and the `helm-brain` CLI on its PATH. It watches every worker session
# (via `helm-brain sessions`) and relays the captain's orders to worker panes.
#
# HARNESS CHOICE (documented decision):
#   We need a harness that can (a) run an interactive chat session and (b) take
#   a *system prompt* non-interactively at launch, on the Sonnet model.
#     1. PREFERRED — `claude`: Claude Code's `--append-system-prompt` injects a
#        system prompt into an interactive session, and `--model sonnet` pins
#        the model. This is the cleanest fit (true system prompt, not a faked
#        first user message), so we use it when `claude` is on PATH.
#     2. FALLBACK — `kiro-cli chat`: has no system-prompt flag, so we pass
#        BRAIN_PROMPT.md as the initial [INPUT] message and pin
#        `--model claude-sonnet-4.6` (the Sonnet id used elsewhere in kaku.lua).
#        `--agent default --trust-all-tools` mirrors how kaku.lua launches kiro.
#   The picked harness is echoed to stderr before exec.
#
# PATH RESOLUTION: works both from the repo (tools/helm-brain/) and when bundled
# in Helm.app/Contents/Resources/tools/helm-brain/. We resolve the script's own
# directory and locate BRAIN_PROMPT.md + the helm-brain CLI next to it.

set -euo pipefail

# --- resolve this script's real directory (follow symlinks) ---
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

PROMPT_FILE="$SCRIPT_DIR/BRAIN_PROMPT.md"
if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "launch-brain: BRAIN_PROMPT.md not found next to launcher ($PROMPT_FILE)" >&2
  exit 1
fi

# Put the helm-brain CLI on PATH so the agent can call `helm-brain ...`.
export PATH="$SCRIPT_DIR:$PATH"

# Run from the repo/bundle root so relative work feels natural; harmless if it
# doesn't exist.
START_DIR="$HOME"
cd "$START_DIR" 2>/dev/null || true

SYSTEM_PROMPT="$(cat "$PROMPT_FILE")"

if command -v claude >/dev/null 2>&1; then
  echo "launch-brain: using claude (--model sonnet, --append-system-prompt)" >&2
  exec claude --model sonnet \
    --append-system-prompt "$SYSTEM_PROMPT" \
    --dangerously-skip-permissions
elif command -v kiro-cli >/dev/null 2>&1; then
  echo "launch-brain: claude not found — falling back to kiro-cli (--model claude-sonnet-4.6)" >&2
  exec kiro-cli chat --trust-all-tools --agent default \
    --model claude-sonnet-4.6 \
    "$SYSTEM_PROMPT"
else
  echo "launch-brain: no supported harness found (need 'claude' or 'kiro-cli' on PATH)" >&2
  exit 1
fi
