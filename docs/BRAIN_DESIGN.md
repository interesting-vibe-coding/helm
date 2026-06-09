# The Brain — Design Decision (pending)

> Status: **open decision**, captured 2026-06-09. Do not treat any framing
> below as shipped. The substrate is no-regret and can be built now; the top
> layer is an experiment to be decided after measuring real token cost.

This doc records a design discussion about what the Helm Brain / First Mate
should actually be. It supersedes the "Layer 4 is the headline" framing in
`ROADMAP.md` until the open decision is made.

---

## The question that decides everything

> If Helm's Brain is **just a visualization layer** showing each session's
> state, why wouldn't a user just open multiple sessions and watch them — the
> way they already do today?

This is the north-star test for every Brain design:

> **It must beat "just open N sessions yourself."**

A pure visualization layer only wins at the margin (persistent cross-session
history + an O(1) glance instead of scanning panes). A power user already
approximates that by hand. The thing that actually pulls ahead of DIY is the
**understanding / synthesis** layer: N panes collapsed into one thing you can
*ask*, where the answer reflects what each session actually did — not just its
status dot.

---

## Two framings

### A. Mission Control (rules / visualization) — ~0 token
A timeline + current-state view. Renders the event log (below). Gives what raw
panes don't: a persistent cross-session history chain and a single glance.
Cheap, always-on, no model. **But** marginal over DIY multi-session.

### B. First Mate (LLM) — bounded, testable token cost
A model (default Sonnet) maintains a **compact running understanding** of each
session: high-level state most of the time, dipping to the session's last
message (low-level) only when needed. Collapses N panes into one conversation.
This is the real differentiator. Token cost is "not particularly low, not
particularly high" — **must be measured in real daily use**, not assumed.

These are **not** mutually exclusive. They share a foundation.

---

## Resolution: shared substrate, deferred top layer

Both framings need the same thing underneath:

- per-session **current state** (working / waiting / done), and
- an append-only **event log** (the history chain).

That foundation is **no-regret** — the First Mate needs it to read; the
visualization needs it to render. **Build the substrate first.** The top layer
(render-only vs Sonnet-narrated vs both) is an **experiment**, fork-friendly,
decided after the substrate exists and token cost is measured.

Note: **planning is explicitly out of scope.** The user always decides the next
step and what each session does. So the LLM layer is "understand & narrate," not
"decide / plan." That removes the most expensive model use entirely.

---

## The substrate (build regardless of the decision)

### Current state — exists
`~/.helm/sessions/runtime.json` is a snapshot map
`{pane_id: {harness, cwd, state, start_time}}`, overwritten each tick. Good for
"now," but it has **no history** — it cannot answer "what happened across the
fleet in the last hour."

### Event log — the missing piece
An append-only `~/.helm/sessions/events.jsonl`, one line per event:

```jsonl
{"ts":..,"pane":2,"ev":"spawn","harness":"claude","cwd":"helm","task":"fix #452"}
{"ts":..,"pane":2,"ev":"state","to":"working"}
{"ts":..,"pane":2,"ev":"state","to":"waiting"}
{"ts":..,"pane":2,"ev":"dispatch","text":"run the full test suite"}
{"ts":..,"pane":2,"ev":"state","to":"done"}
```

Writers (all rules, 0 token):
- `helm-brain spawn` → logs the `spawn` event (with the initial task).
- `helm-brain send`  → logs the `dispatch` event (records what the user sent).
- the `watch` poll loop → logs a `state` event on every transition. The event
  source is the **existing watch loop** — pure Python, no Lua tracker change.

### Renderer
`helm-brain timeline` → reads `events.jsonl`, renders a global feed (who / when
/ what / current state) plus the current snapshot. Per-pane swimlanes or
reverse-chronological. The Brain view (`Cmd+1`) can render this directly instead
of a chat box. Dispatch stays manual: pick a pane, type the next step.

All of the above is **cloud-buildable and unit-testable** (JSONL append / read /
format) — no macOS, no model.

---

## The First Mate on top (the experiment)

If/when we layer the LLM back on:

- It maintains a **compact state digest**, not transcripts.
- It reads the **digested feed** (cheap), and dips to `cli get-text` for a
  pane's last message only when it needs the low-level detail.
- Optional `helm-brain digest <pane>`: a cheap model compresses a worker's noisy
  last output into one line for the feed. **Default off.** Polish, not core.

---

## Open decisions

- [ ] **Top layer**: visualization-only vs LLM-narrated vs both. Experiment;
      may warrant a fork to A/B.
- [ ] **First Mate token cost**: measure in real daily driving before
      committing to it as the headline.
- [ ] **Lineage depth**: (a) per-session lifecycle timeline + global feed —
      do this for V1; (b) cross-session dependency DAG (task A done → triggers
      task B) — deferred, it requires the user to declare deps and adds
      friction.

---

## North-star test (repeat)

Every Brain design must beat **"just open N sessions yourself."** If a proposed
feature doesn't clear that bar, it isn't the differentiator.
