#!/usr/bin/env python3
"""Tests for quota.py — codex parsing (cumulative token_count + rate_limits)."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota  # noqa: E402


def _tc_line(total_tokens, primary_pct=None, secondary_pct=None, plan=None):
    rl = {
        "primary": {"used_percent": primary_pct, "resets_at": 111} if primary_pct is not None else None,
        "secondary": {"used_percent": secondary_pct, "resets_at": 222} if secondary_pct is not None else None,
        "plan_type": plan,
    }
    return json.dumps({
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": {"total_tokens": total_tokens}},
            "rate_limits": rl,
        },
    })


class TestCodex(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = quota.CODEX_SESSIONS
        quota.CODEX_SESSIONS = Path(self._tmp.name)
        today = datetime.now(timezone.utc)
        self.day_dir = Path(self._tmp.name) / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
        self.day_dir.mkdir(parents=True)

    def tearDown(self):
        quota.CODEX_SESSIONS = self._orig
        self._tmp.cleanup()

    def _write(self, name, lines):
        (self.day_dir / name).write_text("\n".join(lines) + "\n")

    def test_missing_dir(self):
        quota.CODEX_SESSIONS = Path(self._tmp.name) / "nope"
        self.assertEqual(quota.codex(), (0, None, None, None))

    def test_cumulative_takes_last_not_sum(self):
        # 3 events in one session: cumulative 100 -> 250 -> 400. Today = 400.
        self._write("rollout-a.jsonl",
                    [_tc_line(100), _tc_line(250), _tc_line(400)])
        sess, tok, _last, _ = quota.codex()
        self.assertEqual(sess, 1)
        self.assertEqual(tok, 400)

    def test_sums_across_sessions(self):
        self._write("rollout-a.jsonl", [_tc_line(400)])
        self._write("rollout-b.jsonl", [_tc_line(100), _tc_line(600)])
        _, tok, _, _ = quota.codex()
        self.assertEqual(tok, 1000)

    def test_limits_from_freshest(self):
        self._write("rollout-a.jsonl",
                    [_tc_line(50, primary_pct=10.0, secondary_pct=38.5, plan="plus")])
        _, _, _, limits = quota.codex()
        self.assertEqual(limits["primary_used_percent"], 10.0)
        self.assertEqual(limits["secondary_used_percent"], 38.5)
        self.assertEqual(limits["secondary_resets_at"], 222)
        self.assertEqual(limits["plan"], "plus")

    def test_null_windows_yield_plan_only(self):
        self._write("rollout-a.jsonl", [_tc_line(50, plan="plus")])
        _, _, _, limits = quota.codex()
        self.assertEqual(limits, {"plan": "plus"})

    def test_corrupt_lines_skipped(self):
        self._write("rollout-a.jsonl", ["{not json", _tc_line(70), '"token_count"'])
        _, tok, _, _ = quota.codex()
        self.assertEqual(tok, 70)

    def test_emit_json_has_limits_key(self):
        self._write("rollout-a.jsonl", [_tc_line(70, secondary_pct=20.0, plan="plus")])
        rows = dict((r[0], r) for r in quota.collect())
        name, sess, tok, last, limits = rows["codex"]
        self.assertEqual(tok, 70)
        self.assertEqual(limits["plan"], "plus")


if __name__ == "__main__":
    unittest.main(verbosity=2)
