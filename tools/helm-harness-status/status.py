#!/usr/bin/env python3
"""helm-harness-status: check which AI harnesses are installed"""
import subprocess, pathlib, os

HOME = pathlib.Path.home()

harnesses = [
  {"name": "kiro",         "cmd": "kiro-cli",  "memory": HOME/".kiro/AGENTS.md",           "session_dir": HOME/".kiro/sessions"},
  {"name": "claude-code",  "cmd": "claude",    "memory": HOME/".claude/CLAUDE.md",          "session_dir": HOME/".claude/projects"},
  {"name": "opencode",     "cmd": "opencode",  "memory": HOME/".config/opencode/AGENTS.md", "session_dir": HOME/".local/share/opencode/storage"},
  {"name": "codex",        "cmd": "codex",     "memory": HOME/".codex/AGENTS.md",           "session_dir": None},
  {"name": "aider",        "cmd": "aider",     "memory": None,                              "session_dir": None},
]

print("Helm Harness Status")
print("===================")
print(f"  {'harness':<14} {'installed':<12} {'memory linked':<16} {'sessions'}")
print(f"  {'-'*14} {'-'*12} {'-'*16} {'-'*10}")

for h in harnesses:
  installed = subprocess.run(["which", h["cmd"]], capture_output=True).returncode == 0
  mem_path = h["memory"]
  if mem_path:
    mem_ok = mem_path.is_symlink() and os.readlink(str(mem_path)) == str(HOME/".kiro/AGENTS.md")
    mem_str = "✓ linked" if mem_ok else ("⚠ exists" if mem_path.exists() else "✗ missing")
  else:
    mem_str = "n/a"

  sess_count = 0
  if h["session_dir"] and pathlib.Path(h["session_dir"]).exists():
    try: sess_count = sum(1 for _ in pathlib.Path(h["session_dir"]).rglob("*.json"))
    except: pass

  inst_str = "✓ yes" if installed else "✗ no"
  print(f"  {h['name']:<14} {inst_str:<12} {mem_str:<16} {sess_count} json files")
