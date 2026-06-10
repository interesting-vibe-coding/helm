# brain-cockpit

The **render-only Brain** — the `Cmd+1` view as a pure visualization, **no
model**. See `docs/BRAIN_DESIGN.md` § "Visualization first" for why this comes
first (and very likely stays model-free).

It reads the substrate and renders one calm screen:

- **brand** — Kaji ghost + wordmark;
- **session list**, ordered **most-neglected first** (waiting longest → working
  → … → done), each with a status dot you read at a glance:
  `● waiting` (amber, needs you) · `● working` (teal) · `○ idle/done` · `● error` · `● background`;
- **per-row last activity** (spawned / you sent / → state);
- **selected session detail** — that pane's recent history, newest first;
- a **compass** row of dots — one per session — for an O(1) glance.

## Data sources

- `helm-brain sessions` → the live snapshot (`runtime.json` + quota).
- `helm-brain timeline --json` → the `events.jsonl` history chain.

Rendering is a **pure function** of `(sessions, events, selection, width)`, so
it is unit-tested and screenshot-able with no Kaji running.

## Try it

```sh
# Preview the layout with a built-in sample fleet (no Kaji needed):
python3 tools/brain-cockpit/cockpit.py --demo --once

# Against the real fleet (Kaji running):
python3 tools/brain-cockpit/cockpit.py --once

# Tests:
cd tools/brain-cockpit && python3 -m unittest discover -p 'test_*.py'
```

## Status / next

- ✅ Render layer + ordering + status dots + history panel (pure, tested).
- ⛏️ **Interactive loop** (full-screen curses: arrow-key session switch, scroll
  history, "send to selected") — next, needs a real tty / macOS.
- ⛏️ Wire into `Cmd+1` (replace the launch-brain chat box with this cockpit).
- Later (only if lived use demands it): a native GUI overlay mirroring this
  layout, and/or an optional LLM region — both gated per `BRAIN_DESIGN.md`.
