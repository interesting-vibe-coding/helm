#!/usr/bin/env python3
"""Unit tests for the helm-brain event-log substrate (events.jsonl).

Pure stdlib (unittest) so CI can run them with no extra deps:

    cd tools/helm-brain && python3 -m unittest discover -p 'test_*.py'

The event log is the no-regret history chain underneath both the timeline
renderer and any future First Mate, so its append / read / render contract is
worth pinning down.
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import brain


class EventLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = brain.EVENTS_JSONL
        # Nested path so we also exercise parent-dir creation.
        brain.EVENTS_JSONL = Path(self._tmp.name) / "sessions" / "events.jsonl"

    def tearDown(self):
        brain.EVENTS_JSONL = self._orig
        self._tmp.cleanup()

    def test_append_creates_dir_and_appends_in_order(self):
        brain.append_event("spawn", pane=2, harness="claude", cwd="kaji", task="fix #452")
        brain.append_event("state", pane=2, to="working")
        brain.append_event("dispatch", pane=2, text="run the full test suite")
        events = brain.read_events()
        self.assertEqual([e["ev"] for e in events], ["spawn", "state", "dispatch"])
        self.assertEqual(events[0]["pane"], 2)
        self.assertEqual(events[0]["task"], "fix #452")
        self.assertIsInstance(events[0]["ts"], int)
        self.assertEqual(events[1]["to"], "working")
        self.assertEqual(events[2]["text"], "run the full test suite")

    def test_read_missing_file_is_empty(self):
        self.assertEqual(brain.read_events(), [])

    def test_read_skips_corrupt_lines(self):
        brain.EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with open(brain.EVENTS_JSONL, "w", encoding="utf-8") as f:
            f.write('{"ts":1,"ev":"spawn","pane":1}\n')
            f.write("not json — half-written crash line\n")
            f.write("\n")  # blank line
            f.write('{"ts":2,"ev":"state","pane":1,"to":"done"}\n')
        events = brain.read_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["to"], "done")

    def test_append_never_raises_on_unwritable_path(self):
        # An embedded null byte makes mkdir/open raise; append must swallow it.
        brain.EVENTS_JSONL = Path("/no/such/root\x00/events.jsonl")
        brain.append_event("state", pane=1, to="working")  # must not raise

    def test_unicode_preserved(self):
        brain.append_event("dispatch", pane=1, text="跑测试 ✓")
        self.assertEqual(brain.read_events()[0]["text"], "跑测试 ✓")

    def test_as_pane_int_coercion(self):
        self.assertEqual(brain._as_pane("7"), 7)
        self.assertEqual(brain._as_pane(7), 7)
        self.assertEqual(brain._as_pane(None), None)
        self.assertEqual(brain._as_pane("abc"), "abc")


class TimelineRenderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = brain.EVENTS_JSONL
        brain.EVENTS_JSONL = Path(self._tmp.name) / "events.jsonl"
        # Keep the render hermetic: no Kaji running, so the "now" snapshot is empty.
        self._orig_collect = brain.collect_sessions
        brain.collect_sessions = lambda: []

    def tearDown(self):
        brain.EVENTS_JSONL = self._orig
        brain.collect_sessions = self._orig_collect
        self._tmp.cleanup()

    def _run_timeline(self, args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = brain.cmd_timeline(args)
        return rc, buf.getvalue()

    def test_timeline_json_roundtrips_events(self):
        brain.append_event("spawn", pane=3, harness="kiro", cwd="mira", task="")
        brain.append_event("state", pane=3, to="waiting")
        rc, out = self._run_timeline(["--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertEqual([e["ev"] for e in parsed], ["spawn", "state"])

    def test_timeline_human_feed_newest_first(self):
        brain.append_event("spawn", pane=2, harness="claude", cwd="kaji", task="fix #452")
        brain.append_event("state", pane=2, to="working")
        rc, out = self._run_timeline([])
        self.assertEqual(rc, 0)
        self.assertIn("Kaji fleet timeline", out)
        self.assertIn("fix #452", out)
        # state (newest) should appear before spawn (oldest) in the feed.
        self.assertLess(out.index("working"), out.index("fix #452"))

    def test_timeline_pane_filter(self):
        brain.append_event("state", pane=2, to="working")
        brain.append_event("state", pane=5, to="waiting")
        rc, out = self._run_timeline(["--json", "--pane", "5"])
        parsed = json.loads(out)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["pane"], 5)

    def test_timeline_empty_log(self):
        rc, out = self._run_timeline([])
        self.assertEqual(rc, 0)
        self.assertIn("none yet", out)


if __name__ == "__main__":
    unittest.main()
