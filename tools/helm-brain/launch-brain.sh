#!/usr/bin/env bash
# launch-brain.sh — start the Helm "First Mate", a Sonnet orchestrator agent.
#
# The Brain is a normal coding-agent session given the BRAIN_PROMPT.md system
# prompt and the `helm-brain` CLI on its PATH. It watches every worker session
# (via `helm-brain sessions`) and relays the captain's orders to worker panes.
#
# HARNESS CHOICE (documented decision):
#   The user picks which harness powers the Brain during first-run onboarding
#   (first_run.sh "Choose your Brain" step). That choice is persisted to
#   ~/.config/kaku/brain.conf as a single line `BRAIN_HARNESS=<value>` where
#   <value> is one of: claude | kiro | opencode | codex. We read it here and
#   launch that harness. If the file is missing/invalid we default to claude;
#   if the chosen harness isn't on PATH we fall back to the first available
#   (preferring claude) and note the substitution on stderr.
#
#   Per-harness launch (all need an interactive chat that takes BRAIN_PROMPT.md):
#     claude   — true system prompt via `--append-system-prompt`, `--model sonnet`.
#                Cleanest fit (real system prompt, not a faked first message).
#     kiro     — `kiro-cli chat` has no system-prompt flag; its only positional
#                is [INPUT] ("the first question to ask"). Rather than pass the
#                whole prompt as a giant positional arg, we pass a short INPUT
#                telling kiro to read BRAIN_PROMPT.md via its fs tool (enabled by
#                --trust-all-tools) and adopt it. Pinned to Sonnet
#                `claude-sonnet-4.6` used elsewhere in kaku.lua.
#     opencode — best-effort: no system-prompt flag. opencode loads instructions
#                from AGENTS.md (first_run.sh symlinks the master memory into
#                ~/.config/opencode), so the prompt is passed via `--prompt` and
#                a Sonnet model is pinned (openrouter/anthropic/claude-sonnet-4.6).
#     codex    — best-effort: no system-prompt flag. codex reads AGENTS.md
#                (~/.codex/AGENTS.md, symlinked by first_run.sh); the prompt is
#                passed as the initial message and it runs low-friction. Model
#                is left to codex's configured default.
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

# --- which harness powers the Brain? --------------------------------------
# Read the user's onboarding choice from ~/.config/kaku/brain.conf. Format is a
# single KEY=VALUE line: `BRAIN_HARNESS=claude` (claude | kiro | opencode |
# codex). Missing file or unknown value → default to claude.
BRAIN_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/kaku/brain.conf"
BRAIN_HARNESS="claude"
if [[ -f "$BRAIN_CONF" ]]; then
  conf_val="$(sed -nE 's/^[[:space:]]*BRAIN_HARNESS[[:space:]]*=[[:space:]]*([A-Za-z]+).*/\1/p' "$BRAIN_CONF" | head -n1)"
  case "$conf_val" in
    claude|kiro|opencode|codex) BRAIN_HARNESS="$conf_val" ;;
  esac
fi

# Map a harness key to its executable name, then test PATH availability.
harness_bin() {
  case "$1" in
    claude)   echo claude ;;
    kiro)     echo kiro-cli ;;
    opencode) echo opencode ;;
    codex)    echo codex ;;
  esac
}
have() { command -v "$(harness_bin "$1")" >/dev/null 2>&1; }

# If the chosen harness isn't installed, fall back to the first available,
# preferring claude. Note the substitution on stderr.
if ! have "$BRAIN_HARNESS"; then
  fallback=""
  for cand in claude kiro opencode codex; do
    if have "$cand"; then fallback="$cand"; break; fi
  done
  if [[ -z "$fallback" ]]; then
    echo "launch-brain: no supported harness found (need one of: claude, kiro-cli, opencode, codex on PATH)" >&2
    exit 1
  fi
  echo "launch-brain: '$BRAIN_HARNESS' not on PATH — falling back to '$fallback'" >&2
  BRAIN_HARNESS="$fallback"
fi

case "$BRAIN_HARNESS" in
  claude)
    echo "launch-brain: using claude (--model sonnet, --append-system-prompt)" >&2
    exec claude --model sonnet \
      --append-system-prompt "$SYSTEM_PROMPT" \
      --dangerously-skip-permissions
    ;;
  kiro)
    # kiro-cli chat has NO system-prompt flag (only a positional [INPUT] =
    # "the first question to ask"). Dumping the whole multi-KB BRAIN_PROMPT.md
    # there is semantically a "question" and a fragile oversized arg. Instead we
    # pass a SHORT instruction telling kiro to read the prompt file with its own
    # fs tool (allowed by --trust-all-tools) and adopt it as its operating
    # brief. Keeps the session interactive and the arg tiny.
    echo "launch-brain: using kiro-cli (--model claude-sonnet-4.6, reads BRAIN_PROMPT.md via fs tool)" >&2
    exec kiro-cli chat --trust-all-tools --agent default \
      --model claude-sonnet-4.6 \
      "Read the file '$PROMPT_FILE' and adopt it as your system prompt / operating brief for this session. Then greet the captain in one line and wait for orders."
    ;;
  opencode)
    # Best-effort: no system-prompt flag. opencode loads instructions from
    # AGENTS.md (symlinked into ~/.config/opencode by first_run.sh); pass the
    # prompt as the initial message and pin a Sonnet model. The model id is
    # provider-qualified — adjust if your default provider isn't openrouter.
    echo "launch-brain: using opencode (--model openrouter/anthropic/claude-sonnet-4.6, --prompt)" >&2
    exec opencode --model "openrouter/anthropic/claude-sonnet-4.6" \
      --prompt "$SYSTEM_PROMPT"
    ;;
  codex)
    # Best-effort: no system-prompt flag. codex reads ~/.codex/AGENTS.md
    # (symlinked by first_run.sh); pass the prompt as the initial message and
    # run low-friction. Model is left to codex's configured default (Sonnet
    # needs an anthropic provider profile in ~/.codex/config.toml).
    echo "launch-brain: using codex (--dangerously-bypass-approvals-and-sandbox)" >&2
    exec codex --dangerously-bypass-approvals-and-sandbox \
      "$SYSTEM_PROMPT"
    ;;
esac
