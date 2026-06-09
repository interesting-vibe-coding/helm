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

## The "one panel" principle → the Brain is our own cockpit (leading direction)

Helm's spine is **less friction** — reduce the human's prefrontal load. The UX
consequence: you should live in **one panel**. Many agents work in the
background; you only ever look at one surface. You leave it only to drill into a
specific worker.

One panel has a sharp consequence for the visualization: if the timeline lives
in a *different* view than the conversation, flipping between them is itself
friction. So **the timeline and the conversation must share one surface.** That
forces a build decision — where does the fusion happen?

- **(X) Harness as container** — the panel *is* a coding-agent's TUI, and we
  render the timeline inside it. But Claude Code / opencode expose no clean
  "draw my widget in your TUI" hook, so this means **forking** — heavy
  maintenance, and a general agent TUI is the wrong shape for a fleet cockpit.
- **(Y) Helm as container** — the panel is **our own native surface**; the
  conversation is one region, the timeline another; the LLM is a *component* of
  our panel, not the shell that contains it.

**Leading direction: (Y).** Build the Brain as a **purpose-built Helm cockpit
TUI** — a *partial-capability harness of our own*:

- one surface: a live **timeline + state** region (native render of
  `events.jsonl`) alongside a **conversation** region;
- under the conversation, a thin, **model-swappable loop** (model API +
  `helm-brain` tools: sessions / send / spawn / notify), with the trust gate
  intact;
- terminal UI is Helm's home turf (termwiz widgets, overlays, panes), so the
  cockpit is in range without forking anything.

Why a purpose-built cockpit beats forking opencode:
- the Brain's scope is already small (no planning — understand / narrate /
  propose routing), so **writing those few things is less code than maintaining
  a fork**, and shaped exactly right;
- no long-term merge tax against a fast-moving upstream (forking fights the
  less-friction spine);
- the model stays swappable (Claude / OpenRouter free / local).

Consequences:
- **The cockpit absorbs Monitor** — the timeline *is* Monitor's content. The
  Brain cockpit becomes home (conversation + fleet state on one screen); worker
  panes remain only for drill-down.
- **Keep the cockpit thin.** If the Brain needs to *investigate* a stuck worker,
  it does not grow capability — it `spawn`s a worker to do it. Heavy work stays
  in worker harnesses; the cockpit never becomes another general agent.
- opencode is **not** forked; it stays a worker harness (and an optional Brain
  backend for users who want a full agent).

Restated: not "fuse the visualization into a harness," but "**fuse the harness
(a thin loop) into our own panel**." The panel is ours; the LLM is a component.

---

## Open decisions

- [ ] **Brain container**: (X) fork a harness vs (Y) our own cockpit TUI.
      Leading toward (Y) — a purpose-built partial harness. Confirm before
      building.
- [ ] **Cockpit build surface**: TUI in the Brain pane (Python/Rust over the
      event feed) vs a GUI overlay. TUI is the cloud-buildable, lower-risk start.
- [ ] **Top layer**: visualization-only vs LLM-narrated vs both. Under (Y) these
      coexist in one cockpit; still measure whether the LLM earns its tokens.
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
