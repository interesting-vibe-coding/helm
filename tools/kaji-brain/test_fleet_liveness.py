#!/usr/bin/env python3
"""Tests for kaji#125 — stale fleet state when the Kaji mux is down.

Covers the three legs of the fix:
  1. _live_gui_sock(): real unix-socket connect test (dead socket files and
     empty dirs yield None; the newest LIVE socket wins).
  2. _cli_run(): refuses with a clear error when no live socket exists, and
     pins WEZTERM_UNIX_SOCKET when one does.
  3. collect_sessions(): mux down (list_panes -> None) means an EMPTY fleet,
     never a fallback to the cached runtime.json snapshot.
"""

import json
import os
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain  # noqa: E402


class SockDirCase(unittest.TestCase):
    """Base: point brain.SOCK_DIR at a private temp dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_sock_dir = brain.SOCK_DIR
        brain.SOCK_DIR = Path(self._tmp.name)
        self._listeners = []

    def tearDown(self):
        for s in self._listeners:
            s.close()
        brain.SOCK_DIR = self._orig_sock_dir
        self._tmp.cleanup()

    def _live_sock(self, name):
        """Create a LIVE listening unix socket gui-sock-<name>."""
        path = os.path.join(self._tmp.name, "gui-sock-%s" % name)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(path)
        s.listen(1)
        self._listeners.append(s)
        return path

    def _dead_sock(self, name):
        """Create a socket FILE with no listener (crashed-GUI leftover)."""
        path = os.path.join(self._tmp.name, "gui-sock-%s" % name)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(path)
        s.close()  # file remains, nothing accepts
        return path


class TestLiveGuiSock(SockDirCase):
    def test_empty_dir_is_none(self):
        self.assertIsNone(brain._live_gui_sock())

    def test_dead_socket_file_is_none(self):
        self._dead_sock("79010")
        self.assertIsNone(brain._live_gui_sock())

    def test_live_socket_found(self):
        path = self._live_sock("77032")
        self.assertEqual(brain._live_gui_sock(), path)

    def test_newest_live_wins_over_dead(self):
        # The kaji#125 repro: dead leftover + fresh launch side by side.
        self._dead_sock("79010")
        time.sleep(0.02)
        live = self._live_sock("77032")
        self.assertEqual(brain._live_gui_sock(), live)


class TestCliRun(SockDirCase):
    def test_refuses_without_live_sock(self):
        rc, out, err = brain._cli_run(["/bin/echo"], ["hello"])
        self.assertEqual(rc, 1)
        self.assertIn("no live gui socket", err)

    def test_pins_env_to_live_sock(self):
        path = self._live_sock("77032")
        rc, out, _ = brain._cli_run(
            [sys.executable, "-c",
             "import os; print(os.environ['WEZTERM_UNIX_SOCKET'])"], [])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), path)


class TestNoPhantomSessions(unittest.TestCase):
    def setUp(self):
        self._orig = (brain.list_panes, brain.load_runtime, brain.load_quota)
        # runtime.json has a cached worker — the 26h phantom from kaji#125.
        brain.load_runtime = lambda: {
            "1": {"harness": "claude", "cwd": "/w/kaji",
                  "state": "waiting", "start_time": int(time.time()) - 26 * 3600},
        }
        brain.load_quota = lambda: {"claude": 5}

    def tearDown(self):
        brain.list_panes, brain.load_runtime, brain.load_quota = self._orig

    def test_mux_down_means_empty_fleet(self):
        brain.list_panes = lambda: None
        self.assertEqual(brain.collect_sessions(), [])

    def test_no_panes_means_empty_fleet(self):
        brain.list_panes = lambda: []
        self.assertEqual(brain.collect_sessions(), [])

    def test_live_pane_still_reported(self):
        brain.list_panes = lambda: [{"pane_id": 1}]
        sessions = brain.collect_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["pane_id"], 1)
        self.assertEqual(sessions[0]["harness"], "claude")


class TestListPanesNone(unittest.TestCase):
    def test_cli_missing_is_none(self):
        orig = brain._helm_cli
        brain._helm_cli = lambda: None
        try:
            self.assertIsNone(brain.list_panes())
        finally:
            brain._helm_cli = orig

    def test_cli_failure_is_none(self):
        orig_cli, orig_run = brain._helm_cli, brain._cli_run
        brain._helm_cli = lambda: ["fake"]
        brain._cli_run = lambda cli, args, timeout=10: (1, "", "boom")
        try:
            self.assertIsNone(brain.list_panes())
        finally:
            brain._helm_cli, brain._cli_run = orig_cli, orig_run

    def test_empty_output_is_empty_list(self):
        orig_cli, orig_run = brain._helm_cli, brain._cli_run
        brain._helm_cli = lambda: ["fake"]
        brain._cli_run = lambda cli, args, timeout=10: (0, "", "")
        try:
            self.assertEqual(brain.list_panes(), [])
        finally:
            brain._helm_cli, brain._cli_run = orig_cli, orig_run

    def test_panes_parsed(self):
        orig_cli, orig_run = brain._helm_cli, brain._cli_run
        brain._helm_cli = lambda: ["fake"]
        brain._cli_run = lambda cli, args, timeout=10: (
            0, json.dumps([{"pane_id": 7}]), "")
        try:
            self.assertEqual(brain.list_panes(), [{"pane_id": 7}])
        finally:
            brain._helm_cli, brain._cli_run = orig_cli, orig_run


class TestResolveProg(unittest.TestCase):
    """GUI PATH lacks user bin dirs (kaji spawn-from-phone bug)."""

    def test_absolute_passthrough(self):
        self.assertEqual(brain._resolve_prog(["/usr/bin/true", "-x"]),
                         ["/usr/bin/true", "-x"])

    def test_resolves_via_which(self):
        out = brain._resolve_prog(["sh", "-c", "x"])
        self.assertTrue(os.path.isabs(out[0]), out)
        self.assertEqual(out[1:], ["-c", "x"])

    def test_falls_back_to_extra_dirs(self):
        import shutil as _sh
        import tempfile as _tf
        with _tf.TemporaryDirectory() as d:
            exe = os.path.join(d, "fakeharness")
            open(exe, "w").write("#!/bin/sh\n")
            os.chmod(exe, 0o755)
            orig_which, orig_dirs = brain.shutil.which, brain.EXTRA_BIN_DIRS
            brain.shutil.which = lambda n: None
            brain.EXTRA_BIN_DIRS = [d]
            try:
                self.assertEqual(brain._resolve_prog(["fakeharness", "--go"]),
                                 [exe, "--go"])
            finally:
                brain.shutil.which, brain.EXTRA_BIN_DIRS = orig_which, orig_dirs

    def test_unresolvable_left_as_is(self):
        orig_which, orig_dirs = brain.shutil.which, brain.EXTRA_BIN_DIRS
        brain.shutil.which = lambda n: None
        brain.EXTRA_BIN_DIRS = []
        try:
            self.assertEqual(brain._resolve_prog(["nope-bin"]), ["nope-bin"])
        finally:
            brain.shutil.which, brain.EXTRA_BIN_DIRS = orig_which, orig_dirs


if __name__ == "__main__":
    unittest.main(verbosity=2)
