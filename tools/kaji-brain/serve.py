#!/usr/bin/env python3
"""kaji-brain serve — the fleet over HTTP.

The trunk of Kaji's remote story. Exposes the same eyes & hands as the
`kaji-brain` CLI, but over HTTP + Server-Sent Events, so that *any* client —
the desktop cockpit, a phone app behind a relay, a script — drives one fleet
through one API. The cockpit and the phone are peers: same endpoints, same
event stream, different device.

Design mirrors the MCP server (tools/kaji-brain/mcp_server.py): a thin adapter.
  • Reads  (sessions / quota / timeline / state)  → in-process functions from
    brain.py (fast, no subprocess).
  • Writes (send / spawn / notify)                → shell out to the tested
    `kaji-brain` CLI, so the action logic lives in exactly one place.

Endpoints
  GET  /healthz                 → {"ok": true}                 (no auth)
  GET  /api/state               → {sessions, quota, ts}        (one glance)
  GET  /api/sessions            → [ {pane_id, harness, ...} ]
  GET  /api/quota               → {harness: tokens_today}
  GET  /api/timeline[?pane=N]   → [ events ]  (oldest first)
  GET  /api/events              → text/event-stream: a `state` event every
                                  POLL secs + new timeline events as they land
  POST /api/send    {pane_id, text}            → inject text + Enter
  POST /api/spawn   {harness, cwd, task?}      → open a worker, {"pane_id": N}
  POST /api/notify  {title, msg}               → macOS notification

Security
  Binds 127.0.0.1 by default (localhost only). Binding a non-loopback host
  (for a relay) REQUIRES a token — the server refuses to start otherwise, so a
  fleet-control API is never silently exposed unauthenticated. When a token is
  set (env KAJI_BRAIN_TOKEN or --token), every /api/* request must carry
  `Authorization: Bearer <token>`; /healthz stays open for liveness checks.
"""

import json
import os
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Reuse the CLI's data layer. brain.py only runs definitions on import (its
# work is guarded by __main__), so importing it is free.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain  # noqa: E402

# SSE state-push cadence (secs). The history tail is checked on the same beat.
POLL_SECS = float(os.environ.get("KAJI_BRAIN_SSE_POLL", "2"))

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", ""}


def _spawn_via_cli(harness, cwd, task):
    """Run `kaji-brain spawn ...`; return (rc, parsed_json_or_error_dict)."""
    argv = ["spawn", str(harness), str(cwd)]
    if task:
        argv.append(str(task))
    # Re-enter this very module's CLI so spawn logic stays in one place.
    cli = brain._helm_cli()
    if not cli:
        return 1, {"error": "kaji cli not available (Kaji not running?)"}
    # brain.cmd_spawn prints JSON to stdout; capture it.
    import io
    import contextlib
    buf = io.StringIO()
    rc = 0
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = brain.cmd_spawn(argv[1:])
    out = buf.getvalue().strip()
    try:
        return rc, json.loads(out) if out else {"error": "no output"}
    except Exception:
        return rc, {"error": out or "spawn failed"}


def _send_via_cli(pane_id, text):
    cli = brain._helm_cli()
    if not cli:
        return 1, "kaji cli not available (Kaji not running?)"
    rc, err = brain._send_text(cli, pane_id, text)
    if rc == 0:
        brain.append_event("dispatch", pane=brain._as_pane(pane_id), text=text)
    return rc, err


def _notify_via_cli(title, msg):
    rc = brain.cmd_notify([str(title), str(msg)])
    return rc, ("" if rc == 0 else "notify failed")


