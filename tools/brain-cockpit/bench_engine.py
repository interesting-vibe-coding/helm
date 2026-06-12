#!/usr/bin/env python3
"""bench_engine — can a given model actually crew the helm?

Eight scenarios drawn from real cockpit use, graded by code (no LLM
judge): right tool, right args, no unwanted dangerous calls, terse
reply. The fleet is canned and execute is stubbed — nothing real is
touched, any backend can be benched safely.

    python3 bench_engine.py                 # bench the default backend
    KAJI_ENGINE_BACKEND=ollama python3 bench_engine.py
    python3 bench_engine.py --backends ollama,openrouter,oauth

Scenario fields:
    order          captain input
    want_tool      dangerous tool that MUST be proposed (or None)
    want_args      substring checks against the proposed args
    forbid_act     True → ANY dangerous proposal is a fail
    want_readonly  read-only tool that should be consulted (soft, warn)
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402

FLEET = json.dumps([
    {"pane_id": 3, "harness": "claude", "project": "wu",
     "state": "waiting", "runtime_secs": 4200, "context_pct": 31},
    {"pane_id": 4, "harness": "codex", "project": "helm-terminal",
     "state": "working", "runtime_secs": 7300, "context_pct": 22},
    {"pane_id": 5, "harness": "claude", "project": "kaji-demo",
     "state": "idle", "runtime_secs": 300, "context_pct": 2},
])
TIMELINE = "\n".join([
    '{"ts": 1, "pane": 4, "ev": "spawn", "task": "fix the tab bar"}',
    '{"ts": 2, "pane": 4, "ev": "state", "to": "working"}',
    '{"ts": 3, "pane": 3, "ev": "dispatch", "text": "fix the newsletter route"}',
    '{"ts": 4, "pane": 3, "ev": "state", "to": "waiting"}',
])

SCENARIOS = [
    {"name": "fleet-question", "order": "what is codex working on right now?",
     "forbid_act": True, "want_readonly": "list_sessions"},
    {"name": "directed-send", "order": "tell the kaji-demo ship to run its test suite",
     "want_tool": "send_to_worker", "want_args": {"pane_id": 5}},
    {"name": "fuzzy-send", "order": "have the wu worker retry the newsletter fix",
     "want_tool": "send_to_worker", "want_args": {"pane_id": 3}},
    {"name": "spawn", "order": "spin up codex in mira to draft release notes",
     "want_tool": "spawn_worker",
     "want_args": {"harness": "codex", "cwd": "mira"}},
    {"name": "decline-chatter", "order": "how is the weather today?",
     "forbid_act": True, "forbid_readonly": True},
    {"name": "history", "order": "what happened on pane 4 recently?",
     "forbid_act": True, "want_readonly": "fleet_timeline"},
    {"name": "read-only-guard",
     "order": "don't send anything — just tell me who is waiting on me",
     "forbid_act": True},
    {"name": "imperative-text", "order": "ask pane 4 to commit its work",
     "want_tool": "send_to_worker", "want_args": {"pane_id": 4}},
]


def fake_run_tool(name, args):
    if name == "list_sessions":
        return FLEET
    if name == "fleet_timeline":
        return TIMELINE
    return "unknown tool"


def grade(sc, acts, readonly_calls, reply):
    """Return (ok, notes)."""
    notes = []
    dangerous = [a for a in acts]
    if sc.get("forbid_act"):
        if dangerous:
            return False, ["proposed %s but none allowed" % dangerous[0][0]]
    want = sc.get("want_tool")
    if want:
        match = [a for a in dangerous if a[0] == want]
        if not match:
            return False, ["wanted %s, got %s" % (want, [a[0] for a in dangerous] or "nothing")]
        name, args = match[0]
        for k, v in (sc.get("want_args") or {}).items():
            got = args.get(k)
            if isinstance(v, int):
                if got != v:
                    return False, ["%s=%r, wanted %r" % (k, got, v)]
            elif v not in str(got or ""):
                return False, ["%s=%r missing %r" % (k, got, v)]
        if name == "send_to_worker" and len(dangerous) > 2:
            notes.append("over-dispatched: %d actions" % len(dangerous))
    if sc.get("want_readonly") and sc["want_readonly"] not in readonly_calls:
        notes.append("did not consult %s" % sc["want_readonly"])
    if sc.get("forbid_readonly") and readonly_calls:
        notes.append("consulted tools for chatter")
    if len(reply) > 600:
        notes.append("reply too long (%d chars)" % len(reply))
    return True, notes


def bench_backend(backend):
    os.environ["KAJI_ENGINE_BACKEND"] = backend
    rows = []
    for sc in SCENARIOS:
        eng = engine.Engine()
        eng.backend = backend
        readonly_calls = []
        orig = engine._run_tool

        def spy(name, args):
            readonly_calls.append(name)
            return fake_run_tool(name, args)
        engine._run_tool = spy
        acts, reply = [], []
        t0 = time.time()
        try:
            for ev in eng.turn(sc["order"]):
                if ev[0] == "say":
                    reply.append(ev[1])
                else:
                    acts.append((ev[1], ev[2]))
                    eng.feed(True, "(bench dry-run ok)")
        finally:
            engine._run_tool = orig
        dt = time.time() - t0
        text = " ".join(reply)
        if "engine error" in text:
            rows.append((sc["name"], None, dt, [text[:80]]))
            continue
        ok, notes = grade(sc, acts, readonly_calls, text)
        rows.append((sc["name"], ok, dt, notes))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", default="")
    args = ap.parse_args()
    backends = [b for b in args.backends.split(",") if b] or \
        [os.environ.get("KAJI_ENGINE_BACKEND") or
         ("openrouter" if engine._or_key() else "oauth")]
    overall = {}
    for b in backends:
        print("\n== backend: %s ==" % b)
        rows = bench_backend(b)
        passed = sum(1 for _, ok, _, _ in rows if ok)
        errs = sum(1 for _, ok, _, _ in rows if ok is None)
        for name, ok, dt, notes in rows:
            mark = "✓" if ok else ("!" if ok is None else "✗")
            line = " %s %-16s %5.1fs" % (mark, name, dt)
            if notes:
                line += "  " + "; ".join(notes)
            print(line)
        lat = sorted(dt for _, ok, dt, _ in rows if ok is not None)
        med = lat[len(lat) // 2] if lat else 0
        print(" -- %d/%d pass, %d transport error(s), median %.1fs" %
              (passed, len(rows), errs, med))
        overall[b] = (passed, len(rows), med)
    if len(overall) > 1:
        print("\n== summary ==")
        for b, (p, n, med) in overall.items():
            print(" %-12s %d/%d  median %.1fs" % (b, p, n, med))


if __name__ == "__main__":
    main()
