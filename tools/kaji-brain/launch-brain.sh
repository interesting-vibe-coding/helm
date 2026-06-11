#!/usr/bin/env bash
# launch-brain.sh — start the Kaji "First Mate", a Sonnet orchestrator agent.
#
# The Brain is a normal coding-agent session pointed at the cross-harness
# `helm-first-mate` skill (single source of truth for the persona; bundled in
# Kaji.app and installed to the open hub ~/.agents/skills by first_run.sh) and given the
# `kaji-brain` CLI on its PATH. It watches every worker session (via
# `kaji-brain sessions`) and relays the captain's orders to worker panes.
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
#   the `helm-first-mate` skill, run `kaji-brain sessions`, and greet the
#   captain. No more multi-KB --append-system-prompt — the skill carries the
#   full operating brief, so the launch arg stays tiny across all harnesses.
#   The picked harness is echoed to stderr before exec.
#
# PATH RESOLUTION: works both from the repo (tools/kaji-brain/) and when bundled
# in Kaji.app/Contents/Resources/tools/kaji-brain/. We resolve the script's own
# directory and locate the kaji-brain CLI next to it.

set -euo pipefail

# --- resolve this script's real directory (follow symlinks) ---
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

# Put the kaji-brain CLI on PATH so the agent can call `kaji-brain ...`.
# Also prepend the common Homebrew bin dirs: GUI-launched apps (Kaji started
# from Finder/Dock) do NOT inherit the shell's PATH, so tools like `node` —
# needed by the Brain harness's own hooks (e.g. Claude Code statusline/skills) —
# would otherwise be "command not found". Prepend them so the whole Brain
# process tree (harness + its hooks) can find them.
export PATH="$SCRIPT_DIR:/opt/homebrew/bin:/usr/local/bin:$PATH"

# Run from the repo/bundle root so relative work feels natural; harmless if it
# doesn't exist.
START_DIR="$HOME"
cd "$START_DIR" 2>/dev/null || true

# --- which harness powers the Brain? --------------------------------------
# Read the user's onboarding choice from ~/.config/kaku/brain.conf. Format is a
# single KEY=VALUE line: `BRAIN_HARNESS=claude` (claude | kiro | opencode |
# codex). Missing file or unknown value → default to claude.
BRAIN_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/helm/brain.conf"
# Backward compat: fall back to the legacy Kaku location if Kaji's isn't present.
if [[ ! -f "$BRAIN_CONF" ]]; then
  LEGACY_BRAIN_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/kaku/brain.conf"
  [[ -f "$LEGACY_BRAIN_CONF" ]] && BRAIN_CONF="$LEGACY_BRAIN_CONF"
fi
# Default Brain = the Kaji Sun TUI cockpit (our own surface — no harness
# shell). An LLM harness can still hold the rudder: set BRAIN_HARNESS to
# claude|kiro|opencode|codex in brain.conf to get the dispatcher-agent Brain.
BRAIN_HARNESS="cockpit"
if [[ -f "$BRAIN_CONF" ]]; then
  conf_val="$(sed -nE 's/^[[:space:]]*BRAIN_HARNESS[[:space:]]*=[[:space:]]*([A-Za-z]+).*/\1/p' "$BRAIN_CONF" | head -n1)"
  case "$conf_val" in
    cockpit|claude|kiro|opencode|codex) BRAIN_HARNESS="$conf_val" ;;
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
# preferring claude. Note the substitution on stderr. (cockpit needs no
# harness — only python3, which macOS always has.)
if [[ "$BRAIN_HARNESS" != "cockpit" ]] && ! have "$BRAIN_HARNESS"; then
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
  cockpit)
    # No banner — the cockpit paints its own frame instantly; any echo here
    # is a flash of noise before the alt screen takes over.
    exec python3 "$SCRIPT_DIR/../brain-cockpit/cockpit.py"
    ;;
  claude)
    echo "launch-brain: using claude (--model sonnet, kaji-brain MCP + /helm-first-mate skill)" >&2
    # The Brain drives the fleet through the kaji-brain MCP SERVER (typed
    # tools: list_sessions / fleet_timeline / spawn_worker / send_to_worker /
    # notify) — the engine-agnostic seam: any MCP-speaking harness can hold
    # the rudder. The CLI stays on PATH as a fallback.
    # --strict-mcp-config: load ONLY this config — reading Claude Desktop's
    # cross-app config file (claude_desktop_config.json) pops a TCC "access
    # data from other apps" prompt on every Brain launch, so we opt out.
    MCP_CONFIG=$(printf '{"mcpServers":{"kaji-brain":{"command":"python3","args":["%s/mcp_server.py"]}}}' "$SCRIPT_DIR")
    # NO --dangerously-skip-permissions for the Brain: the harness's native
    # permission prompt (arrow-key allow/deny) IS the confirm gate for
    # destructive fleet actions (spawn_worker / send_to_worker) — better UX
    # than a typed y/n. Read-only tools + the kaji-brain CLI are pre-allowed
    # so observation stays frictionless.
    exec claude --model sonnet \
      --allowedTools "mcp__kaji-brain__list_sessions" "mcp__kaji-brain__fleet_timeline" "mcp__kaji-brain__notify" "Bash(kaji-brain:*)" \
      --mcp-config "$MCP_CONFIG" --strict-mcp-config \
      "You are the Kaji First Mate. Use the /helm-first-mate skill. Prefer the kaji-brain MCP tools (list_sessions, fleet_timeline, spawn_worker, send_to_worker, notify) over shelling out; the permission prompt on spawn/send is the captain's confirm gate, so call the tool directly after a one-line plan. Start: call list_sessions, run 'kaji-brain last-session' (offer a y/n restore if non-empty), and greet me."
    ;;
  kiro)
    echo "launch-brain: using kiro-cli (--model claude-sonnet-4.6, helm-first-mate skill)" >&2
    exec kiro-cli chat --trust-all-tools --agent default \
      --model claude-sonnet-4.6 \
      "You are the Kaji First Mate. Use the helm-first-mate skill (~/.agents/skills/helm-first-mate), then run 'kaji-brain sessions' and 'kaji-brain last-session' (offer a y/n restore if the latter is non-empty), and greet me."
    ;;
  opencode)
    echo "launch-brain: using opencode (--model openrouter/anthropic/claude-sonnet-4.6, helm-first-mate skill)" >&2
    exec opencode --model "openrouter/anthropic/claude-sonnet-4.6" \
      --prompt "You are the Kaji First Mate. Use the helm-first-mate skill (~/.agents/skills/helm-first-mate), then run 'kaji-brain sessions' and 'kaji-brain last-session' (offer a y/n restore if the latter is non-empty), and greet me."
    ;;
  codex)
    echo "launch-brain: using codex (--dangerously-bypass-approvals-and-sandbox, helm-first-mate skill)" >&2
    exec codex --dangerously-bypass-approvals-and-sandbox \
      "You are the Kaji First Mate. Use the helm-first-mate skill (~/.agents/skills/helm-first-mate), then run 'kaji-brain sessions' and 'kaji-brain last-session' (offer a y/n restore if the latter is non-empty), and greet me."
    ;;
esac
