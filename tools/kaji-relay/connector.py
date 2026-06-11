#!/usr/bin/env python3
"""kaji-relay connector — the Mac side of the relay.

Long-polls the public relay over OUTBOUND https (no inbound ports, no VPN,
works behind any proxy), executes each queued request against the local
`kaji-brain serve` on 127.0.0.1, and posts the response back.

    phone ──▶ relay /c/<rid>/api/state
                 │ (queued)
    this ──poll──┘ ──▶ http://127.0.0.1:8787/api/state ──reply──▶ relay ──▶ phone

Env:
    KAJI_RELAY_URL   https://kaji-relay.<acct>.workers.dev   (required)
    KAJI_RELAY_ID    long random capability id               (required)
    KAJI_RELAY_KEY   shared secret with the worker           (required)
    KAJI_LOCAL_URL   default http://127.0.0.1:8787

Pure stdlib, mirrors the kaji-brain philosophy. Serial by design: the mobile
cockpit polls every 4s and sends are rare, so one in-flight request at a time
is plenty for v0.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

RELAY = os.environ.get("KAJI_RELAY_URL", "").rstrip("/")
RID = os.environ.get("KAJI_RELAY_ID", "")
KEY = os.environ.get("KAJI_RELAY_KEY", "")
LOCAL = os.environ.get("KAJI_LOCAL_URL", "http://127.0.0.1:8787").rstrip("/")

# The local hop must never go through a system proxy (Clash etc.).
_local_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# Cloudflare's bot protection 403s the default "Python-urllib/3.x" UA.
UA = "kaji-relay-connector/1.0"


def _poll():
    """One long-poll. Returns a job dict or None (204 / transient error)."""
    req = urllib.request.Request(RELAY + "/agent/poll?id=" + RID)
    req.add_header("X-Relay-Key", KEY)
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=35) as r:
        if r.status == 204:
            return None
        return json.loads(r.read().decode("utf-8"))


def _execute(job):
    """Run the job against local kaji-brain serve. Returns a reply dict."""
    url = LOCAL + job.get("path", "/")
    body = base64.b64decode(job["body_b64"]) if job.get("body_b64") else None
    req = urllib.request.Request(url, data=body, method=job.get("method", "GET"))
    if job.get("authorization"):
        req.add_header("Authorization", job["authorization"])
    if job.get("content_type"):
        req.add_header("Content-Type", job["content_type"])
    try:
        with _local_opener.open(req, timeout=20) as r:
            payload = r.read()
            ctype = r.headers.get("Content-Type", "application/json")
            status = r.status
    except urllib.error.HTTPError as e:
        payload = e.read()
        ctype = e.headers.get("Content-Type", "application/json")
        status = e.code
    except Exception as e:  # noqa: BLE001 - serve down etc.
        payload = json.dumps({"error": "local serve unreachable: %s" % e}).encode()
        ctype = "application/json"
        status = 502
    return {
        "status": status,
        "content_type": ctype,
        "body_b64": base64.b64encode(payload).decode("ascii"),
    }


def _reply(req_id, reply):
    data = json.dumps(reply).encode("utf-8")
    req = urllib.request.Request(
        RELAY + "/agent/reply?id=" + RID + "&req=" + str(req_id),
        data=data, method="POST")
    req.add_header("X-Relay-Key", KEY)
    req.add_header("User-Agent", UA)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


def main():
    if not (RELAY and RID and KEY):
        sys.stderr.write(
            "KAJI_RELAY_URL, KAJI_RELAY_ID and KAJI_RELAY_KEY are required.\n")
        return 2
    sys.stderr.write("kaji-relay connector → %s (id %s…)\n" % (RELAY, RID[:6]))
    backoff = 1
    while True:
        try:
            job = _poll()
            backoff = 1
            if not job:
                continue
            _reply(job["req_id"], _execute(job))
        except KeyboardInterrupt:
            sys.stderr.write("\nbye.\n")
            return 0
        except Exception as e:  # noqa: BLE001 - network blips: retry forever
            sys.stderr.write("relay error: %s (retry in %ds)\n" % (e, backoff))
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    sys.exit(main())
