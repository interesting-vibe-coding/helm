#!/usr/bin/env python3
"""Tests for kaji-brain serve (the fleet HTTP API).

Cloud-buildable: spins the real ThreadingHTTPServer on 127.0.0.1:0, monkeypatches
brain.py's data layer so no running Kaji / mux is needed, and drives it with
urllib. Covers routing, JSON shape, auth gating, the non-loopback-needs-token
guard, and SSE framing.
"""

import json
import os
import sys
import time
import unittest
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain      # noqa: E402
import serve      # noqa: E402


def _start(token=None):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler(token))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    port = httpd.server_address[1]
    return httpd, "http://127.0.0.1:%d" % port


def _get(base, path, token=None):
    req = urllib.request.Request(base + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=3) as r:
        return r.status, r.read().decode("utf-8")


def _post(base, path, obj, token=None):
    data = json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=3) as r:
        return r.status, r.read().decode("utf-8")


class TestServeReads(unittest.TestCase):
    def setUp(self):
        self._orig = (brain.collect_sessions, brain.load_quota,
                      brain.load_limits, brain.read_events)
        brain.collect_sessions = lambda: [
            {"pane_id": 2, "harness": "claude", "project": "kaji",
             "state": "waiting", "runtime_secs": 30, "tokens_today": 1234},
        ]
        brain.load_quota = lambda: {"claude": 1234}
        brain.load_limits = lambda: {
            "codex": {"secondary_used_percent": 38.0, "plan": "plus"}}
        brain.read_events = lambda: [
            {"ts": 1, "ev": "spawn", "pane": 2, "harness": "claude"},
            {"ts": 2, "ev": "state", "pane": 2, "to": "waiting"},
            {"ts": 3, "ev": "dispatch", "pane": 5, "text": "go"},
        ]
        self.httpd, self.base = _start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()
        (brain.collect_sessions, brain.load_quota,
         brain.load_limits, brain.read_events) = self._orig

    def test_healthz_no_auth(self):
        code, body = _get(self.base, "/healthz")
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_sessions(self):
        code, body = _get(self.base, "/api/sessions")
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data[0]["harness"], "claude")
        self.assertEqual(data[0]["tokens_today"], 1234)

    def test_state_one_glance(self):
        code, body = _get(self.base, "/api/state")
        d = json.loads(body)
        self.assertIn("sessions", d)
        self.assertIn("quota", d)
        self.assertIn("ts", d)
        self.assertEqual(d["quota"]["claude"], 1234)
        self.assertEqual(d["limits"]["codex"]["secondary_used_percent"], 38.0)

    def test_quota(self):
        _, body = _get(self.base, "/api/quota")
        self.assertEqual(json.loads(body)["claude"], 1234)

    def test_timeline_all(self):
        _, body = _get(self.base, "/api/timeline")
        self.assertEqual(len(json.loads(body)), 3)

    def test_timeline_pane_filter(self):
        _, body = _get(self.base, "/api/timeline?pane=2")
        data = json.loads(body)
        self.assertEqual(len(data), 2)
        self.assertTrue(all(e["pane"] == 2 for e in data))

    def test_404(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.base, "/api/nope")
        self.assertEqual(cm.exception.code, 404)


class TestServeAuth(unittest.TestCase):
    def setUp(self):
        self.httpd, self.base = _start(token="sekret")

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_healthz_open_even_with_token(self):
        code, _ = _get(self.base, "/healthz")
        self.assertEqual(code, 200)

    def test_api_requires_token(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.base, "/api/sessions")
        self.assertEqual(cm.exception.code, 401)

    def test_api_with_token_ok(self):
        brain.collect_sessions = lambda: []
        code, _ = _get(self.base, "/api/sessions", token="sekret")
        self.assertEqual(code, 200)

    def test_mobile_page_open_even_with_token(self):
        for path in ("/", "/mobile"):
            code, body = _get(self.base, path)
            self.assertEqual(code, 200)
            self.assertIn("<!DOCTYPE html>", body)
            self.assertIn("Kaji", body)


class TestServeWrites(unittest.TestCase):
    def setUp(self):
        self._send = serve._send_via_cli
        self._spawn = serve._spawn_via_cli
        self.httpd, self.base = _start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()
        serve._send_via_cli = self._send
        serve._spawn_via_cli = self._spawn

    def test_send_requires_fields(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _post(self.base, "/api/send", {"pane_id": 2})
        self.assertEqual(cm.exception.code, 400)

    def test_send_ok(self):
        serve._send_via_cli = lambda pane_id, text: (0, "")
        code, body = _post(self.base, "/api/send", {"pane_id": 2, "text": "hi"})
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_spawn_requires_fields(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _post(self.base, "/api/spawn", {"harness": "claude"})
        self.assertEqual(cm.exception.code, 400)

    def test_spawn_ok(self):
        serve._spawn_via_cli = lambda h, c, t: (0, {"pane_id": 7})
        code, body = _post(self.base, "/api/spawn",
                           {"harness": "claude", "cwd": "/tmp", "task": "x"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["pane_id"], 7)


class TestServePeek(unittest.TestCase):
    def setUp(self):
        self._peek = brain.peek_pane
        self.httpd, self.base = _start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()
        brain.peek_pane = self._peek

    def test_peek_ok(self):
        brain.peek_pane = lambda pane, lines=80: (0, "line1\nline2", "")
        code, body = _get(self.base, "/api/peek?pane=4&lines=20")
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertEqual(d["pane"], 4)
        self.assertEqual(d["lines"], 20)
        self.assertEqual(d["text"], "line1\nline2")

    def test_peek_default_lines(self):
        brain.peek_pane = lambda pane, lines=80: (0, "x", "")
        _, body = _get(self.base, "/api/peek?pane=4")
        self.assertEqual(json.loads(body)["lines"], 80)

    def test_peek_requires_pane(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.base, "/api/peek")
        self.assertEqual(cm.exception.code, 400)

    def test_peek_bad_pane(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.base, "/api/peek?pane=nope")
        self.assertEqual(cm.exception.code, 400)

    def test_peek_cli_error(self):
        brain.peek_pane = lambda pane, lines=80: (1, "", "pane 99 gone")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.base, "/api/peek?pane=99")
        self.assertEqual(cm.exception.code, 502)


class TestNonLoopbackGuard(unittest.TestCase):
    def test_refuses_public_bind_without_token(self):
        # run() must refuse a non-loopback host with no token (rc 2), not bind.
        os.environ.pop("KAJI_BRAIN_TOKEN", None)
        rc = serve.run(host="0.0.0.0", port=0, token=None)
        self.assertEqual(rc, 2)


class TestSSE(unittest.TestCase):
    def setUp(self):
        brain.collect_sessions = lambda: []
        brain.load_quota = lambda: {}
        brain.load_limits = lambda: {}
        brain.read_events = lambda: []
        os.environ["KAJI_BRAIN_SSE_POLL"] = "0.1"
        serve.POLL_SECS = 0.1
        self.httpd, self.base = _start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def test_stream_pushes_state(self):
        req = urllib.request.Request(self.base + "/api/events")
        with urllib.request.urlopen(req, timeout=3) as r:
            chunk = r.read(120).decode("utf-8")
        self.assertIn("event: state", chunk)


if __name__ == "__main__":
    unittest.main(verbosity=2)
