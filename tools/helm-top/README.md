# helm-top 🖥️

An **htop-style monitor** for Helm worker agent sessions — Helm's Layer-3
"Monitor" view. Lists every agent session Helm is tracking, refreshes live,
and lets you browse with the arrow keys and jump straight to a pane.

Zero friction, out of the box: **Python 3 standard library only** (`curses`).
No `pip install`, no virtualenv, no config.

```
helm-top — 3 sessions · 1 working · 1 waiting              14:22:07
STATE        HARNESS    PROJECT              RUNTIME  TOKENS   PANE
─────────────────────────────────────────────────────────────────
▶ working    claude     mira                 2:34     142k     3
◐ waiting    kiro       helm-terminal        1:30     1.2M     7
⏸ background opencode   doabit               0:45     0        12
 ↑↓/jk move · Enter jump · ? help · r refresh · q quit
```

## What it does

- Reads session data from the existing `kaji-brain sessions` CLI (the single
  interface contract). It does **not** track sessions itself — it's a thin,
  read-only viewer.
- Renders a full-screen table, refreshing every **1.5 s**:
  - **STATE** — icon + color: `▶ working` (blue), `◐ waiting` (orange),
    `⏸ background` (gray)
  - **HARNESS** — claude / kiro / opencode / …
  - **PROJECT** — the session's working-directory basename
  - **RUNTIME** — `mm:ss` under an hour, else `h:mm`
  - **TOKENS** — today's token usage, compact (`142k` / `1.2M`)
  - **PANE** — the Helm/wezterm pane id
- A live header: `helm-top — N sessions · M working · K waiting` + the clock.
- Jumping focuses the pane via Helm's mux CLI:
  `kaku cli activate-pane --pane-id <id>`.

If there are no sessions (or `kaji-brain` is missing/errors), it shows a calm
empty state — it never crashes.

## Keys

| Key            | Action                          |
|----------------|---------------------------------|
| `↑` / `↓` or `j` / `k` | move the selection      |
| `g` / `G`      | jump to top / bottom            |
| `Enter`        | jump to (focus) the selected pane |
| `?`            | toggle the bottom help bar      |
| `r`            | refresh now                     |
| `q`            | quit                            |

In Helm, this view is bound to **Cmd+3** (the Monitor layer; Cmd+1 = Brain,
Cmd+2 = Workspace), and the bottom help bar toggles with **Cmd+/**.

## Run it

```sh
tools/helm-top/helm-top
```

### Self-test (non-interactive)

For tests / CI — dumps the parsed table once as plain text, no curses, no TTY:

```sh
tools/helm-top/helm-top --selftest
```

## How it finds things

- **kaji-brain** is resolved relative to this file (`../kaji-brain/kaji-brain`),
  then the app bundle (`/Applications/Helm.app/Contents/Resources/tools/…`),
  then the dev repo (`~/workspace/helm-terminal/tools/…`).
- The **mux CLI** is `kaku` (`$HELM_CLI`, then
  `/Applications/Helm.app/Contents/MacOS/kaku`, then `kaku`/`wezterm` on
  `PATH`). Note: this is the `kaku` binary, **not** the sibling `k` one-shot
  agent CLI.

## Philosophy — zero friction, out of the box, focus on shipping

helm-top exists so you can **see all your agents at a glance and jump to the
one that needs you, with one keystroke**. No setup, no dependencies, no state
of its own. You stay at the helm; the workers do the rowing. Watch who's
**working**, catch who's **waiting**, and get back to shipping.
