#!/usr/bin/env python3
"""kaji engine — the First Mate as our own code, not a borrowed shell.

A minimal tool-use loop over /v1/messages (Claude Code OAuth token, same
auth as the planner): the captain types at the helm line, the engine
converses, observes the fleet through read-only tools it runs itself, and
YIELDS spawn/send actions to the caller — the cockpit owns the confirm
gate (or auto mode). No SDK, no harness, stdlib only.

Contract with the cockpit:
    eng = Engine()
    for ev in eng.turn("开个 codex 去 wu 修路由"):
        ev = ("say", text)            render assistant prose
           | ("act", tool, args)      DANGEROUS action → caller confirms,
                                      then calls eng.feed(ok, result_str)
                                      (or eng.feed(False, reason) on deny)
    eng.transcript                    [(role, text), ...] for rendering

The generator pauses on ("act", …) until feed() is called — a hand-rolled
coroutine so the TUI stays in charge of the screen at all times.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "helm-quota"))

# Two transports, free-first:
#   openrouter — free models (:free), costs nothing, default when key present
#   oauth      — Claude Code OAuth /v1/messages; haiku only (sonnet 429s hard)
# Both go through the system proxy — direct connections are not sanctioned.
# Researched 2026-06: best free dispatcher on OpenRouter — strong Chinese,
# reliable tool use, 262K ctx, MoE so latency is low. ~200 req/day per model
# on the free pool (1000/day account-wide with $10 topped up) — plenty.
OR_MODEL = os.environ.get("KAJI_ENGINE_OR_MODEL",
                          "qwen/qwen3-next-80b-a3b-instruct:free")
MODEL = os.environ.get("KAJI_ENGINE_MODEL", "claude-haiku-4-5-20251001")
MAX_STEPS = 8           # tool round-trips per captain turn — dispatcher, not a coder

SYSTEM = """You are the Kaji First Mate — the fleet dispatcher, not a coder.
The captain gives one-line orders; you observe the fleet (tools), break the
order into minimal actions, and dispatch them to workers.
Rules:
- Reply in terse English, plain text only — no markdown, tables, or emoji.
  The captain may write in any language; you still answer in English.
