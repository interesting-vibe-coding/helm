#!/usr/bin/env python3
"""Offline tests for the engine: format adapters + the turn() coroutine
protocol. No network — _call is stubbed."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402


class TestAdapters(unittest.TestCase):
    def test_oa_messages_roundtrip_shapes(self):
        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "ok"},
                {"type": "tool_use", "id": "t1", "name": "list_sessions",
                 "input": {}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "[]"}]},
        ]
        oa = engine._oa_messages(msgs)
        self.assertEqual(oa[0]["role"], "system")
        self.assertEqual(oa[1], {"role": "user", "content": "hi"})
        self.assertEqual(oa[2]["role"], "assistant")
        self.assertEqual(oa[2]["tool_calls"][0]["function"]["name"],
                         "list_sessions")
        self.assertEqual(oa[3]["role"], "tool")
        self.assertEqual(oa[3]["tool_call_id"], "t1")

    def test_oa_tools_shape(self):
        tools = engine._oa_tools()
        self.assertEqual(len(tools), len(engine.TOOLS))
        for t in tools:
            self.assertEqual(t["type"], "function")
            self.assertIn("parameters", t["function"])

    def test_oa_to_blocks(self):
        resp = {"choices": [{"message": {
            "content": "aye",
            "tool_calls": [{"id": "x", "function": {
                "name": "list_sessions", "arguments": "{}"}}]}}]}
        blocks = engine._oa_to_blocks(resp)
        self.assertEqual(blocks[0], {"type": "text", "text": "aye"})
        self.assertEqual(blocks[1]["type"], "tool_use")
        self.assertEqual(blocks[1]["name"], "list_sessions")

    def test_oa_to_blocks_bad_arguments(self):
        resp = {"choices": [{"message": {"tool_calls": [
            {"id": "x", "function": {"name": "f", "arguments": "not json"}}]}}]}
        self.assertEqual(engine._oa_to_blocks(resp)[0]["input"], {})


class TestTlsDowngradeGuard(unittest.TestCase):
    def _http_error(self, body):
        import io
        import urllib.error
        return urllib.error.HTTPError("https://x", 400, "Bad Request", {},
                                      io.BytesIO(body))

    def test_downgrade_aborts_without_retry(self):
        calls = []
        outer = self

        class FakeOpener:
            def open(self, req, timeout=0):
                calls.append(1)
                raise outer._http_error(
                    b'{"message": "This request was sent over HTTP."}')
        orig = engine.urllib.request.build_opener
        engine.urllib.request.build_opener = lambda *h: FakeOpener()
        try:
            with self.assertRaises(engine.TlsDowngradeError):
                engine._post("https://x", {}, {})
        finally:
            engine.urllib.request.build_opener = orig
        self.assertEqual(len(calls), 1)     # no retry — the key must not re-leak

    def test_downgrade_blocks_oauth_fallback(self):
        eng = engine.Engine.__new__(engine.Engine)
        eng.model, eng.backend = "m", "openrouter"
        eng.messages, eng.transcript, eng._pending = [], [], None

        def boom():
            raise engine.TlsDowngradeError("downgraded")
        eng._call_openrouter = boom
        eng._call_oauth = lambda: self.fail("fallback must not fire")
        with self.assertRaises(engine.TlsDowngradeError):
            eng._call()
        self.assertEqual(eng.backend, "openrouter")  # not flipped


class TestTurnProtocol(unittest.TestCase):
    def _engine_with_script(self, script):
        eng = engine.Engine.__new__(engine.Engine)
        eng.model, eng.backend = "stub", "stub"
        eng.messages, eng.transcript, eng._pending = [], [], None
        it = iter(script)
        eng._call = lambda: next(it)
        return eng

    def test_say_then_end(self):
        eng = self._engine_with_script([[{"type": "text", "text": "two ships on station."}]])
        evs = list(eng.turn("how's the fleet"))
        self.assertEqual(evs, [("say", "two ships on station.")])
        self.assertEqual(eng.transcript[0], ("you", "how's the fleet"))

    def test_act_pauses_until_feed(self):
        eng = self._engine_with_script([
            [{"type": "tool_use", "id": "a", "name": "send_to_worker",
              "input": {"pane_id": 4, "text": "run tests"}}],
            [{"type": "text", "text": "dispatched."}],
        ])
        it = eng.turn("dispatch work")
        ev = next(it)
        self.assertEqual(ev, ("act", "send_to_worker",
                              {"pane_id": 4, "text": "run tests"}))
        eng.feed(True, "sent")
        self.assertEqual(next(it), ("say", "dispatched."))
        acts = [t for t in eng.transcript if t[0] == "act"]
        self.assertEqual(len(acts), 1)
        self.assertTrue(acts[0][1].startswith("✓"))

    def test_denied_act_marks_cross(self):
        eng = self._engine_with_script([
            [{"type": "tool_use", "id": "a", "name": "spawn_worker",
              "input": {"harness": "claude", "cwd": "/tmp"}}],
            [{"type": "text", "text": "ok, standing down."}],
        ])
        it = eng.turn("spawn a ship")
        next(it)
        eng.feed(False, "captain cancelled")
        list(it)
        acts = [t for t in eng.transcript if t[0] == "act"]
        self.assertTrue(acts[0][1].startswith("×"))


if __name__ == "__main__":
    unittest.main()
