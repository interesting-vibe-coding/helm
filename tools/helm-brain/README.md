# helm-brain

The Brain agent's **eyes and hands**. Kaji's "First Mate" — a Sonnet
orchestrator — uses this CLI to watch every worker agent session and to route
the user's instructions to the right pane.

It merges three sources:

- `kaku cli list --format json` — live panes. Kaji is a wezterm fork, so its
  mux CLI is the `kaku` binary in the bundle
  (`/Applications/Helm.app/Contents/MacOS/kaku`). It falls back to `kaku`/
  `wezterm` on `PATH`, and honours `$HELM_CLI` as an override.
  **Note:** the sibling `k` binary is the *agent* one-shot CLI, not the mux
  CLI — `helm-brain` deliberately does not use it.
- `~/.helm/sessions/runtime.json` — per-pane agent state persisted by
  `kaku.lua` (`Helm.sessions.save`).
- `tools/helm-quota/quota.py --json` — per-harness `tokens_today`.

## Commands

### `helm-brain sessions`

Prints a JSON array of worker sessions — one object per pane that Kaji is
tracking as an agent session. Panes without a `runtime.json` entry (i.e. not
agent sessions) are skipped. If Kaji is not running or files are missing it
prints `[]` and exits 0.

```json
[
  {
    "pane_id": 3,
    "harness": "claude",
    "project": "helm-terminal",
    "state": "waiting",
    "runtime_secs": 842,
    "tokens_today": 19000
  }
]
```

Field reference:

| field          | type   | source                                              |
| -------------- | ------ | --------------------------------------------------- |
| `pane_id`      | int    | `runtime.json` key (Kaji/wezterm pane id)           |
| `harness`      | string | `runtime.json.harness`, lowercased (`claude`/`kiro`/`opencode`) |
| `project`      | string | basename of `runtime.json.cwd`                      |
| `state`        | string | `working` \| `waiting` \| `background` \| ...       |
| `runtime_secs` | int    | `now - start_time` (epoch seconds)                  |
| `tokens_today` | int    | `quota.py` `tokens_today` for that harness (0 if N/A) |

> When the live pane list is available, sessions are filtered to panes that
> still exist; stale `runtime.json` entries are dropped. If the pane list is
> unavailable (Kaji not running) the script falls back to `runtime.json` alone.

### `helm-brain send <pane_id> <text>`

Injects `<text>` into the given worker pane, then a carriage return so the
agent submits it. Uses `kaku cli send-text --pane-id <id> --no-paste -- <text>`
followed by a second `send-text` of `\r`. Text is passed via argv (never string
interpolation) so arbitrary instructions are safe to send.

```sh
helm-brain send 3 "run the test suite and report failures"
```

### `helm-brain notify <title> <msg>`

Pops a macOS notification via `osascript`. Quotes are escaped.

```sh
helm-brain notify "pane 3" "claude is waiting for input"
```

### `helm-brain watch`

Polls `sessions` every 3s and prints a line whenever a session's state changes
(especially `-> waiting`). Ctrl-C to stop.

## Launching the Brain

The cross-harness **`helm-first-mate` skill** is the persona that turns a Sonnet
agent into the Helm First Mate. It is bundled in `Helm.app` (under
`Contents/Resources/skills/helm-first-mate`) and symlinked into
`~/.kiro/skills/helm-first-mate` by `first_run.sh`, so any harness can load it.
`launch-brain.sh` boots the chosen harness with a short activation message that
loads the skill, and the `helm-brain` CLI on its `PATH`:

```sh
tools/helm-brain/launch-brain.sh
```

Harness choice (documented in the script) — each gets the same short activation
("Use the helm-first-mate skill, then run 'helm-brain sessions' and greet me"):

- **Preferred — `claude`**: `claude --model sonnet --dangerously-skip-permissions`.
- **`kiro-cli`**: `--model claude-sonnet-4.6`, loads the skill from
  `~/.kiro/skills/helm-first-mate`.
- **`opencode` / `codex`**: best-effort, same short activation.

The script resolves its own directory (following symlinks), so it works both
from the repo and when bundled in `Helm.app/Contents/Resources/tools/helm-brain/`.

## Notes

- Brain model = **Sonnet**.
- Robustness: the script never crashes when Kaji isn't running or files are
  missing — `sessions` prints `[]`, other commands report a clear error.
