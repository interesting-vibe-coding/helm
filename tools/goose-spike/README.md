# goose-spike

> Post-V1 engine spike for the Brain. **Status: WIP — pure-logic done, live run is yours.**
> See `docs/BRAIN_DESIGN.md` § "Engine candidates" / "Decision & sequencing".

## The question this answers

Can an **external client** (not goose's own TUI) fully drive a Goose session —
**create → set provider → prompt → consume the streamed reply** — over goosed's
HTTP API?

- **Yes** → commit to **Goose** as the Brain's headless engine (Rust, same
  language as Kaji, no bun/node runtime to ship, built to serve network clients
  — the reasons in `BRAIN_DESIGN.md`).
- **No / too painful** → fall back to **opencode** (accept the node daemon; its
  HTTP+SDK drive is the most mature).

Either way, the plan is to expose `helm-brain` as an **MCP server** so the engine
stays swappable — this spike does **not** wire goose into Kaji, it only settles
the drivability question.

## What's here

| file | what | needs network? |
|------|------|----------------|
| `sse.py` | engine-agnostic W3C SSE parser | no |
| `goose_client.py` | goosed client: `build_*` / `parse` / `render` (pure) + `start_agent` / `update_provider` / `reply_stream` / `drive` (I/O) + CLI | only the I/O fns |
| `test_sse.py`, `test_goose_client.py` | 22 stdlib `unittest` cases for the pure logic + a fake-stream integration test | no |

Pure stdlib — no `pip install`. Run the tests anywhere:

```sh
cd tools/goose-spike && python3 -m unittest discover -p 'test_*.py'
```

## Verified in the cloud (no Mac, no goosed)

- SSE framing parse (`data: {json}\n\n`, multi-line data, comments/heartbeats, CRLF).
- Request shaping: the `Message` (camelCase) + `ChatRequest` (snake_case) bodies.
- Event rendering: `Message` → assistant text, `Error`/`Finish` terminal, `Ping`/others.
- The full reply loop on a **fake** stream (parser → render → stop on Finish).

## Left for you — live run on macOS (the actual spike)

This is the part a container can't do (needs the `goosed` binary + a provider key).

```sh
# 1. Install goose (gives you the `goosed` binary), then configure a provider
#    once so its API key lands in goose's own config/keychain:
goose configure                 # pick e.g. Anthropic, paste the key

# 2. Launch the server. TLS is ON by default (self-signed) — turn it off for a
#    plain-HTTP client, and set the secret yourself (else goosed generates a
#    random one and does NOT print it):
GOOSE_SERVER__SECRET_KEY=devkey GOOSE_TLS=false GOOSE_PORT=3000 goosed agent

# 3. Drive it from this client (separate shell):
export GOOSE_SERVER__SECRET_KEY=devkey
python3 tools/goose-spike/goose_client.py \
    --provider anthropic --model claude-sonnet-4-6 \
    "Say hello in one short sentence."
```

Expected: the client prints `[session <id>]`, streams the assistant text to
stdout, then `[finish: stop]`. That = **the spike succeeds**, commit to Goose.

If goosed insists on TLS, drop `GOOSE_TLS=false` and use
`--base-url https://127.0.0.1:3000 --insecure` instead.

**Record the result** in `docs/BRAIN_DESIGN.md` § "Open decisions → Which engine"
(works / doesn't, plus the round-trip latency + any friction), so the engine
choice is settled with evidence.

## Caveats (read before trusting the wire details)

Verified against **`block/goose` @ `main`, 2026-06-09** — these are the desktop
app's internal IPC routes, **not a documented public API**, and `main` is
unversioned. Re-check against the commit you build `goosed` from:

- `POST /agent/start {working_dir}` → `Session` (read `id`).
- `POST /agent/update_provider {session_id, provider, model?}` — provider key
  must already be in goose config. May be skippable if the session already has a
  provider.
- `POST /reply {user_message, session_id}` → `text/event-stream`; events are
  `data: {MessageEvent}\n\n` with **no `event:` line**; tagged by `"type"`
  (`Message`/`Error`/`Finish`/`Ping`/…); terminal event is `Finish`.
- Auth: `X-Secret-Key: <secret>` on every request.
- Lower-confidence / unverified: exact `goose_mode` string set; whether
  `update_provider` is strictly required; `TokenState`/`Notification` field
  shapes (we ignore them).

Sources: `crates/goose-server/src/{main,auth,configuration}.rs`,
`routes/{reply,agent,session}.rs`, `commands/agent.rs`;
`crates/goose-providers/src/conversation/message.rs`. (block/goose @ main.)
