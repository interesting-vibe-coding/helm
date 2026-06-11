#!/usr/bin/env python3
"""Tests for the pure render/sort logic of the render-only Brain cockpit.

    cd tools/brain-cockpit && python3 -m unittest discover -p 'test_*.py'
"""
import unittest

import cockpit as ck


class SortTests(unittest.TestCase):
    def test_most_neglected_first(self):
        sessions = [
            {"pane_id": 1, "state": "working", "runtime_secs": 100},
            {"pane_id": 2, "state": "waiting", "runtime_secs": 50},
            {"pane_id": 3, "state": "done", "runtime_secs": 9999},
            {"pane_id": 4, "state": "waiting", "runtime_secs": 800},
        ]
        order = [s["pane_id"] for s in ck.sort_sessions(sessions)]
        # waiting first; among waiting, longest-waiting (800) before (50);
        # working before done.
        self.assertEqual(order, [4, 2, 1, 3])

    def test_unknown_state_sinks_but_present(self):
        sessions = [{"pane_id": 1, "state": "weird"}, {"pane_id": 2, "state": "waiting"}]
        order = [s["pane_id"] for s in ck.sort_sessions(sessions)]
        self.assertEqual(order, [2, 1])


class StyleTests(unittest.TestCase):
    def test_status_style_known_and_unknown(self):
        self.assertEqual(ck.status_style("waiting")[2], "waiting")
        self.assertEqual(ck.status_style("WORKING")[2], "working")  # case-insensitive
        self.assertEqual(ck.status_style("nonsense")[2], "?")

    def test_fmt_runtime(self):
        self.assertEqual(ck.fmt_runtime(5), "5s")
        self.assertEqual(ck.fmt_runtime(125), "2m")
        self.assertEqual(ck.fmt_runtime(3725), "1h02m")
        self.assertEqual(ck.fmt_runtime(-3), "0s")


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            {"ts": 1, "pane": 2, "ev": "spawn", "task": "port #452"},
            {"ts": 2, "pane": 2, "ev": "state", "to": "working"},
            {"ts": 3, "pane": 2, "ev": "dispatch", "text": "run tests"},
            {"ts": 4, "pane": 9, "ev": "spawn", "task": ""},
        ]

    def test_last_activity_uses_latest_event(self):
        self.assertEqual(ck.last_activity(self.events, 2), "you sent: run tests")

    def test_last_activity_spawn_without_task(self):
        self.assertEqual(ck.last_activity(self.events, 9), "spawned")

    def test_last_activity_empty(self):
        self.assertEqual(ck.last_activity(self.events, 404), "")

    def test_pane_events_filter(self):
        self.assertEqual(len(ck.pane_events(self.events, 2)), 3)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.sessions, self.events, self.quota = ck.demo_data()

    def _plain(self, **kw):
        return ck.render(self.sessions, self.events, color=False, **kw)

    def test_brand_and_sessions_present(self):
        out = self._plain(width=80)
        self.assertIn("KAJI", out)
        self.assertIn("you steer", out)
        # the waiting session (kaji) should appear before a done one (wu)
        self.assertLess(out.index("kaji"), out.index("wu"))

    def test_selected_detail_shows_pane_history(self):
        # Select row 0 (the waiting kaji pane after sorting) and expect its
        # dispatched instruction to render in the detail panel.
        out = self._plain(width=80, selected=0)
        self.assertIn("run the full test suite", out)

    def test_empty_fleet_message(self):
        out = ck.render([], [], color=False, width=80)
        self.assertIn("No active sessions", out)

    def test_color_toggle_adds_escapes(self):
        self.assertIn("\033[", ck.render(self.sessions, self.events, color=True, width=80))
        self.assertNotIn("\033[", ck.render(self.sessions, self.events, color=False, width=80))


class KeyTests(unittest.TestCase):
    def test_quit_keys(self):
        for b in (b"q", b"Q", b"\x03"):
            self.assertEqual(ck.parse_key(b), "quit")

    def test_arrows_and_vim(self):
        self.assertEqual(ck.parse_key(b"\x1b[A"), "up")
        self.assertEqual(ck.parse_key(b"k"), "up")
        self.assertEqual(ck.parse_key(b"\x1b[B"), "down")
        self.assertEqual(ck.parse_key(b"j"), "down")

    def test_actions(self):
        self.assertEqual(ck.parse_key(b"\r"), "send")
        self.assertEqual(ck.parse_key(b"s"), "spawn")
        self.assertEqual(ck.parse_key(b"r"), "refresh")
        self.assertEqual(ck.parse_key(b""), "none")
        self.assertEqual(ck.parse_key(b"x"), "none")


class ActionTests(unittest.TestCase):
    """send/spawn shell out to kaji-brain with the right argv (no server)."""

    def setUp(self):
        self._run = ck.subprocess.run
        self._argv = ck._helm_brain_argv
        ck._helm_brain_argv = lambda: ["kaji-brain"]
        self.calls = []

        class _P:
            returncode = 0
            stderr = b""
        def fake_run(argv, **kw):
            self.calls.append(argv)
            return _P()
        ck.subprocess.run = fake_run

    def tearDown(self):
        ck.subprocess.run = self._run
        ck._helm_brain_argv = self._argv

    def test_send_argv(self):
        ok, err = ck.send_text("", None, 7, "hello")
        self.assertTrue(ok)
        self.assertEqual(self.calls[0], ["kaji-brain", "send", "7", "hello"])

    def test_spawn_argv_with_task(self):
        ok, _ = ck.spawn_worker("", None, "claude", "/tmp", "do x")
        self.assertTrue(ok)
        self.assertEqual(self.calls[0], ["kaji-brain", "spawn", "claude", "/tmp", "do x"])

    def test_spawn_argv_no_task(self):
        ck.spawn_worker("", None, "kiro", "/tmp")
        self.assertEqual(self.calls[0], ["kaji-brain", "spawn", "kiro", "/tmp"])


if __name__ == "__main__":
    unittest.main()
