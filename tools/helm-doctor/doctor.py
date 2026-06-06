#!/usr/bin/env python3
"""helm-doctor: diagnose your Helm setup"""
import os, pathlib, subprocess, sys

HOME = pathlib.Path.home()
passed = []
failed = []
warn = []

def check(name, condition, fix=""):
    if condition: passed.append(name)
    else: failed.append((name, fix))

def warn_check(name, condition, msg=""):
    if not condition: warn.append((name, msg))

# Helm.app
check("Helm.app installed", (pathlib.Path("/Applications/Helm.app")).exists(),
      "Build from source: PROFILE=debug ./scripts/build.sh --app-only")

# Master memory
check("~/.kiro/AGENTS.md exists", (HOME/".kiro/AGENTS.md").exists(),
      "Run: bash tools/helm-init/helm-init.sh")

# Symlinks
for harness, path in [
    ("claude-code", HOME/".claude/CLAUDE.md"),
    ("opencode",    HOME/".config/opencode/AGENTS.md"),
    ("codex",       HOME/".codex/AGENTS.md"),
]:
    is_link = path.is_symlink()
    points_right = is_link and os.readlink(path) == str(HOME/".kiro/AGENTS.md")
    check(f"symlink {harness}", points_right,
          f"ln -sf ~/.kiro/AGENTS.md {path}")

# Tools on PATH
for tool in ["kiro-cli", "opencode"]:
    check(f"{tool} on PATH",
          subprocess.run(["which", tool], capture_output=True).returncode == 0,
          f"Install {tool}")

# helm session dir
check("~/.helm/ exists", (HOME/".helm").exists(), "mkdir -p ~/.helm/sessions")

# Print results
print("\nHelm Doctor")
print("===========")
for p in passed: print(f"  ✓ {p}")
for f, fix in failed:
    print(f"  ✗ {f}")
    if fix: print(f"    → {fix}")
for w, msg in warn:
    print(f"  ⚠ {w}: {msg}")
print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(0 if not failed else 1)
