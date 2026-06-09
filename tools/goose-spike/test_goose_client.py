#!/usr/bin/env python3
"""Tests for the pure request/response shaping in goose_client.

No server is touched — only the build_* / parse / render helpers. Live
end-to-end verification against a real goosed is a manual step (see README).

    cd tools/goose-spike && python3 -m unittest discover -p 'test_*.py'
"""
import unittest

import goose_client as gc
from sse import iter_events


class BuildTests(unittest.TestCase):
    def test_user_message_shape(self):
        m = gc.build_user_message("hi", created=1718000000)
        self.assertEqual(m["role"], "user")
        self.assertEqual(m["created"], 1718000000)
        self.assertEqual(m["content"], [{"type": "text", "text": "hi"}])
        self.assertEqual(m["metadata"], {"userVisible": True, "agentVisible": True})

    def test_user_message_default_created_is_int(self):
        self.assertIsInstance(gc.build_user_message("x")["created"], int)

    def test_reply_request_is_snake_case(self):
        r = gc.build_reply_request("hello", "sess-1")
        self.assertEqual(set(r), {"user_message", "session_id"})
        self.assertEqual(r["session_id"], "sess-1")
        self.assertEqual(r["user_message"]["content"][0]["text"], "hello")


class ParseRenderTests(unittest.TestCase):
    def test_parse_event_rejects_non_dict_and_junk(self):
        self.assertIsNone(gc.parse_event("not json"))
        self.assertIsNone(gc.parse_event("[1,2,3]"))
        self.assertEqual(gc.parse_event('{"type":"Ping"}'), {"type": "Ping"})

    def test_extract_message_text_joins_text_parts(self):
        msg = {"content": [
            {"type": "text", "text": "Hello "},
            {"type": "toolReq", "id": "x"},      # non-text part is skipped
            {"type": "text", "text": "world"},
        ]}
        self.assertEqual(gc.extract_message_text(msg), "Hello world")

    def test_render_message_event(self):
        ev = {"type": "Message", "message": {"role": "assistant",
              "content": [{"type": "text", "text": "hi there"}]}}
        self.assertEqual(gc.render_event(ev), ("message", "hi there"))

    def test_render_error_and_finish(self):
        self.assertEqual(gc.render_event({"type": "Error", "error": "boom"}),
                         ("error", "boom"))
        self.assertEqual(gc.render_event({"type": "Finish", "reason": "stop"}),
                         ("finish", "stop"))

    def test_render_ping_and_unknown(self):
        self.assertEqual(gc.render_event({"type": "Ping"}), ("ping", ""))
        self.assertEqual(gc.render_event({"type": "ActiveRequests"})[0], "other")

    def test_is_terminal(self):
        self.assertTrue(gc.is_terminal("finish"))
        self.assertTrue(gc.is_terminal("error"))
        self.assertFalse(gc.is_terminal("message"))
        self.assertFalse(gc.is_terminal("ping"))


class StreamIntegrationTests(unittest.TestCase):
    """Wire the SSE parser + goose event rendering together on a fake stream.

    Mirrors goosed's framing: `data: {json}\\n\\n` per event, no `event:` line.
    """
    def test_full_reply_stream_to_text_and_finish(self):
        frames = (
            'data: {"type":"Ping"}\n\n'
            'data: {"type":"Message","message":{"role":"assistant",'
            '"content":[{"type":"text","text":"Hello "}]}}\n\n'
            'data: {"type":"Message","message":{"role":"assistant",'
            '"content":[{"type":"text","text":"world"}]}}\n\n'
            'data: {"type":"Finish","reason":"stop"}\n\n'
        )
        out, kinds = [], []
        for sse in iter_events(frames.split("\n")):
            ev = gc.parse_event(sse.data)
            kind, payload = gc.render_event(ev)
            kinds.append(kind)
            if kind == "message":
                out.append(payload)
            if gc.is_terminal(kind):
                break
        self.assertEqual("".join(out), "Hello world")
        self.assertEqual(kinds, ["ping", "message", "message", "finish"])

    def test_error_event_is_terminal(self):
        frames = 'data: {"type":"Error","error":"no provider configured"}\n\n'
        kinds = []
        for sse in iter_events(frames.split("\n")):
            kind, _ = gc.render_event(gc.parse_event(sse.data))
            kinds.append(kind)
            if gc.is_terminal(kind):
                break
        self.assertEqual(kinds, ["error"])


if __name__ == "__main__":
    unittest.main()
