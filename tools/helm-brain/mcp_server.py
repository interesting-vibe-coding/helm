#!/usr/bin/env python3
"""helm-brain MCP server — the Brain dispatcher's constrained instrument layer.

Exposes `helm-brain` (sessions / timeline / spawn / send / notify) as MCP tools
over stdio, so the lightweight **dispatcher** (a cheap-model harness — Crush /
Goose / any MCP client) can fan one natural-language instruction out into
worker sessions while staying *scoped to these tools* — it can dispatch but not
wander. Harness-agnostic: switching the dispatcher harness never touches this
layer. See docs/BRAIN_DESIGN.md § "The dispatcher".

Design:
- **Thin adapter.** It shells out to the already-tested `helm-brain` CLI (the
  JSON contract), rather than re-implementing session logic. A `HelmBrain`
  object isolates that I/O so the protocol layer is unit-tested with a fake.
- **Hand-rolled minimal MCP.** stdio transport = newline-delimited JSON-RPC 2.0.
  Implements `initialize`, `tools/list`, `tools/call`, `ping`, and ignores
  notifications. Zero third-party deps (matches the other bundled tools).
- **Trust gate.** `spawn_worker` / `send_to_worker` are annotated as non-read-
  only / destructive so the client (cockpit / harness) keeps a confirm gate in
  front of them. This server does not itself prompt — it is the hands, not the
  gate.

⚠️ The JSON-RPC dispatch + tool routing are unit-tested; the live handshake
against a real MCP client must be verified on macOS with a running Kaji.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional

# Default protocol version we advertise if the client doesn't send one. We echo
# the client's requested version when present (the recommended behavior).
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "helm-brain", "version": "0.1.0"}

HARNESSES = ["kiro", "claude", "opencode", "codex"]


# ── helm-brain CLI adapter (the only I/O) ─────────────────────────────────────

class HelmBrain:
    """Locates and shells out to the `helm-brain` CLI. Never raises."""

    def __init__(self, argv: Optional[List[str]] = None):
        self._argv = argv if argv is not None else self._locate()

    @staticmethod
    def _locate() -> Optional[List[str]]:
        here = os.path.dirname(os.path.abspath(__file__))
        local = os.path.join(here, "helm-brain")
        if os.path.exists(local):
            return [local]
        found = shutil.which("helm-brain")
        return [found] if found else None

    def _run(self, args: List[str], timeout: int = 15) -> (int, str, str):
        if not self._argv:
            return 1, "", "helm-brain CLI not found"
        try:
            p = subprocess.run(self._argv + args, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=timeout)
            return (p.returncode, p.stdout.decode("utf-8", "replace"),
                    p.stderr.decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001 - robustness
            return 1, "", str(e)

    def sessions(self) -> str:
        _, out, _ = self._run(["sessions"])
        return out.strip() or "[]"

    def timeline(self, pane: Optional[int] = None) -> str:
        args = ["timeline", "--json"]
        if pane is not None:
            args += ["--pane", str(pane)]
        _, out, _ = self._run(args)
        return out.strip() or "[]"

    def spawn(self, harness: str, cwd: str, task: str = "") -> (bool, str):
        args = ["spawn", harness, cwd] + ([task] if task else [])
        rc, out, err = self._run(args, timeout=30)
        return rc == 0, (out.strip() or err.strip())

    def send(self, pane_id: int, text: str) -> (bool, str):
        rc, out, err = self._run(["send", str(pane_id), text])
        return rc == 0, (err.strip() or out.strip() or "sent")

    def notify(self, title: str, message: str) -> (bool, str):
        rc, _, err = self._run(["notify", title, message])
        return rc == 0, (err.strip() or "notified")


# ── tool catalogue ────────────────────────────────────────────────────────────

def _tool(name, description, properties, required, *, read_only):
    return {
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "properties": properties,
                        "required": required},
        "annotations": {"title": name, "readOnlyHint": read_only,
                        "destructiveHint": not read_only},
    }


TOOLS = [
    _tool("list_sessions",
          "List the live worker sessions (pane_id, harness, project, state, "
          "runtime_secs, tokens_today) as JSON. Read this first to see the fleet.",
          {}, [], read_only=True),
    _tool("fleet_timeline",
          "The append-only history of fleet events (spawn/dispatch/state) as "
          "JSON, oldest first. Optionally filter to one pane.",
          {"pane": {"type": "integer", "description": "restrict to this pane id"}},
          [], read_only=True),
    _tool("spawn_worker",
          "Create a NEW worker session: open a pane running <harness> in <cwd>, "
          "optionally sending an initial task. Use to fan work out by project. "
          "Destructive — should be confirm-gated by the caller.",
          {"harness": {"type": "string", "enum": HARNESSES},
           "cwd": {"type": "string", "description": "absolute working directory"},
           "task": {"type": "string", "description": "optional initial instruction"}},
          ["harness", "cwd"], read_only=False),
    _tool("send_to_worker",
          "Send an instruction (text + Enter) to an existing worker pane. "
          "Destructive — should be confirm-gated by the caller.",
          {"pane_id": {"type": "integer"},
           "text": {"type": "string", "description": "the instruction to dispatch"}},
          ["pane_id", "text"], read_only=False),
    _tool("notify",
          "Pop a macOS notification (e.g. to flag a worker that needs the user).",
          {"title": {"type": "string"}, "message": {"type": "string"}},
          ["title", "message"], read_only=False),
]
_TOOL_NAMES = {t["name"] for t in TOOLS}


# ── tool dispatch ─────────────────────────────────────────────────────────────

def call_tool(name: str, args: Dict[str, Any], hb: HelmBrain) -> Dict[str, Any]:
    """Run a tool; return an MCP tools/call result ({content, isError})."""
    def ok(text):
        return {"content": [{"type": "text", "text": text}], "isError": False}

    def fail(text):
        return {"content": [{"type": "text", "text": text}], "isError": True}

    args = args or {}
    if name == "list_sessions":
        return ok(hb.sessions())
    if name == "fleet_timeline":
        pane = args.get("pane")
        try:
            pane = int(pane) if pane is not None else None
        except (TypeError, ValueError):
            return fail("pane must be an integer")
        return ok(hb.timeline(pane))
    if name == "spawn_worker":
        harness, cwd = args.get("harness"), args.get("cwd")
        if not harness or not cwd:
            return fail("spawn_worker requires 'harness' and 'cwd'")
        good, detail = hb.spawn(harness, cwd, args.get("task", "") or "")
        return ok(detail) if good else fail(detail)
    if name == "send_to_worker":
        pane_id, text = args.get("pane_id"), args.get("text")
        if pane_id is None or text is None:
            return fail("send_to_worker requires 'pane_id' and 'text'")
        good, detail = hb.send(pane_id, text)
        return ok(detail) if good else fail(detail)
    if name == "notify":
        good, detail = hb.notify(args.get("title", ""), args.get("message", ""))
        return ok(detail) if good else fail(detail)
    return fail("unknown tool: %s" % name)


# ── JSON-RPC / MCP handling ───────────────────────────────────────────────────

def _result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_request(req: Dict[str, Any], hb: HelmBrain) -> Optional[Dict[str, Any]]:
    """Map one JSON-RPC request to a response. None for notifications/no-reply.

    Pure except for the injected `hb` — unit-tested with a fake HelmBrain.
    """
    if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
        return _error(None, -32600, "Invalid Request")

    method = req.get("method")
    req_id = req.get("id")
    is_notification = "id" not in req
    params = req.get("params") or {}

    if method == "initialize":
        version = params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION
        return _result(req_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })

    if method in ("notifications/initialized", "initialized"):
        return None  # notification: no response

    if method == "ping":
        return _result(req_id, {})

    if method == "tools/list":
        return _result(req_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        if name not in _TOOL_NAMES:
            return _error(req_id, -32602, "Unknown tool: %s" % name)
        return _result(req_id, call_tool(name, params.get("arguments") or {}, hb))

    if is_notification:
        return None  # ignore unknown notifications
    return _error(req_id, -32601, "Method not found: %s" % method)


def serve(stdin, stdout, hb: Optional[HelmBrain] = None) -> int:
    """Read newline-delimited JSON-RPC from stdin, write responses to stdout."""
    hb = hb or HelmBrain()
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            _write(stdout, _error(None, -32700, "Parse error"))
            continue
        resp = handle_request(req, hb)
        if resp is not None:
            _write(stdout, resp)
    return 0


def _write(stdout, obj):
    stdout.write(json.dumps(obj) + "\n")
    stdout.flush()


def main(argv: List[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        sys.stdout.write(__doc__ or "")
        return 0
    return serve(sys.stdin, sys.stdout)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
