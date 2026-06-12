# Changelog

All notable changes to Kaji are documented here.
Format: [version] - date - description

## [0.6.7] - 2026-06-13

### The quiet fixes release (#195, #196, #198, #199)
- **CLI stack overflow fixed** (#195) — every `helm cli` call tripped
  a "C stack overflow" inside the Lua module bootstrap: the deferred
  setup hook re-entered itself through non-raw module lookups. The
  hook now detaches before it runs. First release to carry the fix in
  the binary.
- **Settings TUI wears Kaji** (#198) — the TUI chrome palette syncs
  to Kaji Ember / Kaji Sun (the old Kaku purple and Flexoki paper
  retire), and the 'Kaji Ember' / 'Kaji Sun' scheme names are
  recognized alongside the legacy ones.
- **The phone page fits the phone** (#196) — the quota strip wraps
  per harness instead of running off the right edge at iPhone widths,
  and long project names ellipsize so the status column always shows.
- **README hero re-shot to brand** (#199) — the mate speaks as ◉, the
  rudder stays at the helm line, transcript in English.

## [0.6.6] - 2026-06-13

### The terminal wears its own face (#190, #192, #193)
- **Kaji Ember / Kaji Sun terminal schemes** (#192) — the ported Kaku
  palettes retire. Night is ember black (#16100b, warm, never pure)
  with candle-lit cream and a warm-shifted ANSI sixteen; day is paper
  (#fbf8f2) with warm ink. Window frame, tab bar, and compass follow,
  so the shell, the cockpit, and the phone finally share one face.
- **One mark, one meaning** (#193) — KAJI is the wordmark in the
  header; the wheel (◉) is the product's voice in the transcript; 舵
  marks only the helm line you type into. The design doc
  (KAJI_EMBER.md v2) now carries the shipped tokens and the rule.
- **English to the edges** (#190) — residual Chinese in comments,
  docstrings, smoke prompts, and dialogue fixtures moves to English;
  the 舵 brand mark and load-bearing CJK fixtures stay.

## [0.6.5] - 2026-06-12

### Design pass: persimmon energy, Japanese restraint (#185, #187)
- **Cockpit alignment** (#185) — quota hugs the right edge of the
  header (the old pad was computed and never used); per-row meta
  right-aligns into a clean column; the footer gets symmetric rules
  and the hint line recedes to ash; transcript rendering deduped.
- **Phone dark scheme: Kaji Ember** (#185) — warm ember black
  (#16100b, never pure black) behind the same persimmon; peek and the
  brand mark recolor via CSS vars / currentColor; theme-color meta for
  both schemes; plan chips speak human ("claude · kaji", not
  "pane 12").
- **Top bar fixed for good** (#187) — every config reload rebuilds the
  Lua VM and silently dropped all six event handlers (tab titles fell
  back to truncated cwd, the compass froze). The registration guard
  now lives on the per-eval module table, so handlers re-register on
  every reload.
- **Purple retired** (#187) — cursor, selection, and the compass
  accent now use the one persimmon (#f25c05) in both themes; the only
  purple left is the semantic ANSI palette.

## [0.6.4] - 2026-06-12

### Hardening from the live acceptance round (#176–#183)
- **Quota in the top bar** (#179) — the Claude five-hour percent sits in
  the right status, persimmon at >=80%; read from the disk cache, zero
  API calls from Lua.
- **Engine backends benched** (#178) — github gpt-4.1-mini (8/8, median
  6.7s, free via the gh token) is the default dispatcher; openrouter
  and oauth fall back; local ollama stays an explicit opt-in.
- **TLS downgrade guard** (#176) — a proxy node that forwards HTTPS as
  plain HTTP now aborts the call immediately instead of re-leaking the
  key on retries.
- **Acceptance-round fixes** (#181, #182, #183) — the mate grounds ~ in
  the captain's real home (no more /home/user spawns); the conversation
  survives an empty fleet; the frame repaints before a turn; the phone
  auth gate actually gates (inline display defeated the hidden attr).
- **Unified quota, first cut** (#177) — per-project context usage in
  /api/state, phone rows enumerate harnesses dynamically, atomic cache
  writes.

## [0.6.3] - 2026-06-12

### Our own engine at the helm (#169–#174)
- **Conversational First Mate** (#169) — the helm line now drives our own
  tool-use engine (stdlib, no harness shell): it converses, reads the
  fleet itself, and yields spawn/send to the cockpit's confirm gate
  (run / cancel / edit) or auto mode.
- **Free-model dispatch** (#169) — OpenRouter `:free` model by default
  (strong tool use, 262K ctx, $0), sticky fallback to Claude haiku;
  proxy-only transport with same-path retries.
- **Minimal cockpit** (#171) — the conversation is the body: per-pane
  event feed and compass dots removed; the fleet list and the dialogue
  are the whole screen.
- **Peek from the phone** (#172) — tap a session, see its live screen
  (`kaji-brain peek`, `GET /api/peek`, 3s refresh while open).
- **English-first surface** (#174) — hints, selector, engine replies,
  mobile labels, landing copy; the 舵 glyph stays as the brand mark.
- Fixes: CJK characters split across reads no longer drop (#170);
  ^C exits cleanly from anywhere (#174); README/demo re-recorded
  against the real engine (#173).
- Worker registration at spawn (#168) — codex's node shim defeated
  process detection; sessions now self-register in runtime state.

## [0.6.2] - 2026-06-12

### The helm line everywhere (overnight sprint, #157–#166)
- **Phone helm line** (#157) — `POST /api/plan` + plan card with
  执行 / 取消 / 改一改 chips; same grammar as the desktop cockpit.
- **Planner 9s → ~2.5s** (#158) — direct /v1/messages (Claude Code OAuth
  token + haiku) with CLI fallback; prompt hardened (chatter → none,
  imperative send text, real ~/workspace project dirs fed in).
- **QR pairing** (#161) — `kaji-brain qr [--rotate] [out.png]`; the token
  rides the URL #fragment (never reaches the relay server).
- **`kaji-brain doctor`** (#164) — v0.6 seaworthiness check, every ✗ with
  its exact fix command.
- **Tap-for-history on mobile** (#165) — second tap on a session expands
  its last five events inline.
- **focus_pane really focuses** (#159) — compass/keyboard no longer stick
  to the Brain after a switch.
- **Animated README demo** (#162, vhs) + **landing page** (#163) —
  https://kaji.doabit.dev (GitHub Pages + CNAME, HTTPS enforced).

## [0.6.1] - 2026-06-11

- Typing-first hardening from live dogfood (#156): letters never trigger
  commands (quit = Ctrl-C), waiting-notifications no longer leak into the
  舵 input, planner maps project names to real ~/workspace dirs.

## [0.6.0] - 2026-06-11

### Kaji Sun — the terminal wears its own design
- **Sun day/night palettes everywhere** (#143, #145, #146, #150) — paper/ink/
  persimmon visual language: cockpit TUI, mobile page, README hero shot.
  Night = warm cream on charcoal; persimmon means ONE thing: needs you.
- **New mark** (#152) — ink wheel + persimmon spoke (logo / README / app icon).
- **Two views only** (#149) — Cmd+/ flips Mission Control ⇄ Work; Cmd+1/2/4
  retired (Terminal slot → Cmd+T). Top bar always shows where Cmd+/ goes.
- **Brain view = our own cockpit** (#147) — the Sun TUI replaces the
  claude-code shell as the default Brain (BRAIN_HARNESS=claude to revert).
- **Instant paint** (#150) — first frame in ~35ms; data loads behind a
  skeleton; refreshes are async (no more 1s blank).

### The helm line — say it, don't type forms
- **NL dispatch** (#151, #153) — type directly into the cockpit (no prefix):
  one sentence → planner (claude -p sonnet) → {send|spawn} plan → arrow-key
  confirm (执行/取消/改一改) or auto mode (Tab / Cmd+Shift+A toggles).

### Authoritative quota + per-session context
- **Dual-window limits** (#144, #145) — claude oauth usage API + codex
  app-server: 5h/weekly used% on cockpit, status bar, phone.
- **Per-session ctx%** (#145) — each session shows how full its context
  window is (e.g. ctx 18%).

### Fixes
- **Relay stale-job loop** (#148) — an offline connector + an open phone page
  self-sustained a 404 loop; connector now skips expired jobs, worker prunes
  its queue. Lint's plist check now runs on ubuntu (plutil → plistlib).
- **Spawn placement + codex detection** (#153) — Cmd+Shift+K anchors workers
  in the Work area (never beside the Brain); codex (a node shim) is now
  detected via argv; codex spawn tasks submit reliably (boot-wait + CR).

## [0.5.0] - 2026-06-11

### Remote — steer the fleet from anywhere
- **Self-hosted thin relay** (#128) — CF Worker + Durable Object long-poll;
  Mac dials out (no inbound ports), phone talks plain HTTPS at
  `relay.doabit.dev/c/<id>/`. Reachable from China direct AND behind proxies
  (workers.dev is SNI-blocked direct → custom domain on the same edge).
- **Mobile cockpit v2** (#124, #130) — deep-luxury restyle, spawn-a-worker
  sheet, per-worker timeline, desktop two-column grid; served at `/` by
  `kaji-brain serve`, same page over tailnet/Funnel/relay.
- **Tailscale + Funnel paths documented** (#122, #127) with prior-art research
  (Anthropic RC / Omnara / Happy).

### Fleet correctness & quota
- **Stale-fleet fix** (#126, fixes #125) — live-socket resolution for every
  mux call; mux down now means an empty fleet (no phantom sessions); failed
  sends surface as errors on the phone.
- **Codex real quota** (#131) — tokens today + `rate_limits.used_percent`
  + plan from local session files; `/api/state` carries `limits`; cockpit
  chips show "% left".
- **Spawn PATH fix** (#135) — harness binaries resolved to absolute paths
  (GUI PATH lacks /opt/homebrew/bin → "No viable candidates" from the phone).

### Brain & cockpit
- **First Mate wired to the kaji-brain MCP server** (#136) — typed tools
  (list_sessions / spawn_worker / send_to_worker / …), engine-agnostic;
  CLI stays as fallback. Verified live with a headless client.
- **Interactive TUI cockpit** (#132) — ↑↓ select, ⏎ send, s spawn, q quit;
  writes go through the same CLI/HTTP spine as every client.
- **`helm-brain` → `kaji-brain` rename** (#121).

### Infra
- **CI lightened** (#135) — real path filter for the 5-min Cargo Check
  (docs/python PRs now merge in ~1 min); lint on ubuntu.
- README rework, bilingual (#134); project progress now lives in
  `docs/PROGRESS.md` (#129, #133).

## [0.4.0] - 2026-06-09

### Brand
- **Renamed Helm → Kaji** (#109–#112): new logo, README rewrite (philosophy /
  features / thanks), i18n READMEs, bundle id `dev.kaji.app`, rename regression
  guards in CI.

### Agent loop
- **Core agent loop verified end-to-end** — spawn worker → Monitor (helm-top)
  lists it → worker hits *waiting* → Brain `notify` fires → session restore
  after restart. The long-standing ROADMAP P0 is now confirmed working.
- **4-view shell** — Cmd+1 Brain · Cmd+2 Work · Cmd+3 Monitor · Cmd+4 Terminal,
  with a dynamic dot-compass; per-view Cmd+W close semantics (#95).
- **Brain session-tracking crash fixed** — `helm-brain track` called
  `table.concat` on a String, erroring every tick on any agent pane (#96).

### Theming
- **Kaku Light / Auto fully adapted** (#97) — Light palette + appearance
  resolve; theme-aware window_frame / tab_bar / status compass; settings TUI
  (`helm config`) recovers theme intent from the config file when
  `color_scheme` is unevaluated; legible Claude text on cream.
- **Blank tab titles** — compass is the single source of tab identity; engine no
  longer leaks the pane cwd (`Users/Users/Users/`) (#101).

### Upstream Kaku ports
- #448 scroll snap-to-bottom (#101), #446/#450 powerline separators keep their
  color (#102), #449 Cmd+Q close-confirmation scoped to the foreground process
  group (#103), #452 repaint after resize + suppress phantom cold-start window
  (#104).

### CI
- Scroll regression tests wired into Cargo CI (#94).
- Path-filtered cargo job + lint/brand guards; README badges (#110, #113).
- **Release workflow** — tag `v*` builds and publishes the macOS .app on a
  GitHub macОS runner (ad-hoc signed; no local Mac required).

### Isolation
- **Kaji ⟂ Kaku confirmed** — distinct bundle id, config dirs, bundled binary;
  Kaku.app untouched.

## [0.3.2] - 2026-06-07

### Fixed
- Installer now seeds config on fresh install (was a bare terminal otherwise).
  Debt cleanup.

## [0.3.1] - 2026-06-07

### Added
- First-run onboarding now actually runs on first launch (animated ghost +
  Choose-your-Brain harness picker), then drops into the Brain.

## [0.3.0] - 2026-06-07

### Added
- **The Brain (First Mate orchestrator)** — Sonnet orchestrator that watches
  workers, reports only what needs you, and can spawn worker sessions.
- **3-view shell** — Cmd+1 Brain · Cmd+2 Workspace · Cmd+3 Monitor (htop-style).
- **Boot into the Brain** + session restore (rebuilds last run's panes).
- **htop-style Monitor**, animated ghost onboarding, ghost logo.

## [0.2.0] - 2026-06-07

### Added (Agent OS features)
- **Session Scheduler**: LRU-based session virtualization. Cmd+Shift+B to background.
- **Harness Launcher**: Cmd+Shift+K to spawn kiro/claude-code/opencode/codex in new pane.
- **Agent Notifications**: macOS notifications when agent needs input. Cmd+Shift+U to jump to waiting agent.
- **Session List**: Cmd+Shift+S to view all active sessions with runtime and state.
- **Model Toggle**: Cmd+Shift+M to switch between claude-sonnet-4.6 and claude-opus-4.8.
- **Project-aware naming**: Tab bar shows `🔵 kiro:projectname (MM:SS)`.
- **Window title**: Shows `Helm — N agents (M waiting)` when agents are active.
- **Session persistence**: Sessions saved to ~/.helm/sessions/runtime.json across restarts.
- **Cross-harness memory**: AGENTS.md symlinked to claude-code, opencode, codex automatically.

### Tools Added
- `helm-history`: Index and search chat history across all harnesses (282+ sessions).
- `helm-status`: Unified dashboard with sessions, symlinks, build status.
- `helm-watch`: Live session monitor (htop for agents).
- `helm-quota`: Per-harness usage awareness.
- `helm-telemetry`: Local-only usage metrics.
- `helm-init`: One-shot setup script.
- `helm-doctor`: Diagnose setup issues.
- `helm-harness-status`: Check which harnesses are installed.
- `helm-session-replay`: Export past session as context for new agent.

### Paper
- Draft submitted to IUI 2027 (target). Sections: Abstract, Introduction, Related Work, System Design, Implementation, User Study, Evaluation.
- UIST 2026 Demo abstract ready (deadline Jul 10, 2026).
- HAI 2026 Osaka poster/demo planned (deadline Aug 7, 2026).

## [0.1.0] - 2026-06-06

### Added
- Fork of Kaku (WezTerm) with Helm branding (dev.helm.app).
- Interactive first_run.sh: shell detection, required tools, optional tools.
- Helm logo: geometric gold helm wheel icon.
- CI: macos-latest runner + luac syntax check.
