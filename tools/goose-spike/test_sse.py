#!/usr/bin/env python3
"""Tests for the engine-agnostic SSE parser.

    cd tools/goose-spike && python3 -m unittest discover -p 'test_*.py'
"""
import unittest

from sse import SSEEvent, iter_data, iter_events


def _lines(blob):
    # Simulate a line iterator (like requests' iter_lines) by splitting on \n.
    return blob.split("\n")


class SSEParserTests(unittest.TestCase):
    def test_single_event_default_type(self):
        events = list(iter_events(_lines("data: hello\n\n")))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event, "message")
        self.assertEqual(events[0].data, "hello")

    def test_named_event_and_id(self):
        events = list(iter_events(_lines("event: Message\nid: 7\ndata: hi\n\n")))
        self.assertEqual(events[0].event, "Message")
        self.assertEqual(events[0].id, "7")
        self.assertEqual(events[0].data, "hi")

    def test_multiline_data_joined_with_newline(self):
        events = list(iter_events(_lines("data: line1\ndata: line2\n\n")))
        self.assertEqual(events[0].data, "line1\nline2")

    def test_multiple_events(self):
        blob = "event: A\ndata: 1\n\nevent: B\ndata: 2\n\n"
        events = list(iter_events(_lines(blob)))
        self.assertEqual([(e.event, e.data) for e in events], [("A", "1"), ("B", "2")])

    def test_comment_and_heartbeat_ignored(self):
        blob = ": keep-alive\ndata: real\n\n"
        events = list(iter_events(_lines(blob)))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].data, "real")

    def test_optional_space_after_colon_stripped_once(self):
        # Only the first space is stripped; a second space is data.
        events = list(iter_events(_lines("data:  two-leading-spaces\n\n")))
        self.assertEqual(events[0].data, " two-leading-spaces")

    def test_field_without_colon_is_empty_value(self):
        # A bare "data" line contributes an empty data line.
        events = list(iter_events(_lines("data\ndata: x\n\n")))
        self.assertEqual(events[0].data, "\nx")

    def test_crlf_line_endings(self):
        events = list(iter_events("data: hi\r\n\r\n".split("\n")))
        self.assertEqual(events[0].data, "hi")

    def test_unterminated_trailing_event_dropped(self):
        # No final blank line -> not dispatched (matches the spec + goosed).
        events = list(iter_events(_lines("data: incomplete")))
        self.assertEqual(events, [])

    def test_iter_data_skips_empty_payloads(self):
        blob = "event: ping\n\ndata: payload\n\n"
        self.assertEqual(list(iter_data(_lines(blob))), ["payload"])

    def test_is_empty_helper(self):
        self.assertTrue(SSEEvent().is_empty())
        e = SSEEvent()
        e._data_lines.append("x")
        self.assertFalse(e.is_empty())


if __name__ == "__main__":
    unittest.main()
