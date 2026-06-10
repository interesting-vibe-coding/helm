# Remote access — steer the fleet from your phone

> Mobile = relay problem, not engine problem. `kaji-brain serve` already speaks
> HTTP+SSE; remote access is just getting a phone onto that socket safely.

## Path 1: Tailscale (recommended first — zero code)

One-time setup:

1. Mac: `brew install --cask tailscale-app` → open Tailscale.app → log in.
2. Phone: install Tailscale app → same account. Both devices now share a
   private tailnet (WireGuard, end-to-end encrypted, no ports opened).
3. Find the Mac's tailnet IP: `tailscale ip -4` (e.g. `100.x.y.z`).

Start the server (non-loopback bind **requires** a token — refuses to start
without one):

```sh
KAJI_BRAIN_TOKEN=<long-random-string> kaji-brain serve --host 0.0.0.0 --port 8787
```

Generate a token: `openssl rand -hex 24`.

From the phone (any HTTP client, or a browser for GET endpoints):

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
