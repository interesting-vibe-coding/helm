# The Brain — Design Decision (pending)

> Status: **open decision**, captured 2026-06-09. Do not treat any framing
> below as shipped. The substrate is no-regret and can be built now; the top
> layer is an experiment to be decided after measuring real token cost.

This doc records a design discussion about what the Helm Brain / First Mate
should actually be. It supersedes the "Layer 4 is the headline" framing in
`ROADMAP.md` until the open decision is made.

---

## Update 2026-06-10 — the trunk is the service, the engine is a leaf

Reasoning backwards from the **killer feature — a phone app that manages every
harness (state + quota + steering) across the fleet** — reframed the whole
architecture:

- The phone and the desktop cockpit are **the same client shape**, both talking
  to a machine-side **helm-brain network service**. So the trunk is *making
  helm-brain a service + a relay + auth*, **not** picking an engine.
- The mobile-remote space is **already crowded** (Anthropic's own Remote
  Control, Omnara, Nimbalyst, Forge Remote, …) but every one is **single-vendor
  locked** (Claude-only / Claude+Codex). Kaji's wedge is **harness-agnostic
  unified fleet** — all harnesses, one app, shared memory/skills.
- The First Mate is a **thin stateless dispatcher** (NL → spawn/send,
  confirm-gated, no long conversation, no planning), so the heavy-engine
  justification (context mgmt / auto-compaction) largely collapses. The engine
  (Goose/opencode/Crush) becomes one *optional* client for synthesis — kept
  reversible by the helm-brain MCP layer. **Goose spike archived** (PR #116),
  not merged.
- **Quota is achievable after all.** No scriptable CLI exists, but Kaji holds
  the pane: inject `/usage` → scrape rendered output. A per-harness scraper
  adapter gives a **unified fleet quota view** nobody else has. (Currently
  `helm-quota` only sums *consumed* tokens; remaining/reset is the scrape TODO.)

**Build order (revised):** ✅ substrate (`events.jsonl`) → ✅ **helm-brain HTTP
service** (`helm-brain serve`, this change) → unified quota scraper → relay +
auth. Engine choice stays deferred.

### `helm-brain serve` (shipped 2026-06-10)
REST + SSE over stdlib `http.server`. Reads (sessions / quota / timeline /
state) run in-process; writes (send / spawn / notify) shell out to the tested
CLI — same thin-adapter philosophy as the MCP server. Binds `127.0.0.1` by
default; a non-loopback bind **requires a token** (refuses to start otherwise),
so the fleet API is never silently exposed. The cockpit gained a `--server URL`
mode and is now just one HTTP client — proving the client/server split the phone
will reuse.

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

Note: **autonomous planning is out of scope.** The user always decides *what* to
do; the LLM layer's job is to **dispatch** that intent — fan one instruction out
into `spawn`/`send` calls and create sessions — plus understand & narrate. It
does not decide the work itself, and every action is confirm-gated. (See § "The
dispatcher".) That keeps the model's job bounded and cheap.

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

**Leading direction: (Y) container, headless coding-agent engine.** The panel is
our own native surface; the conversation engine is an existing open-source
harness **running headless**, driven as a custom client. We own the surface and
the fusion; we do **not** own (fork/vendor) the agent engine.

Why not a from-scratch thin loop (an earlier proposal, now rejected): even
though the Brain doesn't *edit code*, it runs a **long-running multi-turn
conversation** (reads worker output, accumulates fleet state, dialogues with the
captain). That conversation needs **context orchestration + automatic
compaction + token control** — the hardest, least-obvious, easiest-to-botch
engineering, and it is needed regardless of whether the agent has coding
capability. These harnesses have evolved it over hundreds of releases;
reinventing it would almost certainly be worse. So ride proven engineering for
the engine.

The shape:

- **Engine** — a harness run headless (HTTP + SSE), providing the agent loop,
  **context management / auto-compaction**, provider plumbing (Claude /
  OpenRouter / local), and tool execution. We do **not** fork, vendor, or
  maintain this. (Candidate selection below.)
- **Eyes & hands** — expose `helm-brain` (sessions / send / spawn / notify) as an
  **MCP server**. Every candidate engine speaks MCP, so this **decouples the
  Brain's instruments from the engine choice** — switching engines later doesn't
  rewrite the tool layer. Trust gate intact.
- **Persona** — a constrained **custom agent** definition (the First Mate, scoped
  to understand / narrate / route — no planning).
- **Cockpit** — our own client that consumes the server's **SSE stream** to
  render the conversation, and renders the `events.jsonl` **timeline** on the
  same surface. Every pixel ours = the real fusion. Language-agnostic (the
  cockpit can be Rust, native to Helm); the engine stays behind HTTP.
- **Model** — swappable via the engine's provider config.

Net: **proven engineering (context / compaction / capability) is reused for
free; brand and fusion (cockpit UI + persona + MCP tools) are entirely ours;
zero fork.** The "minimal version we maintain" is the cockpit client + agent
config + the helm-brain MCP server — **not the engine.**

### Engine candidates (researched 2026-06-09)

| Engine | Lang | Runtime weight | Drivable server/API | MCP | Providers | Stars | License |
|---|---|---|---|---|---|---|---|
| **opencode** | TS + Zig | **heavy** (bun/node daemon) | **mature**: REST `POST /session/:id/message` + SSE + OpenAPI 3.1 + official SDK | ✓ | 75+ (OpenRouter, local) | ~172k | MIT |
| **Crush** (Charm) | **Go** | **lightest** (single binary, no deps) | `internal/server/` + `crush run` + `POST /v1/workspaces` + SSE exist, but read as **TUI↔TUI sharing**; public prompt-drive API **unverified** (needs source dive) | ✓ (stdio/http/sse) | many (OpenRouter, Ollama, LM Studio) | ~25k | MIT |
| **Goose** (Block) | **Rust** core (+TS) | flexible: **in-process crate** (no sidecar) / goosed / ACP | **strongest**: embed `goose` crate in-process, *or* goosed REST+SSE (~103 ep), *or* ACP (JSON-RPC). Same language as Helm | ✓ (70+) | 15+ (OpenRouter, Ollama) | ~48k | Apache-2.0 (Linux Foundation) |
| **Codex** (OpenAI) | Rust | light (single binary) | **none** documented; OpenAI-only | ✗ | OpenAI only | ~90k | Apache-2.0 |

### Drivability deep-dive (researched 2026-06-09)

The decisive criterion is: *can an external client fully drive a session
(create / send prompt / stream output) without being the harness's own TUI?*

- **opencode** — **confirmed, best-documented.** Official TS SDK
  (`@opencode-ai/sdk`): `session.create()`, `session.prompt()`, event stream,
  and `createOpencodeClient({ baseUrl })` for client-only mode against an
  already-running server. Endpoint families: sessions (incl. prompt/command/
  shell/share), files, config, tui, auth, events. Fully external-drivable.
  Cost: TS+Zig, runtime is a **bun/node daemon** (the weight).

- **Goose** — **strongest programmatic story, and Rust-native.** Three paths:
  1. the **`goose` core crate** — embed the agent **in-process** in a Rust app
     (Helm), no sidecar, no IPC at all (the lightest possible integration);
  2. **goosed** — the agent behind a bespoke **REST + SSE HTTP API (~103
     endpoints)**; the desktop app, mobile clients, and Slack bots already drive
     it over the network;
  3. **goose-acp-server** — the agent behind **ACP (Agent Client Protocol)**, an
     open JSON-RPC standard (Zed, JetBrains) over streamable HTTP/websocket.
  48k stars, Apache-2.0, Linux Foundation (AAIF) governance. Crates: `goose`
  (core), `goose-server` (goosed), `goose-cli`, `goose-mcp`, `goose-acp-*`.

- **Crush** — **lightest runtime, but the external-drive API is the least
  proven.** Go single binary, no deps; `internal/server/` exists, plus a
  `crush run` non-interactive one-shot and a `POST /v1/workspaces` + SSE server.
  But the server reads as **TUI↔TUI workspace sharing** (a workspace lives only
  while a client holds an SSE stream; keyed by `--cwd`), and a public
  prompt-driving HTTP API is **undocumented / still evolving** (see open issue
  "Crush HTTP interface"). MIT, Charm terminal-UX pedigree, MCP-native
  (stdio/http/sse), many providers. Confirming external session-drive needs a
  source dive into `internal/server/`.

**Revised recommendation (updated from the earlier "lead with Crush").** Goose
now looks like the front-runner for a Rust terminal: the **`goose` core crate
embeds in-process** — lighter than *any* sidecar (including Crush's Go binary,
which is still a separate process) and same language as Helm — with goosed
(REST+SSE) and ACP as drop-in alternatives if we want process isolation. Ranking
for our use:

1. **Goose** — Rust-native, in-process crate embed *or* goosed/ACP; most
   documented programmatic surfaces; well-governed. Top pick to prototype.
2. **opencode** — safest HTTP+SDK drive, most mature; accept the node daemon.
3. **Crush** — most elegant/lightest *if* its server can be externally driven;
   highest integration risk until `internal/server/` is verified.

The **helm-brain-as-MCP-server** instrument layer keeps this reversible: all
three speak MCP, so the engine can be swapped without rewriting the tools.

Bonus: goosed / `opencode serve` can each host **many sessions**, so a future
Helm-branded **worker** can ride the same engine and API. Non-engine workers
(claude / kiro / codex) still go through the uniform `helm-brain` abstraction.

Why not the other containers:
- **(X) fork a harness** — fast-moving upstreams, no clean in-TUI widget hook,
  and a brutal merge tax. Rejected.
- **Extract / vendor a minimal core** — same fast-moving core; worst of both.
  Rejected. The client-server APIs (and Goose's embeddable crate) make
  extraction unnecessary.

Consequences:
- **The cockpit absorbs Monitor** — the timeline *is* Monitor's content. The
  Brain cockpit becomes home (conversation + fleet state on one screen); worker
  panes remain only for drill-down.
- **Keep the cockpit thin.** If the Brain needs to *investigate* a stuck worker,
  it does not grow capability — it `spawn`s a worker to do it. Heavy work stays
  in worker harnesses; the cockpit never becomes another general agent.

Restated: not "fuse the visualization into a harness," but "**drive a headless
engine from our own panel**." The panel is ours; opencode is the engine behind
an HTTP boundary.

---

## Implication: mobile remote (the roadmap endgame)

The next roadmap step is **mobile remote control** — the desktop becomes a
controlled endpoint, a phone app steers it (cf. Anthropic's remote control). The
cockpit-as-client decision makes this nearly free, and it sharpens the engine
choice:

- **Desktop cockpit and the phone app are peers** — both are clients of the same
  headless engine API (same session drive, same SSE stream, same `events.jsonl`
  timeline). The mobile app is not a new system, just another client.
- **This favors an engine whose server is built for network clients.** Goose's
  **goosed** already serves mobile clients and Slack bots over the network;
  opencode's HTTP server is client-only-mode friendly. Crush's TUI↔TUI sharing
  server is the *least* suited to a remote, non-TUI client — another reason it
  drops behind for our use.
- **Nuance that flips one earlier preference:** Goose's *in-process crate embed*
  is lightest for the desktop, but it exposes **no network API**, so it can't be
  driven remotely. For the mobile endgame the clean shape is **run `goosed` (the
  server) on the machine**; the desktop cockpit talks to it locally and the
  phone talks to it through a relay — both clients. So remote control nudges the
  integration away from "embed the crate" toward "run the server."
- **Still missing:** (1) a **relay / tunnel** to expose the local engine to the
  phone safely (cf. `kaku-relay`), and (2) **auth**.

---

## Decision & sequencing (2026-06-09)

**Functionality first.** The UI/aesthetics look good and the core agent loop is
now **verified end-to-end** (2026-06-09). The whole engine redesign below (Goose /
cockpit / mobile) is a **north star, not the next task** — chasing it now would
push "Kaji is actually usable" out indefinitely. Pretty shell + broken core =
demo-ware.

Agreed build order:

1. ✅ **Prove the existing loop end-to-end (done, 2026-06-09).** Using what
   already ships — `helm-brain` + claude workers, no new engine: spawn worker
   (Cmd+Shift+K) → Monitor (Cmd+3) lists it → worker hits *waiting* → Brain
   `notify` fires → session restore after restart. Walked each link; working.
   (This was the long-standing ROADMAP P0 "Core agent loop, end-to-end.")
2. ✅ **Substrate `events.jsonl` (done, 2026-06-09).** No-regret, cloud-built,
   unit-tested, engine-independent. `helm-brain` now appends `spawn`/`dispatch`/
   `state` events and renders `helm-brain timeline [--json]`. This is the data
   layer the cockpit renders. (PR #115.)
3. **Pure-visualization cockpit (now — the next task).** See § "Visualization
   first" below. Build the cockpit as render-only and **live in it for several
   days** before adding any model. This both ships real value and answers the
   north-star test from evidence rather than assumption.
4. **The dispatcher (a lightweight LLM) — needed, built on top of the cockpit.**
   The LLM's job is now concrete: **dispatch** — turn one natural-language
   instruction ("fix the failing tests in kaji and mira") into `spawn` / `send`
   calls and create/route worker sessions. This is the fan-out the user
   shouldn't do by hand; it is *not* autonomous planning (the user gives the
   intent, every action is confirm-gated). See § "The dispatcher" below.

**Visualization first, then a lightweight dispatcher (consensus, evolved
2026-06-09 evening).** The cockpit ships first (it is necessary either way and
is the surface the dispatcher acts beside), but we **do** want the LLM layer —
not for narration, but because **something has to fan a single instruction out
into multiple sessions**. The earlier "maybe no LLM at all" resolved to: yes,
but make it as light as possible. Why the order and the shape still hold:

- **The cockpit is necessary either way**, so build it first with zero regret:
  it is the render-only product *and* the surface the dispatcher acts beside
  (the LLM is a component, not the shell).
- **Marginal-on-its-own is still worth it.** Even bare, the cockpit collapses
  "scan N panes" into an O(1) glance + persistent history, on top of Kaji's real
  differentiators — cross-harness **memory** + **chat history** — on an
  already-handsome terminal. The dispatcher then adds the active half.

**Mobile is a relay problem, not an engine problem (consensus 2026-06-09).** A
render-only Brain does not need `goosed` for remote control — the phone just
needs a lightweight **relay** exposing `runtime.json` + `events.jsonl` +
`helm-brain send`. Goose's network engine only wins *if* the Brain top layer is
a live LLM conversation you want to chat with from the phone. So mobile is
**decoupled** from the engine choice and must not drive it prematurely.

## The dispatcher (the lightweight LLM layer)

**Job:** one NL instruction → `spawn` / `send` fan-out across sessions. Dispatch,
not planning; user gives intent; confirm-gated.

**Key consequence of having built the substrate: the dispatcher is near
*stateless*, so it needs no heavy engine.** Each dispatch reads the current
fleet fresh from the substrate (`helm-brain sessions` + `timeline`), adds the
user's instruction, and emits tool calls. There is no giant accumulating
conversation to compact — so **auto-compaction / context-orchestration, the
main reason Goose was ranked #1, is no longer required.** That re-opens
"lightest wins."

**Shape (elegant, minimal):**

```
  cockpit (render-only, built)  ──┐  shared substrate
     fleet state / history        │  (events.jsonl + sessions)
  dispatcher = lightest harness ──┘  + cheap model (DeepSeek / Flash)
        │  acts only through ↓ (scoped + confirm-gated)
  helm-brain as MCP server  (sessions / send / spawn / notify / timeline)
```

- **Constraint framework = `helm-brain` exposed as an MCP server.** The model
  gets only those scoped tools — it can dispatch but can't wander; the trust /
  confirm gate stays. Harness-agnostic: swapping the harness doesn't touch the
  tool layer. **This is the next no-regret, cloud-buildable piece.**
- **Lightest harness — leaning Crush.** With compaction no longer needed, Crush
  (Charm; Go single static binary; MCP-native; OpenRouter/Ollama → free models)
  becomes the front-runner. Its earlier weakness (unverified external HTTP
  drive) does **not** apply when we run it *locally as the dispatcher the user
  types into* rather than driving it headless. Goose drops to second; opencode's
  node daemon is heaviest. Confirm the pick with a live run.
- **Surface — dispatcher-as-pane beside the cockpit** (lightest; no headless
  drive plumbing). Mobile later = a relay forwarding instructions to it +
  streaming cockpit state.

**Correction to the earlier Goose rationale.** Goose was ranked #1 for its
in-process crate embed and proven context management. The mobile endgame already
mooted the embed (remote control needs a network API). Now the substrate moots
the context-management edge too (stateless dispatch). What's left for Goose is
"Rust, no node runtime, LF governance" — real but no longer decisive against a
lighter MCP-native harness like Crush. **Decide on lightness + MCP fit, with a
live run.**

---

## Open decisions

- [x] **LLM layer needed?** **Yes** — as a lightweight **dispatcher** (NL →
      spawn/send fan-out + session creation), not narration, not planning. Kept
      as light as possible (near-stateless on the substrate).
- [x] **Engine class**: not a heavy headless engine after all. The substrate
      makes dispatch near-stateless, removing the need for auto-compaction. Ride
      the **lightest MCP-native harness** as a local dispatcher.
- [~] **Which harness**: **leaning Crush** (Go single binary, MCP-native, free
      models via OpenRouter). Goose second; opencode (node) heaviest. The Goose
      drivability spike (PR #116) is code-ready but the headless-drive concern
      it tests is **moot** if we run the harness locally rather than driving it.
      Confirm Crush with a live run.
- [x] **Instrument layer**: expose `helm-brain` as an **MCP server** — the
      constraint framework the dispatcher acts through. Harness-agnostic; the
      next no-regret, cloud-buildable piece.
- [~] **Cockpit build surface**: **TUI-first** (render-only, in the Brain pane,
      reading `events.jsonl` + `runtime.json`; shipped in PR #117). Promote to a
      native GUI overlay only after the TUI proves the layout.
- [~] **Dispatcher surface**: **lean dispatcher-as-pane** the user types into,
      beside the cockpit (lightest; no headless-drive plumbing). Revisit only if
      a cockpit-drives-headless shape proves clearly better.
- [ ] **Token cost**: measure the dispatcher on a cheap model (DeepSeek / Flash)
      in real use; keep per-dispatch context to the fleet snapshot + instruction.
- [ ] **Mobile relay**: render-only mobile needs a `runtime.json` +
      `events.jsonl` + `helm-brain send` relay (cf. `kaku-relay`) + auth —
      independent of the engine choice.
- [ ] **Lineage depth**: (a) per-session lifecycle timeline + global feed —
      do this for V1; (b) cross-session dependency DAG (task A done → triggers
      task B) — deferred, it requires the user to declare deps and adds
      friction.

---

## Work view layout (deferred polish)

The Work view (`Cmd+2`) is a backup "see all live workers" surface — you live in
the Brain; Work is for an eyeball glance. Workers are tiled in one tab: the first
opens the Work tab, each later worker is added by `helm-brain spawn` splitting the
**largest** existing worker pane along its longer (pixel) side. This self-balances:
2 → equal columns, 4 → even 2×2, 3 → a balanced 2+1 (not three equal columns).

Open: if we ever want count-specific layouts (e.g. 3 → three equal columns *and*
4 → 2×2), the self-balancing rule can't express both — that needs a full re-tile
on every spawn (`--move-pane-id` + `--percent`), which is heavier and needs visual
iteration. Deferred: layout polish is explicitly **not** the priority while the
core chain (spawn → Work → notify → restore) is still being proven end-to-end.

## North-star test (repeat)

Every Brain design must beat **"just open N sessions yourself."** If a proposed
feature doesn't clear that bar, it isn't the differentiator.
