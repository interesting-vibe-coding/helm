# Remote access — steer the fleet from your phone

> Mobile = relay problem, not engine problem. `kaji-brain serve` already speaks
> HTTP+SSE; remote access is just getting a phone onto that socket safely.

## Path 1: Tailscale (recommended first — zero code)

One-time setup:

1. Mac — two variants:
   - **GUI**: `brew install --cask tailscale-app` → open Tailscale.app → log
     in. Needs admin rights (pkg + system extension).
   - **CLI userspace (no admin, verified)**: `brew install tailscale`, then
     ```sh
     tailscaled --tun=userspace-networking \
       --statedir ~/.local/share/tailscaled \
       --socket ~/.local/share/tailscaled/sock &
     tailscale --socket ~/.local/share/tailscaled/sock up --hostname kaji-mac
     ```
     No root, no kernel/system extension; netstack forwards inbound tailnet
     connections to localhost services, so `kaji-brain serve` can stay bound
     to `127.0.0.1`.
2. Phone: install Tailscale app → same account. Both devices now share a
   private tailnet (WireGuard, end-to-end encrypted, no ports opened).
3. Find the Mac's tailnet IP: `tailscale ip -4` (e.g. `100.x.y.z`).

Start the server. A token is always recommended; a non-loopback bind
**requires** one (refuses to start otherwise):

```sh
KAJI_BRAIN_TOKEN=<long-random-string> kaji-brain serve --host 127.0.0.1 --port 8787
```

(Bind `0.0.0.0` instead if using the GUI variant — its tun device delivers
inbound traffic to the real interface, not localhost.)

Generate a token: `openssl rand -hex 24`.

From the phone, open `http://100.x.y.z:8787/` in the browser — the built-in
**mobile cockpit**. Enter the token once (kept in localStorage); it shows the
fleet (sessions, state dots, runtime, quota) and sends instructions to any
worker. Add to Home Screen for an app-like feel. A native app may come later;
the web page is deliberately first.

Raw API (any HTTP client):

```
GET  http://100.x.y.z:8787/api/state      # fleet snapshot (sessions + quota)
GET  http://100.x.y.z:8787/api/sessions   # worker list
GET  http://100.x.y.z:8787/api/timeline   # recent events
GET  http://100.x.y.z:8787/api/events     # SSE live stream
POST http://100.x.y.z:8787/api/send       # {"pane_id": N, "text": "..."} steer a worker
POST http://100.x.y.z:8787/api/spawn      # {"cwd": "...", "harness": "claude"} new worker
```

Every request needs `Authorization: Bearer <token>`.

Security model: Tailscale provides the encrypted private network (nothing is
exposed to the public internet); the bearer token guards against other devices
on the same tailnet. Both layers are required.

## Path 1.5: Tailscale Funnel (no app on the phone, no VPN slot)

If the phone can't (or shouldn't) run the Tailscale app — e.g. iOS has a single
VPN slot and it's taken by a proxy — expose the cockpit over Funnel instead:

```sh
tailscale funnel --bg 8787       # one-time: approve the printed admin URL
```

This publishes `https://<host>.<tailnet>.ts.net/` on the public internet via
Tailscale's ingress (TLS terminated with an auto-provisioned cert; traffic
proxied to 127.0.0.1:8787). The phone needs nothing installed and keeps its
own VPN/proxy on.

Security model shifts: the tailnet no longer gates access — **the bearer token
is the only gate**. Use a long random token (`openssl rand -hex 24`), treat the
URL as semi-secret, and turn Funnel off (`tailscale funnel off`) when unused.
`/healthz` and the static cockpit page are open by design; everything under
`/api/*` 401s without the token.

Verified (2026-06-11): public `https://kaji-mac.taild66623.ts.net/` — healthz
ok, /api/* 401 without token, 200 with token, reachable from China mobile
networks without touching the phone's VPN slot.

## Prior art — how the others connect a phone (researched 2026-06-11)

All shipped competitors use the same shape: **no inbound ports, the dev
machine dials OUT to a relay; the phone talks to the relay**. Nobody uses a
VPN/tailnet.

| Product | Transport | Notes |
|---------|-----------|-------|
| Anthropic Remote Control (`claude rc`) | local proc polls Anthropic API over outbound HTTPS; QR pairing | E2E encrypted; Claude Code only |
| Omnara (YC) | encrypted relay (their cloud), Agent-SDK based | closed SaaS; web/mobile/watch clients |
| Happy (slopus/happy, OSS) | CLI wrapper → relay (~1.3k LOC TS, self-hostable) → app; AES-256-GCM, QR key exchange | best open reference implementation |
| happier (fork) | same, multi-harness (Codex/OpenCode/…) | closest competitor to Kaji's harness-agnostic wedge |

Implication for Kaji: the end-state is a thin self-hosted relay (Mac dials out
over WebSocket, phone connects over HTTPS, QR pairing + E2E crypto), which
also solves China reachability. Tailscale/Funnel are stepping stones that cost
zero code while the cockpit feature set is iterated.

## Path 2: self-hosted relay (later)

For users without Tailscale: a small public relay (cf. `kaku-relay`) that the
Mac dials out to and the phone connects through. Decided but not built —
Tailscale path must prove the phone workflow is worth it first. See
`docs/BRAIN_DESIGN.md` § mobile relay.

## Known limits

- The serve process must be running on the Mac (started by the Brain launcher
  or manually). No daemon/launchd unit yet.
- SSE over tailnet works but iOS Safari backgrounds kill the stream; poll
  `/api/state` as the fallback.
