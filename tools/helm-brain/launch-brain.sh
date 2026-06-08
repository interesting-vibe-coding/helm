#!/usr/bin/env bash
# launch-brain.sh — start the Helm "First Mate", a Sonnet orchestrator agent.
#
# The Brain is a normal coding-agent session pointed at the cross-harness
# `helm-first-mate` skill (single source of truth for the persona; bundled in
# Helm.app and installed to the open hub ~/.agents/skills by first_run.sh) and given the
# `helm-brain` CLI on its PATH. It watches every worker session (via
# `helm-brain sessions`) and relays the captain's orders to worker panes.
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
#   Per-harness launch: each gets a SHORT activation message telling it to load
#   the `helm-first-mate` skill, run `helm-brain sessions`, and greet the
#   captain. No more multi-KB --append-system-prompt — the skill carries the
#   full operating brief, so the launch arg stays tiny across all harnesses.
#   The picked harness is echoed to stderr before exec.
#
# PATH RESOLUTION: works both from the repo (tools/helm-brain/) and when bundled
# in Helm.app/Contents/Resources/tools/helm-brain/. We resolve the script's own
# directory and locate the helm-brain CLI next to it.

set -euo pipefail

# --- resolve this script's real directory (follow symlinks) ---
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

# Put the helm-brain CLI on PATH so the agent can call `helm-brain ...`.
export PATH="$SCRIPT_DIR:$PATH"

# Run from the repo/bundle root so relative work feels natural; harmless if it
# doesn't exist.
START_DIR="$HOME"
cd "$START_DIR" 2>/dev/null || true

# --- which harness powers the Brain? --------------------------------------
# Read the user's onboarding choice from ~/.config/kaku/brain.conf. Format is a
# single KEY=VALUE line: `BRAIN_HARNESS=claude` (claude | kiro | opencode |
# codex). Missing file or unknown value → default to claude.
BRAIN_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/helm/brain.conf"
# Backward compat: fall back to the legacy Kaku location if Helm's isn't present.
if [[ ! -f "$BRAIN_CONF" ]]; then
  LEGACY_BRAIN_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/kaku/brain.conf"
  [[ -f "$LEGACY_BRAIN_CONF" ]] && BRAIN_CONF="$LEGACY_BRAIN_CONF"
fi
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
    echo "launch-brain: using claude (--model sonnet, /helm-first-mate skill)" >&2
    # --strict-mcp-config: ignore ALL other MCP configs (incl. Claude Desktop's
    # ~/Library/Application Support/Claude/claude_desktop_config.json). Reading
    # that cross-app file makes macOS pop a TCC "Helm wants to access data from
    # other apps" prompt on every Brain launch. The Brain doesn't need desktop
    # MCP servers (it drives workers via the helm-brain CLI), so we opt out.
    exec claude --model sonnet --dangerously-skip-permissions \
      --mcp-config '{"mcpServers":{}}' --strict-mcp-config \
      "You are the Helm First Mate. Use the /helm-first-mate skill, then run 'helm-brain sessions' and greet me."
    ;;
  kiro)
    echo "launch-brain: using kiro-cli (--model claude-sonnet-4.6, helm-first-mate skill)" >&2
    exec kiro-cli chat --trust-all-tools --agent default \
      --model claude-sonnet-4.6 \
      "You are the Helm First Mate. Use the helm-first-mate skill (~/.agents/skills/helm-first-mate), then run 'helm-brain sessions' and greet me."
    ;;
  opencode)
    echo "launch-brain: using opencode (--model openrouter/anthropic/claude-sonnet-4.6, helm-first-mate skill)" >&2
    exec opencode --model "openrouter/anthropic/claude-sonnet-4.6" \
      --prompt "You are the Helm First Mate. Use the helm-first-mate skill (~/.agents/skills/helm-first-mate), then run 'helm-brain sessions' and greet me."
    ;;
  codex)
    echo "launch-brain: using codex (--dangerously-bypass-approvals-and-sandbox, helm-first-mate skill)" >&2
    exec codex --dangerously-bypass-approvals-and-sandbox \
      "You are the Helm First Mate. Use the helm-first-mate skill (~/.agents/skills/helm-first-mate), then run 'helm-brain sessions' and greet me."
    ;;
esac
