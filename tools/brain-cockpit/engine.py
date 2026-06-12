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

# haiku: the OAuth /v1/messages path rate-limits sonnet hard (Max plan keeps
# the big models for the CC client itself); haiku is fast and generous.
MODEL = os.environ.get("KAJI_ENGINE_MODEL", "claude-haiku-4-5-20251001")
MAX_STEPS = 8           # tool round-trips per captain turn — dispatcher, not a coder

SYSTEM = """你是 Kaji 的大副（First Mate）——舰队调度员，不是码农。
船长用一句话下令；你观察舰队（工具）、拆解成最小动作、派发给 worker。
规则:
- 回复极简中文（终端环境）。纯文本，禁 markdown/表格/emoji。无废话，不复述命令。
- 先看舰队再动手: 不确定时 list_sessions。
- send_to_worker 的 text 必须是对那个 worker 的祈使句指令。
- spawn 只在没有合适 session 时; 项目名 → ~/workspace/<名> 路径。
- 闲聊/天气/与舰队无关 → 一句话拒绝。
- 一次回合最多派 2 个动作; 派完用一行总结收尾。"""

TOOLS = [
    {"name": "list_sessions",
     "description": "当前所有 worker session（pane_id/harness/project/state/ctx）。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "fleet_timeline",
     "description": "舰队事件史（spawn/dispatch/state）。可选 pane 过滤。",
     "input_schema": {"type": "object",
                      "properties": {"pane": {"type": "integer"}}}},
    {"name": "spawn_worker",
     "description": "开新 worker。harness ∈ claude|codex。cwd 必须是绝对路径。",
     "input_schema": {"type": "object",
                      "properties": {"harness": {"type": "string"},
                                     "cwd": {"type": "string"},
                                     "task": {"type": "string"}},
                      "required": ["harness", "cwd"]}},
    {"name": "send_to_worker",
     "description": "向已有 worker 注入一条指令（text + 回车）。",
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


class Engine:
    def __init__(self, model=MODEL):
        self.model = model
        self.messages = []          # full API history (content blocks)
        self.transcript = []        # [(who, text)] for the TUI: you / 舵 / act
        self._pending = None        # set by feed()

    def feed(self, ok, result):
        """Resolve the action the generator is paused on."""
        self._pending = (ok, result)

    def _call(self):
        tok = _token()
        if not tok:
            raise RuntimeError("no Claude Code OAuth token (run `claude` once)")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": self.model, "max_tokens": 1200, "system": SYSTEM,
                "tools": TOOLS, "messages": self.messages,
            }).encode(),
            headers={"Authorization": "Bearer %s" % tok,
                     "anthropic-beta": "oauth-2025-04-20",
                     "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json",
                     "User-Agent": "claude-code/2.1.90"})
        import time as _t
        # ALWAYS through the system proxy (user rule: direct connections are
        # not viable on this network — proxy is the only sanctioned path).
        # Flakes are retried, never bypassed.
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if attempt == 3:
                    raise
                if e.code == 429:
                    ra = e.headers.get("retry-after")
                    # OAuth /v1/messages burst-limits hard; recovers in ~60s.
                    _t.sleep(min(float(ra) if ra else 20.0 * (attempt + 1), 60))
                elif e.code == 400 or e.code >= 500:
                    # Clash sometimes hands back junk 400/5xx — same-path retry
                    _t.sleep(2.0 * (attempt + 1))
                else:
                    raise
            except urllib.error.URLError:
                # proxy hiccup (Clash SSL EOF etc.) — brief backoff, retry
                if attempt == 3:
                    raise
                _t.sleep(1.5 * (attempt + 1))
        raise RuntimeError("unreachable")

    def turn(self, user_text):
        """One captain turn. Yields ('say', text) / ('act', tool, args);
        after an 'act' the caller MUST feed() before resuming iteration."""
        self.transcript.append(("you", user_text))
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(MAX_STEPS):
            try:
                resp = self._call()
            except Exception as e:  # noqa: BLE001
                msg = "engine error: %s" % e
                self.transcript.append(("舵", msg))
                yield ("say", msg)
                return
            blocks = resp.get("content") or []
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
        self.transcript.append(("舵", "(回合步数到顶，先到这。)"))
        yield ("say", "(回合步数到顶，先到这。)")


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
    # smoke: python3 engine.py "有哪些 session?" — auto-approves actions.
    eng = Engine()
    for word in sys.argv[1:] or ["列一下现在的舰队"]:
        it = eng.turn(word)
        for ev in it:
            if ev[0] == "say":
                print("舵:", ev[1])
            else:
                _, name, args = ev
                print("act:", name, json.dumps(args, ensure_ascii=False))
                ok, res = execute_action(name, args)
                eng.feed(ok, res)
        print("--- transcript ---")
        for who, t in eng.transcript:
            print(" %s | %s" % (who, t[:100]))
