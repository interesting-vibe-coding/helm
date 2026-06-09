#!/usr/bin/env python3
"""Minimal Server-Sent Events (SSE) parser — engine-agnostic.

The Goose spike client consumes goosed's `text/event-stream` reply. The wire
format is the W3C EventSource spec, which is independent of anything
Goose-specific, so this parser is written and tested on its own:

  - the stream is UTF-8 text split into lines (\\n, \\r\\n, or \\r);
  - a line `field: value` sets a field (one optional space after the colon is
    stripped); a line with no colon is a field with an empty value; a line that
    starts with `:` is a comment and ignored;
  - the `data` field accumulates across multiple `data:` lines, joined by \\n;
  - a blank line dispatches the buffered event.

`iter_events` is incremental: feed it any iterable of decoded lines (e.g. from
`requests`/`httpx` `iter_lines`) and it yields one SSEEvent per dispatched
event. The Goose-specific JSON inside `event.data` is parsed by the caller, not
here — keeping this layer reusable if the engine is swapped (opencode/Crush).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional


@dataclass
class SSEEvent:
    """One dispatched SSE event. `data` is the joined data payload (may be '')."""
    event: str = "message"  # the `event:` field, defaulting to "message" per spec
    data: str = ""
    id: Optional[str] = None
    _data_lines: List[str] = field(default_factory=list, repr=False)

    def is_empty(self) -> bool:
        """True if nothing was set — such events are not dispatched per spec."""
        return not self._data_lines and self.event == "message" and self.id is None


def _strip_bom(line: str) -> str:
    return line[1:] if line and line[0] == "﻿" else line


def iter_events(lines: Iterable[str]) -> Iterator[SSEEvent]:
    """Yield SSEEvents from an iterable of decoded lines (newlines stripped).

    Lines may arrive with or without trailing newlines; we normalize by
    rstripping a single trailing \\r (handles \\r\\n splits) and treat an empty
    line as the event boundary.
    """
    cur = SSEEvent()
    first = True
    for raw in lines:
        line = raw.rstrip("\n")
        line = line[:-1] if line.endswith("\r") else line
        if first:
            line = _strip_bom(line)
            first = False

        if line == "":
            # Blank line: dispatch the buffered event (if any data accumulated).
            if cur._data_lines:
                cur.data = "\n".join(cur._data_lines)
                yield cur
            cur = SSEEvent()
            continue

        if line.startswith(":"):
            # Comment line — ignored (often a keep-alive heartbeat).
            continue

        if ":" in line:
            field_name, value = line.split(":", 1)
            if value.startswith(" "):
                value = value[1:]
        else:
            field_name, value = line, ""

        if field_name == "event":
            cur.event = value
        elif field_name == "data":
            cur._data_lines.append(value)
        elif field_name == "id":
            # Per spec, ignore an id containing a NUL; otherwise set it.
            if "\x00" not in value:
                cur.id = value
        elif field_name == "retry":
            pass  # reconnection timing — not relevant to a one-shot client
        # Unknown fields are ignored per spec.

    # Stream ended. Per spec a trailing event without a final blank line is NOT
    # dispatched; goosed terminates events with blank lines, so we mirror the
    # spec and drop any unterminated remainder.


def iter_data(lines: Iterable[str]) -> Iterator[str]:
    """Convenience: yield just the `data` payload of each event (skip empties)."""
    for ev in iter_events(lines):
        if ev.data != "":
            yield ev.data
