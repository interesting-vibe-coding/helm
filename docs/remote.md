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