def build_state():
    """The one-glance payload: live sessions + quota + a server timestamp."""
    return {
        "sessions": brain.collect_sessions(),
        "quota": brain.load_quota(),
        "ts": int(time.time()),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "kaji-brain/1.0"
    # Set by the factory below.
    token = None

    # ── helpers ───────────────────────────────────────────────────────────
    def log_message(self, fmt, *args):  # quieter than the default
        if os.environ.get("KAJI_BRAIN_VERBOSE"):
            super().log_message(fmt, *args)

    def _authed(self):
        if not self.token:
            return True
        got = self.headers.get("Authorization", "")
        return got == "Bearer " + self.token

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            n = 0
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # ── routing ───────────────────────────────────────────────────────────
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            return self._json({"ok": True})
        if not self._authed():
            return self._json({"error": "unauthorized"}, 401)

        if path == "/api/state":
            return self._json(build_state())
        if path == "/api/sessions":
            return self._json(brain.collect_sessions())
        if path == "/api/quota":
            return self._json(brain.load_quota())
        if path == "/api/timeline":
            pane = self._query_pane()
            events = brain.read_events()
            if pane is not None:
                events = [e for e in events if e.get("pane") == pane]
            return self._json(events)
        if path == "/api/events":
            return self._stream_events()
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if not self._authed():
            return self._json({"error": "unauthorized"}, 401)
        body = self._read_body()

        if path == "/api/send":
            pane_id, text = body.get("pane_id"), body.get("text")
            if pane_id is None or text is None:
                return self._json({"error": "pane_id and text required"}, 400)
            rc, err = _send_via_cli(pane_id, text)
            return self._json({"ok": rc == 0, "error": err} if rc else {"ok": True}, 200 if rc == 0 else 502)
        if path == "/api/spawn":
            harness, cwd = body.get("harness"), body.get("cwd")
            if not harness or not cwd:
                return self._json({"error": "harness and cwd required"}, 400)
            rc, payload = _spawn_via_cli(harness, cwd, body.get("task", ""))
            return self._json(payload, 200 if rc == 0 else 502)
        if path == "/api/notify":
            title, msg = body.get("title", "Kaji"), body.get("msg", "")
            rc, err = _notify_via_cli(title, msg)
            return self._json({"ok": rc == 0, "error": err} if rc else {"ok": True}, 200 if rc == 0 else 502)
        return self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):  # CORS preflight (phone / browser clients)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def _query_pane(self):
        if "?" not in self.path:
            return None
        q = self.path.split("?", 1)[1]
        for part in q.split("&"):
            if part.startswith("pane="):
                try:
                    return int(part[5:])
                except ValueError:
                    return None
        return None

    def _stream_events(self):
        """SSE: push a `state` snapshot every POLL_SECS + tail new events."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        seen = len(brain.read_events())
        try:
            while True:
                # New history events since last beat.
                events = brain.read_events()
                if len(events) > seen:
                    for e in events[seen:]:
                        self._sse("event", e)
                    seen = len(events)
                # Current fleet snapshot.
                self._sse("state", build_state())
                time.sleep(POLL_SECS)
        except (BrokenPipeError, ConnectionResetError):
            return  # client went away; end the stream quietly

    def _sse(self, event, data):
        payload = "event: %s\ndata: %s\n\n" % (event, json.dumps(data, ensure_ascii=False))
        self.wfile.write(payload.encode("utf-8"))
        self.wfile.flush()


def make_handler(token=None):
    """Return a Handler subclass bound to a token (for tests / embedding)."""
    return type("BoundHandler", (Handler,), {"token": token})


def run(host="127.0.0.1", port=8765, token=None):
    token = token or os.environ.get("KAJI_BRAIN_TOKEN") or None
    if host not in LOOPBACK_HOSTS and not token:
        sys.stderr.write(
            "refusing to bind non-loopback host %r without a token.\n"
            "set KAJI_BRAIN_TOKEN or pass --token to expose the fleet safely.\n"
            % host
        )
        return 2
    httpd = ThreadingHTTPServer((host, port), make_handler(token))
    where = "%s:%d" % (host or "127.0.0.1", port)
    auth = "token-protected" if token else "localhost-only, no token"
    sys.stderr.write("kaji-brain serve → http://%s  (%s)\n" % (where, auth))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\nshutting down.\n")
    finally:
        httpd.server_close()
    return 0


def cmd_serve(args):
    """CLI entry: kaji-brain serve [--host H] [--port P] [--token T]."""
    host, port, token = "127.0.0.1", 8765, None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--host" and i + 1 < len(args):
            host = args[i + 1]; i += 2
        elif a == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                sys.stderr.write("invalid --port\n"); return 2
            i += 2
        elif a == "--token" and i + 1 < len(args):
            token = args[i + 1]; i += 2
        else:
            sys.stderr.write("usage: kaji-brain serve [--host H] [--port P] [--token T]\n")
            return 2
    return run(host=host, port=port, token=token)


if __name__ == "__main__":
    sys.exit(cmd_serve(sys.argv[1:]))
