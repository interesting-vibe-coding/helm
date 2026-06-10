#!/usr/bin/env python3
"""Tests for the helm-brain MCP server's JSON-RPC + tool dispatch.

The live handshake against a real MCP client is a separate macOS step; here we
pin the protocol logic with a fake HelmBrain (no subprocess, no Kaji).

    cd tools/helm-brain && python3 -m unittest discover -p 'test_*.py'
"""
import io
import json
import unittest

import mcp_server as m


class FakeHelmBrain:
    def __init__(self):
        self.calls = []

    def sessions(self):
        return '[{"pane_id":2,"harness":"claude","project":"kaji","state":"waiting"}]'

    def timeline(self, pane=None):
        self.calls.append(("timeline", pane))
        return '[{"ts":1,"pane":2,"ev":"spawn"}]'

    def spawn(self, harness, cwd, task=""):
        self.calls.append(("spawn", harness, cwd, task))
        return True, '{"pane_id": 7}'

    def send(self, pane_id, text):
        self.calls.append(("send", pane_id, text))
        return True, "sent"

    def notify(self, title, message):
        self.calls.append(("notify", title, message))
        return True, "notified"


class InitializeTests(unittest.TestCase):
    def test_initialize_echoes_protocol_version(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-03-26"}}
        resp = m.handle_request(req, FakeHelmBrain())
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["protocolVersion"], "2025-03-26")
        self.assertIn("tools", resp["result"]["capabilities"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "helm-brain")

    def test_initialize_defaults_protocol_version(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = m.handle_request(req, FakeHelmBrain())
        self.assertEqual(resp["result"]["protocolVersion"], m.DEFAULT_PROTOCOL_VERSION)

    def test_initialized_notification_no_response(self):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self.assertIsNone(m.handle_request(req, FakeHelmBrain()))


class ToolsListTests(unittest.TestCase):
    def test_tools_list_shape(self):
        resp = m.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, FakeHelmBrain())
        tools = resp["result"]["tools"]
        names = {t["name"] for t in tools}
        self.assertEqual(names, {"list_sessions", "fleet_timeline",
                                 "spawn_worker", "send_to_worker", "notify"})
        for t in tools:
            self.assertIn("inputSchema", t)
            self.assertEqual(t["inputSchema"]["type"], "object")

    def test_write_tools_are_marked_destructive(self):
        resp = m.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, FakeHelmBrain())
        by_name = {t["name"]: t for t in resp["result"]["tools"]}
        self.assertTrue(by_name["spawn_worker"]["annotations"]["destructiveHint"])
        self.assertTrue(by_name["send_to_worker"]["annotations"]["destructiveHint"])
        self.assertTrue(by_name["list_sessions"]["annotations"]["readOnlyHint"])


class ToolCallTests(unittest.TestCase):
    def _call(self, name, args, hb):
        req = {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
               "params": {"name": name, "arguments": args}}
        return m.handle_request(req, hb)

    def test_list_sessions(self):
        resp = self._call("list_sessions", {}, FakeHelmBrain())
        self.assertFalse(resp["result"]["isError"])
        self.assertIn("waiting", resp["result"]["content"][0]["text"])

    def test_spawn_worker_passes_args(self):
        hb = FakeHelmBrain()
        resp = self._call("spawn_worker",
                          {"harness": "claude", "cwd": "/x", "task": "fix #1"}, hb)
        self.assertFalse(resp["result"]["isError"])
        self.assertIn(("spawn", "claude", "/x", "fix #1"), hb.calls)

    def test_spawn_worker_missing_args_is_error(self):
        resp = self._call("spawn_worker", {"harness": "claude"}, FakeHelmBrain())
        self.assertTrue(resp["result"]["isError"])

    def test_send_to_worker(self):
        hb = FakeHelmBrain()
        resp = self._call("send_to_worker", {"pane_id": 3, "text": "go"}, hb)
        self.assertFalse(resp["result"]["isError"])
        self.assertIn(("send", 3, "go"), hb.calls)

    def test_fleet_timeline_pane_filter(self):
        hb = FakeHelmBrain()
        self._call("fleet_timeline", {"pane": 5}, hb)
        self.assertIn(("timeline", 5), hb.calls)

    def test_fleet_timeline_bad_pane_is_error(self):
        resp = self._call("fleet_timeline", {"pane": "nope"}, FakeHelmBrain())
        self.assertTrue(resp["result"]["isError"])

    def test_unknown_tool_is_jsonrpc_error(self):
        resp = self._call("frobnicate", {}, FakeHelmBrain())
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)


class ProtocolErrorTests(unittest.TestCase):
    def test_unknown_method(self):
        resp = m.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "bogus"}, FakeHelmBrain())
        self.assertEqual(resp["error"]["code"], -32601)

    def test_invalid_request_object(self):
        resp = m.handle_request({"method": "initialize"}, FakeHelmBrain())
        self.assertEqual(resp["error"]["code"], -32600)

    def test_unknown_notification_ignored(self):
        self.assertIsNone(m.handle_request(
            {"jsonrpc": "2.0", "method": "notifications/cancelled"}, FakeHelmBrain()))


class ServeLoopTests(unittest.TestCase):
    def test_serve_reads_lines_and_writes_responses(self):
        stdin = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
            + "not json\n"
        )
        stdout = io.StringIO()
        m.serve(stdin, stdout, FakeHelmBrain())
        lines = [json.loads(x) for x in stdout.getvalue().splitlines()]
        # initialize result, tools/list result, parse error — the notification
        # produces no line.
        self.assertEqual(lines[0]["id"], 1)
        self.assertEqual(lines[1]["id"], 2)
        self.assertEqual(lines[2]["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