- Look before you act: list_sessions when unsure.
- send_to_worker text must be an imperative instruction to that worker.
- spawn only when no suitable session exists; project name → ~/workspace/<name>.
- Small talk / anything off-fleet → decline in one line.
- At most 2 actions per turn; close with a one-line summary."""

TOOLS = [
    {"name": "list_sessions",
     "description": "All live worker sessions (pane_id/harness/project/state/ctx).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "fleet_timeline",
     "description": "Fleet event history (spawn/dispatch/state). Optional pane filter.",
     "input_schema": {"type": "object",
                      "properties": {"pane": {"type": "integer"}}}},
    {"name": "spawn_worker",
     "description": "Open a new worker. harness ∈ claude|codex. cwd must be absolute.",
     "input_schema": {"type": "object",
                      "properties": {"harness": {"type": "string"},
                                     "cwd": {"type": "string"},
                                     "task": {"type": "string"}},
                      "required": ["harness", "cwd"]}},
    {"name": "send_to_worker",
     "description": "Inject one instruction (text + Enter) into an existing worker.",
     "input_schema": {"type": "object",
                      "properties": {"pane_id": {"type": "integer"},
                                     "text": {"type": "string"}},
                      "required": ["pane_id", "text"]}},
]
DANGEROUS = {"spawn_worker", "send_to_worker"}


def _token():
    try:
        import quota
        return quota._claude_oauth_token()
    except Exception:
        return None


def _or_key():
    """OpenRouter key: env first, else the fish config it is exported from."""
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    try:
        cfg = os.path.expanduser("~/.config/fish/config.fish")
        with open(cfg) as f:
            for ln in f:
                if "OPENROUTER_API_KEY" in ln:
                    return ln.split()[-1].strip("'\"")
    except Exception:
        pass
    return None


# ── OpenAI-format adapters (OpenRouter speaks chat/completions) ──────────────

def _oa_messages(messages):
    """Anthropic-block history → OpenAI chat messages."""
    out = [{"role": "system", "content": SYSTEM}]
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            out.append({"role": m["role"], "content": c})
            continue
        if m["role"] == "assistant":
            text, calls = [], []
            for b in c:
                if b.get("type") == "text":
                    text.append(b.get("text", ""))
                elif b.get("type") == "tool_use":
                    calls.append({"id": b["id"], "type": "function",
                                  "function": {"name": b["name"],
                                               "arguments": json.dumps(b.get("input") or {})}})
            msg = {"role": "assistant", "content": "\n".join(text) or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
        else:                                   # user turn carrying tool results
            for b in c:
                if b.get("type") == "tool_result":
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"],
                                "content": str(b.get("content", ""))})
    return out


def _oa_tools():
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["description"],
                          "parameters": t["input_schema"]}} for t in TOOLS]


def _oa_to_blocks(resp):
    """OpenAI chat response → Anthropic-style content blocks."""
    msg = (resp.get("choices") or [{}])[0].get("message") or {}
    blocks = []
    if msg.get("content"):
        blocks.append({"type": "text", "text": msg["content"]})
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except Exception:
            args = {}
        blocks.append({"type": "tool_use", "id": tc.get("id") or "tc",
                       "name": fn.get("name"), "input": args})
    return blocks


def _hb():
    cand = os.path.join(HERE, "..", "kaji-brain", "kaji-brain")
    return cand if os.path.exists(cand) else "kaji-brain"


def _run_tool(name, args):
    """Execute a READ-ONLY tool via the kaji-brain CLI. Returns a string."""
    try:
        if name == "list_sessions":
            out = subprocess.run([_hb(), "sessions"], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, timeout=20).stdout
            return out.decode("utf-8", "replace").strip() or "[]"
        if name == "fleet_timeline":
            argv = [_hb(), "timeline", "--json"]
            if args.get("pane") is not None:
                argv += ["--pane", str(args["pane"])]
            out = subprocess.run(argv, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, timeout=20).stdout
            lines = out.decode("utf-8", "replace").strip().splitlines()
            return "\n".join(lines[-15:]) or "[]"
    except Exception as e:  # noqa: BLE001
        return "tool error: %s" % e
    return "unknown tool"


def execute_action(name, args):
    """Execute a CONFIRMED dangerous action. Returns (ok, result_str)."""
    try:
        if name == "spawn_worker":
            argv = [_hb(), "spawn", args.get("harness", "claude"),
                    args.get("cwd", "")]
            if args.get("task"):
                argv.append(args["task"])
            p = subprocess.run(argv, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=60)
            return p.returncode == 0, p.stdout.decode("utf-8", "replace").strip()
        if name == "send_to_worker":
            p = subprocess.run([_hb(), "send", str(args.get("pane_id")),
                                args.get("text", "")],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=30)
            return p.returncode == 0, p.stdout.decode("utf-8", "replace").strip() or "sent"
    except Exception as e:  # noqa: BLE001
        return False, str(e)
    return False, "unknown action"


def _post(url, payload, headers, attempts=4, max_429_wait=60.0):
    """POST JSON, ALWAYS through the system proxy (user rule: direct
    connections are not viable on this network — proxy is the only
    sanctioned path). Flakes are retried on the same path, never bypassed."""
    import time as _t
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=headers)
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if attempt == attempts - 1:
                try:
                    body = e.read().decode("utf-8", "replace")[:300]
                except Exception:
                    body = ""
                raise RuntimeError("HTTP %d: %s" % (e.code, body or e.reason))
            if e.code == 429:
                ra = e.headers.get("retry-after")
                _t.sleep(min(float(ra) if ra else 10.0 * (attempt + 1),
                             max_429_wait))
            elif e.code == 400 or e.code >= 500:
                # Clash sometimes hands back junk 400/5xx — same-path retry
                _t.sleep(3.0 * (attempt + 1))
            else:
                raise
        except (urllib.error.URLError, ConnectionError, OSError):
            # proxy hiccup (SSL EOF / RemoteDisconnected) — brief backoff, retry
            if attempt == attempts - 1:
                raise
            _t.sleep(2.5 * (attempt + 1))
    raise RuntimeError("unreachable")


class Engine:
    def __init__(self, model=MODEL):
        self.model = model
        self.messages = []          # full API history (Anthropic content blocks)
        self.transcript = []        # [(who, text)] for the TUI: you / 舵 / act
        self._pending = None        # set by feed()
        # free-first: OpenRouter when a key exists, else Claude OAuth haiku
        self.backend = os.environ.get("KAJI_ENGINE_BACKEND") or \
            ("openrouter" if _or_key() else "oauth")

    def feed(self, ok, result):
        """Resolve the action the generator is paused on."""
        self._pending = (ok, result)

    def _call(self):
        """One model call → Anthropic-style content blocks (both backends)."""
        if self.backend == "openrouter":
            try:
                return self._call_openrouter()
            except Exception:
                if not _token():
                    raise
                self.backend = "oauth"   # sticky fallback for this session
        return self._call_oauth()

    def _call_openrouter(self):
        resp = _post(
            "https://openrouter.ai/api/v1/chat/completions",
            {"model": OR_MODEL, "max_tokens": 1200,
             "messages": _oa_messages(self.messages), "tools": _oa_tools()},
            {"Authorization": "Bearer %s" % _or_key(),
             "Content-Type": "application/json",
             "HTTP-Referer": "https://kaji.doabit.dev",
             "X-Title": "kaji"},
            attempts=4, max_429_wait=8.0)   # proxy junk windows outlast 1 retry
        if resp.get("error"):               # OpenRouter tucks errors in 200s too
            raise RuntimeError(resp["error"].get("message", "openrouter error"))
        return _oa_to_blocks(resp)

    def _call_oauth(self):
        tok = _token()
        if not tok:
            raise RuntimeError("no Claude Code OAuth token (run `claude` once)")
        resp = _post(
            "https://api.anthropic.com/v1/messages",
            {"model": self.model, "max_tokens": 1200, "system": SYSTEM,
             "tools": TOOLS, "messages": self.messages},
            {"Authorization": "Bearer %s" % tok,
             "anthropic-beta": "oauth-2025-04-20",
             "anthropic-version": "2023-06-01",
             "Content-Type": "application/json",
             "User-Agent": "claude-code/2.1.90"})
        return resp.get("content") or []

    def turn(self, user_text):
        """One captain turn. Yields ('say', text) / ('act', tool, args);
        after an 'act' the caller MUST feed() before resuming iteration."""
        self.transcript.append(("you", user_text))
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(MAX_STEPS):
            try:
                blocks = self._call()
            except Exception as e:  # noqa: BLE001
                msg = "engine error: %s" % e
                self.transcript.append(("舵", msg))
                yield ("say", msg)
                return
            self.messages.append({"role": "assistant", "content": blocks})
            results = []
            for b in blocks:
                if b.get("type") == "text" and b.get("text", "").strip():
                    self.transcript.append(("舵", b["text"].strip()))
                    yield ("say", b["text"].strip())
                elif b.get("type") == "tool_use":
                    name, args = b.get("name"), b.get("input") or {}
                    if name in DANGEROUS:
                        self._pending = None
                        yield ("act", name, args)
                        ok, result = self._pending or (False, "denied")
                        tag = "✓" if ok else "×"
                        self.transcript.append(
                            ("act", "%s %s %s" % (tag, name, _brief(name, args))))
                        results.append(_tool_result(b["id"], result, not ok))
                    else:
                        results.append(_tool_result(b["id"], _run_tool(name, args)))
            if not results:
                return                      # end_turn — nothing left to do
            self.messages.append({"role": "user", "content": results})
        self.transcript.append(("舵", "(step limit reached — stopping here.)"))
        yield ("say", "(step limit reached — stopping here.)")


def _tool_result(tool_id, content, is_error=False):
    out = {"type": "tool_result", "tool_use_id": tool_id,
           "content": str(content)[:4000]}
    if is_error:
        out["is_error"] = True
    return out


def _brief(name, args):
    if name == "spawn_worker":
        return "%s · %s" % (args.get("harness"), args.get("cwd", ""))
    return "→ pane %s" % args.get("pane_id")


if __name__ == "__main__":
    # smoke: python3 engine.py "有哪些 session?" — DRY-RUN: dangerous actions
    # are printed, not executed (pass --live to really run them).
    live = "--live" in sys.argv
    eng = Engine()
    for word in [a for a in sys.argv[1:] if a != "--live"] or ["列一下现在的舰队"]:
        it = eng.turn(word)
        for ev in it:
            if ev[0] == "say":
                print("舵:", ev[1])
            else:
                _, name, args = ev
                print("act:", name, json.dumps(args, ensure_ascii=False))
                if live:
                    ok, res = execute_action(name, args)
                else:
                    ok, res = True, "(dry-run: pretended to execute)"
                eng.feed(ok, res)
        print("--- transcript ---")
        for who, t in eng.transcript:
            print(" %s | %s" % (who, t[:100]))
