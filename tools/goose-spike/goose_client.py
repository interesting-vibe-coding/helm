#!/usr/bin/env python3
"""goose_client — a minimal external client that drives a goosed session.

The post-V1 engine spike from docs/BRAIN_DESIGN.md: prove that an external
client (not goose's own TUI) can fully drive a Goose session end-to-end —
**create → set provider → prompt → consume the SSE stream**. If this works, we
commit to Goose as the Brain's headless engine; if not, we fall back to
opencode. Either way the `helm-brain`-as-MCP instrument layer keeps the engine
swappable.

This file is pure stdlib (urllib + the sibling sse.py) so it ships with no
dependencies. The wire details below are verified against block/goose @ main
(2026-06-09) — see README.md for exact source citations. Because they come from
`main` (unversioned) and are the desktop app's internal IPC routes, treat them
as unstable and re-check against the commit you build goosed from.

The request/response *shaping* is split out as pure functions (build_*, parse_*,
render_event) so it can be unit-tested with no server running; only drive() and
the _post helpers touch the network.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, Iterator, List, Optional, Tuple

# sse.py lives next to this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sse import iter_events  # noqa: E402

DEFAULT_BASE_URL = "http://127.0.0.1:3000"
SECRET_ENV = "GOOSE_SERVER__SECRET_KEY"  # goosed reads its secret from this var
AUTH_HEADER = "X-Secret-Key"             # ...and checks it on every request


# ── pure request/response shaping (no network — unit-tested) ──────────────────

def build_user_message(text: str, created: Optional[int] = None) -> Dict:
    """A goose `Message` (camelCase). `created` is a required unix-seconds i64.

    Minimal valid shape: role + created + one text content item + metadata.
    Mirrors the Rust `Message::user().with_text(...)` builder.
    """
    return {
        "role": "user",
        "created": int(time.time()) if created is None else int(created),
        "content": [{"type": "text", "text": text}],
        "metadata": {"userVisible": True, "agentVisible": True},
    }


def build_reply_request(text: str, session_id: str) -> Dict:
    """Body for `POST /reply`. NOTE: ChatRequest is snake_case (no rename_all)."""
    return {"user_message": build_user_message(text), "session_id": session_id}


def parse_event(data_str: str) -> Optional[Dict]:
    """Parse one SSE `data:` payload (a MessageEvent) into a dict. None if junk."""
    try:
        obj = json.loads(data_str)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def extract_message_text(message: Dict) -> str:
    """Join the text content items of a goose Message (skip non-text parts)."""
    parts: List[str] = []
    for item in (message or {}).get("content", []) or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text", ""))
    return "".join(parts)


def render_event(ev: Dict) -> Tuple[str, str]:
    """Map a MessageEvent dict to (kind, text) for display / control flow.

    kind ∈ {message, error, finish, ping, other}. `finish` text is the reason.
    MessageEvent is externally tagged by "type" (Message/Error/Finish/Ping/...).
    """
    t = (ev or {}).get("type")
    if t == "Message":
        return "message", extract_message_text(ev.get("message", {}))
    if t == "Error":
        return "error", str(ev.get("error", ""))
    if t == "Finish":
        return "finish", str(ev.get("reason", ""))
    if t == "Ping":
        return "ping", ""
    return "other", str(t)


def is_terminal(kind: str) -> bool:
    """The stream is done after a Finish or an Error."""
    return kind in ("finish", "error")


# ── network I/O ───────────────────────────────────────────────────────────────

def _ssl_ctx(insecure: bool):
    # goosed defaults to TLS-on with a self-signed cert (GOOSE_TLS=true). For a
    # plain client either launch goosed with GOOSE_TLS=false (http) or pass
    # --insecure to skip verification of the self-signed cert over https.
    if not insecure:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _request(base_url: str, path: str, secret: str, body: Dict, insecure: bool):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base_url.rstrip("/") + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header(AUTH_HEADER, secret)
    return urllib.request.urlopen(req, context=_ssl_ctx(insecure), timeout=120)


def _post_json(base_url: str, path: str, secret: str, body: Dict, insecure: bool) -> Dict:
    with _request(base_url, path, secret, body, insecure) as resp:
        raw = resp.read().decode("utf-8", "replace")
    return json.loads(raw) if raw.strip() else {}


def start_agent(base_url: str, secret: str, working_dir: str, insecure: bool) -> str:
    """POST /agent/start {working_dir} → Session; return its `id`."""
    session = _post_json(base_url, "/agent/start", secret,
                         {"working_dir": working_dir}, insecure)
    sid = session.get("id")
    if not sid:
        raise RuntimeError("no session id in /agent/start response: %r" % session)
    return sid


def update_provider(base_url: str, secret: str, session_id: str,
                    provider: str, model: Optional[str], insecure: bool) -> None:
    """POST /agent/update_provider — pick provider/model for the session.

    The provider's API key must already be in goose's own config/keychain. May
    be unnecessary if the session already carries a provider from config.
    """
    body = {"session_id": session_id, "provider": provider}
    if model:
        body["model"] = model
    _post_json(base_url, "/agent/update_provider", secret, body, insecure)


def reply_stream(base_url: str, secret: str, text: str, session_id: str,
                insecure: bool) -> Iterator[Tuple[str, str]]:
    """POST /reply, stream the text/event-stream, yield (kind, text) per event."""
    body = build_reply_request(text, session_id)
    with _request(base_url, "/reply", secret, body, insecure) as resp:
        lines = (raw.decode("utf-8", "replace") for raw in resp)
        for sse in iter_events(lines):
            ev = parse_event(sse.data)
            if ev is None:
                continue
            kind, payload = render_event(ev)
            yield kind, payload
            if is_terminal(kind):
                return


def drive(base_url: str, secret: str, prompt: str, working_dir: str,
          session_id: Optional[str], provider: Optional[str],
          model: Optional[str], insecure: bool) -> int:
    """End-to-end: (start →) (update_provider →) reply → print assistant text."""
    if not session_id:
        session_id = start_agent(base_url, secret, working_dir, insecure)
        print("[session %s]" % session_id, file=sys.stderr)
    if provider:
        update_provider(base_url, secret, session_id, provider, model, insecure)
        print("[provider %s%s]" % (provider, "/" + model if model else ""), file=sys.stderr)

    saw_error = False
    for kind, payload in reply_stream(base_url, secret, prompt, session_id, insecure):
        if kind == "message":
            if payload:
                sys.stdout.write(payload)
                sys.stdout.flush()
        elif kind == "error":
            saw_error = True
            print("\n[error] %s" % payload, file=sys.stderr)
        elif kind == "finish":
            print("\n[finish: %s]" % payload, file=sys.stderr)
    print()
    return 1 if saw_error else 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Drive a goosed session: create → prompt → consume SSE.")
    ap.add_argument("prompt", help="the user prompt to send")
    ap.add_argument("--base-url", default=os.environ.get("GOOSE_BASE_URL", DEFAULT_BASE_URL),
                    help="goosed base URL (default %s)" % DEFAULT_BASE_URL)
    ap.add_argument("--working-dir", default=os.getcwd(),
                    help="working_dir for /agent/start (default: cwd)")
    ap.add_argument("--session-id", default=None,
                    help="reuse an existing session instead of starting one")
    ap.add_argument("--provider", default=None,
                    help="set the provider (e.g. anthropic) via /agent/update_provider")
    ap.add_argument("--model", default=None, help="model id for --provider")
    ap.add_argument("--insecure", action="store_true",
                    help="https with self-signed cert: skip verification "
                         "(default goosed TLS is on; or launch with GOOSE_TLS=false)")
    args = ap.parse_args(argv)

    secret = os.environ.get(SECRET_ENV)
    if not secret:
        print("error: set %s to the same value goosed was launched with." % SECRET_ENV,
              file=sys.stderr)
        return 2

    try:
        return drive(args.base_url, secret, args.prompt, args.working_dir,
                     args.session_id, args.provider, args.model, args.insecure)
    except urllib.error.HTTPError as e:
        print("HTTP %s from goosed: %s" % (e.code, e.read().decode("utf-8", "replace")[:500]),
              file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print("could not reach goosed at %s: %s\n"
              "(is `goosed agent` running? TLS on by default — try GOOSE_TLS=false "
              "or --insecure.)" % (args.base_url, e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
