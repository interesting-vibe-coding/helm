/**
 * kaji-relay — thin public relay for the Kaji fleet API.
 *
 * Shape (same as Anthropic Remote Control / Happy): the Mac never opens an
 * inbound port. A connector on the Mac LONG-POLLS this relay over outbound
 * HTTPS; the phone talks plain HTTPS to the same relay. The relay holds no
 * business logic and no fleet state — it queues requests and matches replies.
 *
 *   phone ──HTTPS──▶ /c/<rid>/api/state ──▶ DO queue ──▶ (connector poll)
 *   Mac   ──HTTPS──▶ /agent/poll?id=<rid>  ◀─ job        │
 *         ──HTTPS──▶ /agent/reply          ──────────────┘──▶ phone response
 *
 * Security model:
 *   • <rid> is a long random capability id (pick with `openssl rand -hex 16`).
 *   • /agent/* requires X-Relay-Key == RELAY_KEY (worker secret) — nobody else
 *     can drain the queue (queued requests carry the phone's bearer token).
 *   • End-to-end auth stays the kaji-brain bearer token: the relay forwards
 *     the Authorization header verbatim and `kaji-brain serve` validates it.
 *     The relay never knows whether a token is valid.
 */

const AGENT_POLL_MS = 25000; // held-open poll; under CF's 30s response window
const CLIENT_WAIT_MS = 30000; // phone waits this long for the Mac to answer

export class RelaySession {
  constructor(state, env) {
    this.env = env;
    this.queue = [];          // jobs not yet picked up by the connector
    this.agentWaiter = null;  // resolver for a held-open /agent/poll
    this.pending = new Map(); // req_id -> {resolve, timer} phone waiting
    this.nextId = 1;
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/agent/poll") return this.agentPoll();
    if (url.pathname === "/agent/reply") return this.agentReply(request, url);
    return this.clientForward(request, url);
  }

  // ── connector side ──────────────────────────────────────────────────────
  agentPoll() {
    // Drop already-expired jobs before handing one out.
    this.queue = this.queue.filter(
      (j) => Date.now() - (j.queued_at || 0) < CLIENT_WAIT_MS);
    const job = this.queue.shift();
    if (job) return jsonResponse(job);
    // Hold the poll open until a job lands or the window closes.
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        if (this.agentWaiter && this.agentWaiter.resolve === resolve) {
          this.agentWaiter = null;
        }
        resolve(new Response(null, { status: 204 }));
      }, AGENT_POLL_MS);
      // A newer poll supersedes a stale one (connector restarted).
      if (this.agentWaiter) {
        clearTimeout(this.agentWaiter.timer);
        this.agentWaiter.resolve(new Response(null, { status: 204 }));
      }
      this.agentWaiter = { resolve, timer };
    });
  }

  async agentReply(request, url) {
    const reqId = url.searchParams.get("req");
    const entry = this.pending.get(reqId);
    if (!entry) return jsonResponse({ error: "no such pending request" }, 404);
    this.pending.delete(reqId);
    clearTimeout(entry.timer);
    let payload;
    try {
      payload = await request.json();
    } catch (e) {
      entry.resolve(jsonResponse({ error: "bad reply from agent" }, 502));
      return jsonResponse({ ok: false }, 400);
    }
    const body = payload.body_b64 ? b64decode(payload.body_b64) : null;
    entry.resolve(new Response(body, {
      status: payload.status || 200,
      headers: { "Content-Type": payload.content_type || "application/json" },
    }));
    return jsonResponse({ ok: true });
  }

  // ── phone side ──────────────────────────────────────────────────────────
  async clientForward(request, url) {
    const reqId = String(this.nextId++);
    const bodyBuf = ["GET", "HEAD"].includes(request.method)
      ? null
      : await request.arrayBuffer();
    const job = {
      req_id: reqId,
      method: request.method,
      path: url.pathname + url.search, // already stripped to the local path
      authorization: request.headers.get("Authorization") || "",
      content_type: request.headers.get("Content-Type") || "",
      body_b64: bodyBuf && bodyBuf.byteLength ? b64encode(bodyBuf) : "",
    };

    const responsePromise = new Promise((resolve) => {
      const timer = setTimeout(() => {
        this.pending.delete(reqId);
        resolve(jsonResponse(
          { error: "Mac connector not responding (is it running?)" }, 504));
      }, CLIENT_WAIT_MS);
      this.pending.set(reqId, { resolve, timer });
    });

    if (this.agentWaiter) {
      const w = this.agentWaiter;
      this.agentWaiter = null;
      clearTimeout(w.timer);
      w.resolve(jsonResponse(job));
    } else {
      // Stamp + cap the backlog: when the connector is away, an open phone
      // page queues a job every few seconds. Old jobs are pointless (their
      // pending entry expires after CLIENT_WAIT_MS) — keep only the fresh
      // tail so a returning connector doesn't drain garbage.
      job.queued_at = Date.now();
      this.queue = this.queue.filter(
        (j) => Date.now() - (j.queued_at || 0) < CLIENT_WAIT_MS);
      if (this.queue.length >= 20) this.queue.shift();
      this.queue.push(job);
    }
    return responsePromise;
  }
}

// ── worker router ───────────────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/healthz") return jsonResponse({ ok: true });

    // Connector endpoints: /agent/poll?id=<rid>, /agent/reply?id=<rid>&req=N
    if (url.pathname.startsWith("/agent/")) {
      if (request.headers.get("X-Relay-Key") !== env.RELAY_KEY) {
        return jsonResponse({ error: "bad relay key" }, 401);
      }
      const rid = url.searchParams.get("id");
      if (!rid) return jsonResponse({ error: "id required" }, 400);
      return sessionStub(env, rid).fetch(request);
    }

    // Phone endpoints: /c/<rid>/<local path...>
    const m = url.pathname.match(/^\/c\/([A-Za-z0-9_-]{16,})(\/.*)?$/);
    if (m) {
      const rid = m[1];
      const localPath = m[2] || "/";
      // Rewrite so the DO sees the LOCAL path the Mac should serve.
      const fwd = new URL(url);
      fwd.pathname = localPath;
      return sessionStub(env, rid).fetch(new Request(fwd, request));
    }

    return jsonResponse({ error: "not found" }, 404);
  },
};

function sessionStub(env, rid) {
  return env.SESSIONS.get(env.SESSIONS.idFromName(rid));
}

function jsonResponse(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function b64encode(buf) {
  let s = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s);
}

function b64decode(s) {
  const bin = atob(s);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}
