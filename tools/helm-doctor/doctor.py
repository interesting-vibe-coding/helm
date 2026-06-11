#!/usr/bin/env python3
"""kaji doctor — is this boat seaworthy?

Checks the v0.6 reality: the app, the harnesses, the Brain service, the
relay, and the quota sources. Every ✗ comes with the exact fix command.
Exit 0 = all required checks pass (warnings allowed).
"""
import os
import pathlib
import shutil
import subprocess
import sys
import urllib.request

HOME = pathlib.Path.home()
CFG = HOME / ".config" / "helm"

SUN = "\033[38;2;242;92;5m"
DIM = "\033[38;2;138;129;116m"
RST = "\033[0m"

rows = []           # (kind, name, fix) — kind ∈ ok / fail / warn


def ok(name):
    rows.append(("ok", name, ""))


def fail(name, fix):
    rows.append(("fail", name, fix))


def warn(name, fix=""):
    rows.append(("warn", name, fix))


def check(name, cond, fix):
    ok(name) if cond else fail(name, fix)


def http_get(url, timeout=4):
    try:
        req = urllib.request.Request(url)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except Exception:
        return None, b""


def launchd_loaded(label):
    out = subprocess.run(["launchctl", "list"], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL).stdout.decode()
    return label in out


# ── the app ──────────────────────────────────────────────────────────────────
check("Kaji.app installed", pathlib.Path("/Applications/Kaji.app").exists(),
      "curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/kaji/main/install.sh | bash")

# ── harnesses ────────────────────────────────────────────────────────────────
extra = ["/opt/homebrew/bin", "/usr/local/bin", str(HOME / ".local/bin")]
env_path = os.environ.get("PATH", "") + ":" + ":".join(extra)
found = {h: bool(shutil.which(h, path=env_path))
         for h in ("claude", "codex", "kiro-cli", "opencode")}
if found["claude"] or found["codex"]:
    ok("harness on PATH (%s)" % ", ".join(k for k, v in found.items() if v))
else:
    fail("no harness found", "install one: npm i -g @anthropic-ai/claude-code  (or codex)")
if not found["claude"]:
    warn("claude missing", "the helm-line planner uses it as fallback — npm i -g @anthropic-ai/claude-code")

# ── brain service ────────────────────────────────────────────────────────────
tok = CFG / "brain-token"
check("brain token", tok.exists() and tok.read_text().strip() != "",
      "head -c 24 /dev/urandom | xxd -p > ~/.config/helm/brain-token && chmod 600 ~/.config/helm/brain-token")
check("serve LaunchAgent", launchd_loaded("dev.kaji.brain-serve"),
      "see docs/remote.md — install dev.kaji.brain-serve.plist, or run: kaji-brain serve")
st, _ = http_get("http://127.0.0.1:8787/healthz")
check("serve answering on :8787", st == 200,
      "launchctl kickstart -k gui/$(id -u)/dev.kaji.brain-serve")

# ── relay (optional but recommended) ─────────────────────────────────────────
rid = CFG / "relay-id"
if rid.exists():
    ok("relay paired (id %s…)" % rid.read_text().strip()[:6])
    check("relay connector LaunchAgent", launchd_loaded("dev.kaji.relay-connector"),
          "launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.kaji.relay-connector.plist")
else:
    warn("relay not set up", "phone access from anywhere — see docs/remote.md, then: kaji-brain qr")

# ── quota sources ────────────────────────────────────────────────────────────
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "helm-quota"))
try:
    import quota
    if found["claude"]:
        check("claude OAuth token (live limits)", bool(quota._claude_oauth_token()),
              "run `claude` once and sign in — limits stay blank without it")
    if found["codex"]:
        sess = HOME / ".codex" / "sessions"
        check("codex session files (quota)", sess.exists(),
              "run `codex` once — quota reads its rollout files")
except Exception as e:  # noqa: BLE001
    warn("quota module unreadable: %s" % e)

# ── report ───────────────────────────────────────────────────────────────────
color = sys.stdout.isatty()


def c(txt, code):
    return (code + txt + RST) if color else txt


print()
print(" " + c("◉ ", SUN) + "kaji doctor")
print()
bad = 0
for kind, name, fix in rows:
    if kind == "ok":
        print("   " + c("●", DIM) + " " + name)
    elif kind == "warn":
        print("   " + c("△ " + name, DIM))
        if fix:
            print("     " + c("→ " + fix, DIM))
    else:
        bad += 1
        print("   " + c("✗ " + name, SUN))
        if fix:
            print("     " + c("→ " + fix, DIM))
print()
print("   " + c("seaworthy ⚓" if bad == 0 else "%d check(s) need attention" % bad,
                DIM if bad == 0 else SUN))
print()
sys.exit(0 if bad == 0 else 1)
