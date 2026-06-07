local wezterm = require 'wezterm'

local function resolve_bundled_config()
  local resource_dir = wezterm.executable_dir:gsub('MacOS/?$', 'Resources')
  local bundled = resource_dir .. '/kaku.lua'
  local f = io.open(bundled, 'r')
  if f then
    f:close()
    return bundled
  end

  local dev_bundled = wezterm.executable_dir .. '/../../assets/macos/Kaku.app/Contents/Resources/kaku.lua'
  f = io.open(dev_bundled, 'r')
  if f then
    f:close()
    return dev_bundled
  end

  local app_bundled = '/Applications/Kaku.app/Contents/Resources/kaku.lua'
  f = io.open(app_bundled, 'r')
  if f then
    f:close()
    return app_bundled
  end

  local home = os.getenv('HOME') or ''
  local home_bundled = home .. '/Applications/Kaku.app/Contents/Resources/kaku.lua'
  f = io.open(home_bundled, 'r')
  if f then
    f:close()
    return home_bundled
  end

  return nil
end

local config = {}
local bundled = resolve_bundled_config()

if bundled then
  local ok, loaded = pcall(dofile, bundled)
  if ok and type(loaded) == 'table' then
    config = loaded
  else
    wezterm.log_error('Kaku: failed to load bundled defaults from ' .. bundled)
  end
else
  wezterm.log_error('Kaku: bundled defaults not found')
end

-- Kaku follows macOS appearance by default. Uncomment one line to force a theme:
-- config.color_scheme = 'Kaku Dark'
-- config.color_scheme = 'Kaku Light'

-- User overrides:
-- Kaku intentionally keeps WezTerm-compatible Lua API names
-- for maximum compatibility, so `wezterm.*` here is expected.
-- Full API docs: https://wezfurlong.org/wezterm/config/lua/
--
-- 1) Font family and size
-- config.font = wezterm.font('JetBrains Mono')
-- config.font_size = 16.0
-- config.line_height = 1.2
--
-- 2) Color scheme
-- config.color_scheme = 'Catppuccin Mocha'
--
-- 3) Window size and padding
-- config.initial_cols = 120
-- config.initial_rows = 30
-- config.window_padding = { left = '24px', right = '24px', top = '40px', bottom = '20px' }
--
-- 4) Window transparency and blur
-- config.window_background_opacity = 0.95
-- config.macos_window_background_blur = 20
--
-- 5) Copy on select
-- config.copy_on_select = false
--
-- 6) Default shell/program
-- config.default_prog = { '/bin/zsh', '-l' }
--
-- 7) Cursor and scrollback
-- config.default_cursor_style = 'BlinkingBar'
-- config.cursor_blink_rate = 500
-- config.scrollback_lines = 20000
--
-- 8) Tab bar
-- config.hide_tab_bar_if_only_one_tab = true
-- config.tab_bar_at_bottom = true
-- config.tab_title_show_basename_only = true
--
-- 9) Working directory inheritance
-- config.window_inherit_working_directory = true
-- config.tab_inherit_working_directory = true
-- config.split_pane_inherit_working_directory = true
--
-- 10) Split pane
-- config.split_pane_gap = 2
-- config.inactive_pane_hsb = { saturation = 1.0, brightness = 0.9 }
--
-- 11) Add or override a key binding
-- table.insert(config.keys, {
--   key = 'Enter',
--   mods = 'CMD|SHIFT',
--   action = wezterm.action.TogglePaneZoomState,
-- })

config.color_scheme = 'Kaku Dark'
config.window_decorations = 'INTEGRATED_BUTTONS|RESIZE'
config.font_size = 16

-- ════════════════════════════════════════════════════════════
-- Paws 🐾 — terminal companion (fully native, no external scripts)
-- The game lives in its OWN TAB (full-window, never disturbs your panes).
--   CMD+G        : open the game tab (centered menu) ↔ toggle back to agent
--   CMD+SHIFT+P  : close the game tab and re-open the menu
-- Manual switching only. A session-status HUD (in the game) shows which agents
-- are running vs done, so you decide when to flip back — no auto-jumping.
-- ════════════════════════════════════════════════════════════
local PAWS_SHELL = os.getenv('SHELL') or '/bin/sh'  -- login shell, so PATH resolves

-- wezterm.mux.get_tab raises if the tab is gone; make it return nil instead
local function paws_tab(tab_id)
  if not tab_id then return nil end
  local ok, t = pcall(wezterm.mux.get_tab, tab_id)
  return ok and t or nil
end

-- spawn the game tab running the `paws` menu; remember the agent tab; activate it
local function paws_spawn(window, agent_tab_id)
  if agent_tab_id then wezterm.GLOBAL.paws_agent_tab = agent_tab_id end
  local tab = window:mux_window():spawn_tab { args = { PAWS_SHELL, '-l', '-c', 'paws' } }
  wezterm.GLOBAL.paws_game_tab = tab:tab_id()
  tab:activate()
end

config.keys = config.keys or {}
-- CMD+G: open the game tab (centered menu) / toggle agent <-> game
table.insert(config.keys, {
  key = 'g',
  mods = 'CMD',
  action = wezterm.action_callback(function(window, pane)
    local game = paws_tab(wezterm.GLOBAL.paws_game_tab)
    if game then
      if pane:tab():tab_id() == wezterm.GLOBAL.paws_game_tab then
        local at = paws_tab(wezterm.GLOBAL.paws_agent_tab)
        if at then at:activate() end
      else
        game:activate()
      end
      return
    end
    paws_spawn(window, pane:tab():tab_id())
  end),
})
-- CMD+SHIFT+P: close any open game tab and re-open the menu
table.insert(config.keys, {
  key = 'P',
  mods = 'CMD|SHIFT',
  action = wezterm.action_callback(function(window, pane)
    local agent_id = wezterm.GLOBAL.paws_agent_tab or pane:tab():tab_id()
    local old = paws_tab(wezterm.GLOBAL.paws_game_tab)
    if old then
      old:activate()
      window:perform_action(wezterm.action.CloseCurrentTab { confirm = false }, old:active_pane())
    end
    paws_spawn(window, agent_id)
  end),
})
-- CMD+H: open the Paws repo (file an issue, say hi)
table.insert(config.keys, {
  key = 'h',
  mods = 'CMD',
  action = wezterm.action_callback(function()
    os.execute("open 'https://github.com/MisterBrookT/paws'")
  end),
})

config.restore_previous_session = true

-- ════════════════════════════════════════════════════════════
-- Helm 🎯 — agent-native terminal layer (on top of WezTerm/Kaku)
-- Organized as one namespace; sub-tables map to the 3 layers.
-- To add a harness: add a row to Helm.harnesses.list
-- To add a keybind:  add to Helm.keys.bind(config)
-- ════════════════════════════════════════════════════════════
local Helm = {}

-- Ghost glyph: placeholder logo for the bottom status bar (swap for a custom
-- mark later). Used at the head of the LEFT zone.
Helm.GHOST = '👻'

-- ── Tuning constants ────────────────────────────────────────
--   IDLE_THRESHOLD : secs of stable pane content before a session is 'waiting'
--   LRU_LIMIT      : max sessions shown in the Cmd+Shift+S overlay (most-recent first)
--   FP_LINES       : trailing lines hashed for the content-change fingerprint
--   RUNTIME_JSON   : where session state is persisted across restarts
Helm.cfg = {
  IDLE_THRESHOLD = 3,
  LRU_LIMIT      = 6,
  FP_LINES       = 12,
  RUNTIME_JSON   = (os.getenv('HOME') or '/tmp') .. '/.helm/sessions/runtime.json',
}

-- ════════════════════════════════════════════════════════════
-- Layer 0: harness registry (single source of truth)
-- Both detect() (process-name → display label) and the Cmd+Shift+K
-- launcher derive from this one list. To add a harness, add one row.
--   match  : substring matched against the foreground process name
--   name   : display label used in tab titles / HUD
--   cmd    : command run by the launcher
--   label  : menu label shown in the launcher
--   resume : (optional) flag appended on session-rebuild to resume the last
--            conversation in that cwd. Only set where the harness supports it.
-- ════════════════════════════════════════════════════════════
Helm.harnesses = {}
Helm.harnesses.list = {
  { match = 'kiro',     name = 'Kiro',     cmd = 'kiro-cli chat --trust-all-tools --agent default --effort medium', label = '🤖 kiro  (default, medium effort)' },
  { match = 'claude',   name = 'Claude',   cmd = 'claude --dangerously-skip-permissions', resume = '--continue',    label = '🟣 claude-code  (auto-approve)' },
  { match = 'opencode', name = 'opencode', cmd = 'opencode',                                                        label = '⚡ opencode' },
  { match = 'codex',    name = 'Codex',    cmd = 'codex',                                                           label = '🔵 codex' },
}

-- Resolve the launch command for a harness by its display name. When `resume`
-- is true and the harness declares a resume flag, append it so the previous
-- conversation in that cwd comes back; otherwise relaunch clean. Returns nil
-- for unknown harnesses.
function Helm.harnesses.spawn_cmd(name, resume)
  if not name then return nil end
  for _, h in ipairs(Helm.harnesses.list) do
    if h.name == name then
      if resume and h.resume then return h.cmd .. ' ' .. h.resume end
      return h.cmd
    end
  end
  return nil
end

-- process name → harness display name (nil if unknown)
function Helm.harnesses.detect(process_name)
  if not process_name then return nil end
  local base = (process_name:match('([^/]+)$') or process_name):lower()
  for _, h in ipairs(Helm.harnesses.list) do
    if base:find(h.match, 1, true) then return h.name end
  end
  return nil
end

-- launcher choices derived from the list (id = command to exec)
function Helm.harnesses.choices()
  local out = {}
  for _, h in ipairs(Helm.harnesses.list) do
    table.insert(out, { id = h.cmd, label = h.label })
  end
  return out
end

-- ── Utilities ───────────────────────────────────────────────
Helm.util = {}

function Helm.util.now()
  return tonumber(wezterm.strftime('%s')) or 0
end

function Helm.util.cwd_basename(cwd_url)
  if not cwd_url then return '?' end
  local path = tostring(cwd_url)
  -- strip file:// prefix
  path = path:gsub('^file://[^/]*', '')
  -- strip trailing slash
  path = path:gsub('/$', '')
  return path:match('([^/]+)$') or path
end

-- Full filesystem path of a cwd Url (strips file://host prefix + trailing slash).
-- Returns nil when unavailable — used to rebuild a session in its real dir.
function Helm.util.cwd_path(cwd_url)
  if not cwd_url then return nil end
  local path = tostring(cwd_url)
  path = path:gsub('^file://[^/]*', '')
  path = path:gsub('/$', '')
  if path == '' then return nil end
  return path
end

function Helm.util.fmt_duration(secs)
  local s = math.floor(secs)
  return string.format('%02d:%02d:%02d', math.floor(s/3600), math.floor((s%3600)/60), s%60)
end

-- Compact runtime for the status bar: 45s / 2m34s / 1h12m
function Helm.util.fmt_short(secs)
  local s = math.floor(secs)
  if s < 60 then return s .. 's' end
  if s < 3600 then return math.floor(s/60) .. 'm' .. (s % 60) .. 's' end
  return math.floor(s/3600) .. 'h' .. math.floor((s % 3600)/60) .. 'm'
end

-- ════════════════════════════════════════════════════════════
-- Layer 1: Session Scheduler
-- State lives in wezterm.GLOBAL.helm_sessions so it survives reloads:
--   helm_sessions[pane_id] = { harness, cwd, start_time, last_accessed, state, fp, last_change }
-- ════════════════════════════════════════════════════════════
Helm.sessions = {}

-- internal: serialize the session table to JSON
local function sessions_to_json(sessions)
  local parts = {}
  for id, s in pairs(sessions) do
    local entry = string.format(
      '"%s":{"harness":%q,"cwd":%q,"cwd_full":%q,"start_time":%d,"last_accessed":%d,"state":%q}',
      id, s.harness or '', s.cwd or '', s.cwd_full or '', s.start_time or 0, s.last_accessed or 0, s.state or 'working'
    )
    table.insert(parts, entry)
  end
  return '{' .. table.concat(parts, ',') .. '}'
end

-- Update or insert a session record for this pane.
-- State detection via idle heuristic: content changing = working,
-- content stable > IDLE_THRESHOLD = waiting (agent finished, awaiting input).
function Helm.sessions.track(pane)
  local sessions = wezterm.GLOBAL.helm_sessions
  local id = tostring(pane:pane_id())
  local proc = pane:get_foreground_process_name()
  local harness = Helm.harnesses.detect(proc)
  if not harness then return end  -- only track known harnesses

  local t = Helm.util.now()
  -- cheap content fingerprint of the trailing FP_LINES lines: length + sampled byte sum
  local text = table.concat(pane:get_lines_as_text(Helm.cfg.FP_LINES), '')
  local fp = #text
  for i = 1, #text, 64 do fp = fp + text:byte(i) end

  if not sessions[id] then
    sessions[id] = {
      harness       = harness,
      cwd           = Helm.util.cwd_basename(pane:get_current_working_dir()),
      cwd_full      = Helm.util.cwd_path(pane:get_current_working_dir()),
      start_time    = t,
      last_accessed = t,
      state         = 'working',
      fp            = fp,
      last_change   = t,
    }
  else
    local s = sessions[id]
    s.harness = harness
    s.cwd     = Helm.util.cwd_basename(pane:get_current_working_dir())
    s.cwd_full = Helm.util.cwd_path(pane:get_current_working_dir()) or s.cwd_full
    -- idle detection (skip if user backgrounded it)
    if s.state ~= 'background' then
      if fp ~= s.fp then
        s.fp = fp
        s.last_change = t
        s.state = 'working'
      elseif (t - (s.last_change or t)) > Helm.cfg.IDLE_THRESHOLD then
        -- working → waiting transition: fire the Brain event exactly ONCE
        -- (the guard `s.state ~= 'waiting'` prevents re-firing every idle tick).
        if s.state ~= 'waiting' then
          s.state = 'waiting'
          Helm.brain.notify_waiting(id, s.harness, s.cwd)
        end
      end
    end
  end
  wezterm.GLOBAL.helm_sessions = sessions
  Helm.sessions.save()
end

-- Returns sessions sorted by last_accessed descending (most recent first).
-- Pass `limit` to cap the result to the N most-recently-used sessions.
function Helm.sessions.lru(limit)
  local sessions = wezterm.GLOBAL.helm_sessions
  local list = {}
  for pane_id, s in pairs(sessions) do
    table.insert(list, { pane_id = pane_id, session = s })
  end
  table.sort(list, function(a, b)
    return (a.session.last_accessed or 0) > (b.session.last_accessed or 0)
  end)
  if limit and #list > limit then
    local trimmed = {}
    for i = 1, limit do trimmed[i] = list[i] end
    return trimmed
  end
  return list
end

-- Remove a session record
function Helm.sessions.untrack(pane_id)
  local sessions = wezterm.GLOBAL.helm_sessions
  sessions[tostring(pane_id)] = nil
  wezterm.GLOBAL.helm_sessions = sessions
  Helm.sessions.save()
end

-- Persist only when the serialized state actually changes. track() fires
-- ~1×/sec per window; previously this wrote runtime.json on every tick. We now
-- compare the freshly-serialized JSON against the last written value (kept in
-- GLOBAL so it survives reloads) and skip the file write when nothing changed.
function Helm.sessions.save()
  local json = sessions_to_json(wezterm.GLOBAL.helm_sessions or {})
  if json == wezterm.GLOBAL.helm_last_json then return end
  local f = io.open(Helm.cfg.RUNTIME_JSON, 'w')
  if not f then return end
  f:write(json)
  f:close()
  wezterm.GLOBAL.helm_last_json = json
end

function Helm.sessions.restore()
  local f = io.open(Helm.cfg.RUNTIME_JSON, 'r')
  if not f then return end
  local raw = f:read('*a'); f:close()
  if not raw or raw == '' then return end
  local ok, decoded = pcall(wezterm.json_parse, raw)
  if not ok or type(decoded) ~= 'table' then return end
  local cutoff = Helm.util.now() - 86400
  local restored = {}
  for id, s in pairs(decoded) do
    if type(s) == 'table' and (s.last_accessed or 0) > cutoff then
      restored[id] = s
    end
  end
  wezterm.GLOBAL.helm_sessions = restored
end

-- Rebuild last run's worker panes into `mux_window` as fresh tabs.
-- For each DISTINCT (harness, cwd_full) recorded last time, spawn a tab running
-- that harness in that dir, appending its resume flag when known so the
-- conversation context comes back (agent process itself is fresh).
-- Guardrails: skips entries without a full path / unknown harness / the Brain
-- and Monitor; de-dups (harness,cwd); each spawn is pcall'd so one failure
-- doesn't abort the rest. `snapshot` is the metadata table from restore().
function Helm.sessions.rebuild(mux_window, snapshot)
  if not mux_window or type(snapshot) ~= 'table' then return 0 end
  local seen = {}
  local count = 0
  for _, s in pairs(snapshot) do
    local harness = s and s.harness
    local cwd = s and s.cwd_full
    local hl = (harness or ''):lower()
    if harness and cwd and cwd ~= '' and hl ~= 'brain' and hl ~= 'monitor' then
      local key = harness .. '\0' .. cwd
      if not seen[key] then
        seen[key] = true
        local cmd = Helm.harnesses.spawn_cmd(harness, true)
        if cmd then
          local ok = pcall(function()
            mux_window:spawn_tab {
              cwd  = cwd,
              args = { '/bin/bash', '-l', '-c', 'cd ' .. ("%q"):format(cwd) .. ' && exec ' .. cmd },
            }
          end)
          if ok then count = count + 1 end
        end
      end
    end
  end
  return count
end

-- internal: build InputSelector choices from current sessions (LRU order)
-- Format: '[kiro] wu (01:23) working'
local function build_session_choices()
  local lru = Helm.sessions.lru(Helm.cfg.LRU_LIMIT)
  local choices = {}
  local t = Helm.util.now()
  for _, entry in ipairs(lru) do
    local s = entry.session
    local elapsed = t - (s.start_time or t)
    local mm = math.floor(elapsed / 60)
    local ss = math.floor(elapsed % 60)
    local runtime = string.format('%02d:%02d', mm, ss)
    local harness_lower = (s.harness or 'agent'):lower()
    local project = s.cwd or '?'
    local state = s.state or 'working'
    local label = string.format('[%s] %s (%s) %s', harness_lower, project, runtime, state)
    table.insert(choices, { label = label, id = entry.pane_id })
  end
  if #choices == 0 then
    table.insert(choices, { label = '(no active harness sessions)', id = '' })
  end
  return choices
end

-- ════════════════════════════════════════════════════════════
-- Layer 2: Status Awareness (tab title + HUD + window title)
-- ════════════════════════════════════════════════════════════
Helm.status = {}

-- Calm, low-saturation palette for the bottom bar.
Helm.status.palette = {
  working = '#7aa2f7',  -- blue   — agent actively producing output
  waiting = '#e0af68',  -- orange — agent finished, awaiting input
  dim     = '#565f73',  -- gray   — separators, background count, idle
  usage   = '#8a7faa',  -- muted purple/gray — per-harness token usage
  ghost   = '#8a8fa3',  -- ghost glyph
  text    = '#a9b1d6',  -- harness/project label
}

-- Format a token count compactly: 142k / 1.2M.
function Helm.status.fmt_tokens(n)
  if not n or n == 0 then return '0' end
  if n >= 1000000 then
    local m = n / 1000000
    return (m >= 10 and string.format('%dM', math.floor(m + 0.5))) or string.format('%.1fM', m)
  end
  if n >= 1000 then return math.floor(n / 1000) .. 'k' end
  return tostring(n)
end

-- ── Live per-harness usage (quota.py --json), throttled + cached ──
-- quota.py reads local session/message files. We call it via
-- run_child_process at most once / 60s and stash the result in
-- wezterm.GLOBAL.helm_quota_cache = { ts=, data= }. render() reads the cache
-- and kicks a refresh when stale; the fetch guard prevents re-entry.

-- Resolve quota.py path once (bundle Resources, then dev repo), cache in GLOBAL.
function Helm.status.quota_script()
  if wezterm.GLOBAL.helm_quota_path ~= nil then
    return wezterm.GLOBAL.helm_quota_path or nil
  end
  local home = os.getenv('HOME') or ''
  local candidates = {
    wezterm.executable_dir:gsub('MacOS/?$', 'Resources') .. '/tools/helm-quota/quota.py',
    home .. '/workspace/helm-terminal/tools/helm-quota/quota.py',
    home .. '/.config/kaku/tools/helm-quota/quota.py',
  }
  for _, p in ipairs(candidates) do
    local f = io.open(p, 'r')
    if f then f:close(); wezterm.GLOBAL.helm_quota_path = p; return p end
  end
  wezterm.GLOBAL.helm_quota_path = false  -- remember "not found"
  return nil
end

-- Blocking call, but invoked at most once per 60s (quota.py runs in ~100ms).
function Helm.status.refresh_quota()
  local script = Helm.status.quota_script()
  if not script then
    wezterm.GLOBAL.helm_quota_fetching = false
    return
  end
  local ok, stdout = pcall(wezterm.run_child_process, { 'python3', script, '--json' })
  if ok and stdout and stdout ~= '' then
    local ok2, data = pcall(wezterm.json_parse, stdout)
    if ok2 and type(data) == 'table' then
      wezterm.GLOBAL.helm_quota_cache = { ts = Helm.util.now(), data = data }
    end
  end
  wezterm.GLOBAL.helm_quota_fetching = false
end

-- Returns formatted usage strings like { 'kiro 142k', 'claude 1.2M' };
-- kicks a background-ish refresh when the cache is stale (>60s).
function Helm.status.usage_summary()
  local now = Helm.util.now()
  local cache = wezterm.GLOBAL.helm_quota_cache
  if (not cache or (now - (cache.ts or 0)) > 60) and not wezterm.GLOBAL.helm_quota_fetching then
    wezterm.GLOBAL.helm_quota_fetching = true
    Helm.status.refresh_quota()
    cache = wezterm.GLOBAL.helm_quota_cache
  end
  if not cache or type(cache.data) ~= 'table' then return {} end
  local parts = {}
  for _, name in ipairs({ 'kiro', 'claude', 'opencode' }) do
    local d = cache.data[name]
    if type(d) == 'table' and (d.tokens_today or 0) > 0 then
      table.insert(parts, name .. ' ' .. Helm.status.fmt_tokens(d.tokens_today))
    end
  end
  return parts
end

-- format-tab-title: the bar is now a single clean status line, so tabs shrink
-- to a tiny marker (active ● / inactive ·) instead of boxy browser tabs.
-- The agent + project info now lives in the LEFT status zone (render).
function Helm.status.tab_title(tab)
  return tab.is_active and ' ● ' or ' · '
end

-- update-right-status render: paint the bottom bar in two zones.
--   LEFT  (set_left_status)  : current pane's agent → 👻 kiro · proj ▶ working 2m34s
--   RIGHT (set_right_status) : globals + live usage → ○ 2 bg · ◐ 1 waiting   kiro 142k · claude 1.2M
-- The bottom bar is a toggleable HELP BAR (a key-bindings cheat-sheet), not a
-- per-agent HUD. Philosophy: zero friction, out of the box, focus on shipping —
-- the keys you need are always one glance away, and one keystroke (⌘/) away from
-- getting out of your way. Per-agent status now lives in the Brain (⌘1) and the
-- Monitor (⌘3) layers, so the bottom bar no longer duplicates it.
--   visible (default) → calm one-line cheat-sheet
--   hidden  (⌘/)      → empty, nothing at the bottom
function Helm.status.render(window, pane)
  local P = Helm.status.palette

  if wezterm.GLOBAL.helm_help_visible then
    window:set_left_status(wezterm.format({
      { Foreground = { Color = P.ghost } }, { Text = ' ›_  ' },
      { Foreground = { Color = P.text } },  { Text = '⌘1 Brain  ⌘2 Work  ⌘3 Monitor  ' },
      { Foreground = { Color = P.dim } },   { Text = '⌘⇧K Launch  ⌘⇧S Sessions  ⌘/ Help ' },
    }))
  else
    window:set_left_status('')
  end
  window:set_right_status('')

  -- Window title keeps an at-a-glance agent count even when the bar is hidden.
  local waiting_count, total = 0, 0
  for _, entry in ipairs(Helm.sessions.lru()) do
    total = total + 1
    if entry.session.state == 'waiting' then waiting_count = waiting_count + 1 end
  end
  if total > 0 then
    local title = 'Helm \xe2\x80\x94 ' .. total .. ' agent' .. (total == 1 and '' or 's')
    if waiting_count > 0 then title = title .. ' (' .. waiting_count .. ' waiting)' end
    window:set_title(title)
  else
    window:set_title('Helm')
  end
end

-- Layer 3 lives in tools/ (cross-harness memory via symlinks) — no Lua needed here

-- ════════════════════════════════════════════════════════════
-- Layer 2.5: Brain 🧠 — the "First Mate" orchestrator (Sonnet)
-- An optional coordination agent that lives in its OWN tab. Cmd+Shift+Return
-- toggles between the Brain and the worker you were last on. When a worker
-- transitions into 'waiting', we inject a one-line event into the Brain pane
-- so the First Mate notices and can report / route on your behalf.
-- ════════════════════════════════════════════════════════════
Helm.brain = {}

-- Resolve launch-brain.sh once (bundle Resources, then dev repo, then ~/.config),
-- cached in GLOBAL. Same resolution strategy as quota_script().
function Helm.brain.launcher()
  if wezterm.GLOBAL.helm_brain_path ~= nil then
    return wezterm.GLOBAL.helm_brain_path or nil
  end
  local home = os.getenv('HOME') or ''
  local candidates = {
    wezterm.executable_dir:gsub('MacOS/?$', 'Resources') .. '/tools/helm-brain/launch-brain.sh',
    home .. '/workspace/helm-terminal/tools/helm-brain/launch-brain.sh',
    home .. '/.config/kaku/tools/helm-brain/launch-brain.sh',
  }
  for _, p in ipairs(candidates) do
    local f = io.open(p, 'r')
    if f then f:close(); wezterm.GLOBAL.helm_brain_path = p; return p end
  end
  wezterm.GLOBAL.helm_brain_path = false  -- remember "not found"
  return nil
end

-- Return the live Brain pane (mux pane object) or nil if it's gone. Clears the
-- stale id so a fresh Cmd+Shift+Return re-spawns the Brain.
function Helm.brain.pane()
  local id = wezterm.GLOBAL.helm_brain_pane
  if not id then return nil end
  local ok, p = pcall(wezterm.mux.get_pane, id)
  if ok and p then return p end
  wezterm.GLOBAL.helm_brain_pane = nil
  return nil
end

-- Focus a pane by id: activate its tab + focus its gui window. Returns true if found.
function Helm.brain.focus_pane(pane_id)
  if not pane_id then return false end
  for _, win in ipairs(wezterm.mux.all_windows()) do
    for _, tab in ipairs(win:tabs()) do
      for _, p in ipairs(tab:panes()) do
        if p:pane_id() == pane_id then
          tab:activate()
          for _, gw in ipairs(wezterm.gui.gui_windows()) do
            if gw:mux_window():window_id() == win:window_id() then gw:focus(); break end
          end
          return true
        end
      end
    end
  end
  return false
end

-- Spawn the Brain in a dedicated tab of `mux_window`; remember its tab + pane
-- id and activate it. Returns pane or nil. Used at gui-startup (no gui window
-- exists yet) and by Helm.brain.spawn(window).
function Helm.brain.spawn_in(mux_window)
  local launcher = Helm.brain.launcher()
  if not launcher or not mux_window then return nil end
  -- exec so the agent takes over the shell (pane won't close when it exits cleanly)
  local tab, pane = mux_window:spawn_tab {
    args = { '/bin/bash', '-l', '-c', "exec '" .. launcher .. "'" },
  }
  wezterm.GLOBAL.helm_brain_tab  = tab:tab_id()
  wezterm.GLOBAL.helm_brain_pane = pane:pane_id()
  tab:activate()
  return pane
end

-- Spawn the Brain in a dedicated tab; remember its tab + pane id. Returns pane or nil.
function Helm.brain.spawn(window)
  if not window then return nil end
  return Helm.brain.spawn_in(window:mux_window())
end

-- Cmd+Shift+Return action: toggle Brain <-> last worker. Spawns Brain on first use.
function Helm.brain.toggle(window, pane)
  local bpane = Helm.brain.pane()
  if bpane then
    if pane:pane_id() == bpane:pane_id() then
      -- currently on the Brain → flip back to the worker we came from
      local last = wezterm.GLOBAL.helm_last_worker
      if last then Helm.brain.focus_pane(last) end
    else
      -- currently on a worker → remember it, jump to the Brain
      wezterm.GLOBAL.helm_last_worker = pane:pane_id()
      Helm.brain.focus_pane(bpane:pane_id())
    end
  else
    -- no Brain yet → remember the current worker and spawn one
    wezterm.GLOBAL.helm_last_worker = pane:pane_id()
    Helm.brain.spawn(window)
  end
end

-- Inject a one-line event into the Brain pane when a worker starts WAITING.
-- No-op if no Brain exists, and never injects into the Brain pane itself.
function Helm.brain.notify_waiting(worker_id, harness, project)
  local bpane = Helm.brain.pane()
  if not bpane then return end
  if bpane:pane_id() == tonumber(worker_id) then return end
  bpane:send_text(string.format(
    '\n[helm-event] session %s (%s · %s) is now WAITING for input.\n',
    tostring(worker_id), harness or '?', project or '?'
  ))
end

-- ════════════════════════════════════════════════════════════
-- Helm.top — the Monitor layer (helm-top, an htop-style session list)
-- ════════════════════════════════════════════════════════════
-- Philosophy: zero friction, out of the box, focus on shipping. helm-top is a
-- stdlib-only Python viewer over `helm-brain sessions` — no deps, no state of
-- its own. You stay at the helm; this just shows who's working / waiting so you
-- can jump to the one that needs you and get back to shipping.
Helm.top = {}

-- Resolve the helm-top script once (bundle Resources, dev repo, ~/.config),
-- cached in GLOBAL. Same strategy as Helm.brain.launcher().
function Helm.top.launcher()
  if wezterm.GLOBAL.helm_top_path ~= nil then
    return wezterm.GLOBAL.helm_top_path or nil
  end
  local home = os.getenv('HOME') or ''
  local candidates = {
    wezterm.executable_dir:gsub('MacOS/?$', 'Resources') .. '/tools/helm-top/helm-top',
    home .. '/workspace/helm-terminal/tools/helm-top/helm-top',
    home .. '/.config/kaku/tools/helm-top/helm-top',
  }
  for _, p in ipairs(candidates) do
    local f = io.open(p, 'r')
    if f then f:close(); wezterm.GLOBAL.helm_top_path = p; return p end
  end
  wezterm.GLOBAL.helm_top_path = false  -- remember "not found"
  return nil
end

-- Return the live Monitor pane, or nil (clearing the stale id).
function Helm.top.pane()
  local id = wezterm.GLOBAL.helm_top_pane
  if not id then return nil end
  local ok, p = pcall(wezterm.mux.get_pane, id)
  if ok and p then return p end
  wezterm.GLOBAL.helm_top_pane = nil
  return nil
end

-- Focus the Monitor, spawning helm-top in its own tab on first use.
function Helm.top.focus(window)
  local tp = Helm.top.pane()
  if tp then
    Helm.brain.focus_pane(tp:pane_id())
    return
  end
  local launcher = Helm.top.launcher()
  if not launcher then return end
  local tab, pane = window:mux_window():spawn_tab {
    args = { '/bin/bash', '-l', '-c', "exec '" .. launcher .. "'" },
  }
  wezterm.GLOBAL.helm_top_tab  = tab:tab_id()
  wezterm.GLOBAL.helm_top_pane = pane:pane_id()
  tab:activate()
end

-- ════════════════════════════════════════════════════════════
-- Helm.workspace — the Workspace layer (the worker panes you actually drive)
-- ════════════════════════════════════════════════════════════
Helm.workspace = {}

-- Focus the worker you were last on; else the first pane that is neither the
-- Brain nor the Monitor. This is "get me back to the work".
function Helm.workspace.focus(_window, _pane)
  local bp = wezterm.GLOBAL.helm_brain_pane
  local tp = wezterm.GLOBAL.helm_top_pane
  local last = wezterm.GLOBAL.helm_last_worker
  if last and last ~= bp and last ~= tp and Helm.brain.focus_pane(last) then
    return
  end
  for _, win in ipairs(wezterm.mux.all_windows()) do
    for _, tab in ipairs(win:tabs()) do
      for _, p in ipairs(tab:panes()) do
        local id = p:pane_id()
        if id ~= bp and id ~= tp then
          Helm.brain.focus_pane(id)
          return
        end
      end
    end
  end
end

-- Remember the current pane as "the worker" if it isn't the Brain/Monitor, so
-- Cmd+2 can return to it. Called by the layer-nav binds.
function Helm.workspace.remember(pane)
  local id = pane:pane_id()
  if id ~= wezterm.GLOBAL.helm_brain_pane and id ~= wezterm.GLOBAL.helm_top_pane then
    wezterm.GLOBAL.helm_last_worker = id
  end
end

-- ════════════════════════════════════════════════════════════
-- Keybindings — all Cmd+Shift+* binds + the Cmd+L / Cmd+Shift+M overrides
-- ════════════════════════════════════════════════════════════
Helm.keys = {}

function Helm.keys.bind(config)
  config.keys = config.keys or {}

  -- ── Helm's three-layer view navigation ──────────────────────
  --   Cmd+1 Brain (First Mate)  ·  Cmd+2 Workspace (workers)  ·  Cmd+3 Monitor (helm-top)
  -- Cmd+1: jump to the Brain (spawn it on first use).
  table.insert(config.keys, {
    key = '1',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      Helm.workspace.remember(pane)
      local b = Helm.brain.pane()
      if b then Helm.brain.focus_pane(b:pane_id()) else Helm.brain.spawn(window) end
    end),
  })

  -- Cmd+2: back to the Workspace (the worker pane you were last on).
  table.insert(config.keys, {
    key = '2',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      Helm.workspace.focus(window, pane)
    end),
  })

  -- Cmd+3: open the Monitor (helm-top, htop-style session list).
  table.insert(config.keys, {
    key = '3',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      Helm.workspace.remember(pane)
      Helm.top.focus(window)
    end),
  })

  -- Cmd+/: toggle the bottom help bar (key bindings cheat-sheet).
  table.insert(config.keys, {
    key = '/',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      wezterm.GLOBAL.helm_help_visible = not wezterm.GLOBAL.helm_help_visible
      Helm.status.render(window, pane)  -- repaint immediately
    end),
  })

  -- Cmd+Shift+Return: toggle between the Brain (First Mate) view and the worker
  -- pane you were last on. On first use, spawns the Brain in its own tab.
  table.insert(config.keys, {
    key  = 'Return',
    mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      Helm.brain.toggle(window, pane)
    end),
  })

  -- Cmd+Shift+M: 轮转 kiro 模型 sonnet ↔ opus
  table.insert(config.keys, {
    key = 'M',
    mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(_, pane)
      local f = io.open(os.getenv('HOME') .. '/.kiro/settings/cli.json', 'r')
      local current = f and f:read('*a') or ''
      if f then f:close() end
      local next_model = current:find('opus') and 'claude-sonnet-4.6' or 'claude-opus-4.8'
      pane:inject_output('')  -- noop, use SendString
      wezterm.GLOBAL.kiro_next_model = next_model
      -- SendString 无法从 callback 直接调，用 MultiplexedPane:send_text
      pane:send_text('/model ' .. next_model .. '\r')
    end),
  })

  -- Cmd+Shift+K: Helm Harness Launcher 🚀
  table.insert(config.keys, {
    key = 'K',
    mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      window:perform_action(
        wezterm.action.InputSelector {
          action = wezterm.action_callback(function(w, p, id, label)
            if not id then return end
            w:perform_action(
              wezterm.action.SplitPane {
                direction = 'Right',
                -- exec so the agent takes over the shell process; without exec
                -- bash exits when the command ends and the pane closes (looks like a crash)
                command = { args = { '/bin/bash', '-l', '-c', 'exec ' .. id } },
              },
              p
            )
          end),
          fuzzy = true,
          title = '  Launch Harness',
          choices = Helm.harnesses.choices(),
        },
        pane
      )
    end),
  })

  -- Cmd+Shift+S: show session overlay
  table.insert(config.keys, {
    key   = 'S',
    mods  = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      window:perform_action(
        wezterm.action.InputSelector {
          action      = wezterm.action.EmitEvent 'helm-session-selected',
          title       = '  Helm Sessions',
          choices     = build_session_choices(),
          fuzzy       = true,
          description = 'Select a session to focus',
        },
        pane
      )
    end),
  })

  -- Cmd+Shift+B: mark current pane as 'background'
  table.insert(config.keys, {
    key  = 'B',
    mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(_, pane)
      local sessions = wezterm.GLOBAL.helm_sessions
      local id = tostring(pane:pane_id())
      if sessions[id] then
        sessions[id].state = 'background'
        wezterm.GLOBAL.helm_sessions = sessions
        Helm.sessions.save()
      end
    end),
  })

  -- Override Cmd+L: Helm doesn't need the built-in AI chat (use your own harness).
  -- Remap to clear screen (send Ctrl+L to the shell), the conventional terminal behavior.
  table.insert(config.keys, {
    key = 'l',
    mods = 'CMD',
    action = wezterm.action.SendKey { key = 'l', mods = 'CTRL' },
  })
end

-- ════════════════════════════════════════════════════════════
-- Hooks + wiring — call once with the config table to activate Helm.
-- ════════════════════════════════════════════════════════════
function Helm.apply(config)
  -- Session state lives in GLOBAL so it survives config reloads.
  wezterm.GLOBAL.helm_sessions = wezterm.GLOBAL.helm_sessions or {}

  -- The help bar (bottom cheat-sheet) is VISIBLE by default; ⌘/ toggles it.
  if wezterm.GLOBAL.helm_help_visible == nil then
    wezterm.GLOBAL.helm_help_visible = true
  end

  -- The single update-right-status handler: (1) track this pane's session
  -- (working/waiting idle heuristic), (2) render the HUD + window title.
  wezterm.on('update-right-status', function(win, pane)
    Helm.sessions.track(pane)
    Helm.status.render(win, pane)
  end)

  -- clean up closed panes
  wezterm.on('pane-removed', function(pane)
    if pane then Helm.sessions.untrack(pane:pane_id()) end
  end)

  -- update last_accessed on pane focus
  wezterm.on('pane-focused', function(pane)
    local sessions = wezterm.GLOBAL.helm_sessions
    local id = tostring(pane:pane_id())
    if sessions[id] then
      sessions[id].last_accessed = Helm.util.now()
      wezterm.GLOBAL.helm_sessions = sessions
    end
  end)

  -- Boot sequence: rebuild last run's worker tabs, then land in the Brain.
  -- We own window creation here (registering gui-startup suppresses wezterm's
  -- default window), so we spawn ONE window whose first tab IS the Brain, add
  -- the rebuilt workers as further tabs, then re-activate the Brain so the user
  -- opens straight into the Brain view (Layer 1).
  wezterm.on('gui-startup', function(cmd)
    -- guard against a double run (gui-startup should fire once, but be safe)
    if wezterm.GLOBAL.helm_restored then return end
    wezterm.GLOBAL.helm_restored = true

    -- load last run's metadata into GLOBAL, then snapshot it for the rebuild
    Helm.sessions.restore()
    local snapshot = wezterm.GLOBAL.helm_sessions or {}
    -- start live tracking from a clean slate: the snapshot's pane ids are stale,
    -- live panes re-register via update-right-status.
    wezterm.GLOBAL.helm_sessions = {}

    -- create the initial window running the Brain as its first tab (falls back
    -- to a plain shell if the Brain launcher can't be found)
    local launcher = Helm.brain.launcher()
    local spawn_args = launcher
      and { args = { '/bin/bash', '-l', '-c', "exec '" .. launcher .. "'" } }
      or (cmd or {})
    local ok, brain_tab, _brain_pane, mux_window = pcall(wezterm.mux.spawn_window, spawn_args)
    if not ok or not mux_window then return end
    if launcher then
      wezterm.GLOBAL.helm_brain_tab  = brain_tab:tab_id()
      wezterm.GLOBAL.helm_brain_pane = _brain_pane:pane_id()
    end

    -- rebuild workers in the background (best-effort, each spawn pcall'd)
    Helm.sessions.rebuild(mux_window, snapshot)

    -- land on the Brain tab last so it's the front/active view
    pcall(function() brain_tab:activate() end)
  end)

  -- agent status in tab title
  wezterm.on('format-tab-title', function(tab, _, _, _, _, _)
    return Helm.status.tab_title(tab)
  end)

  -- session overlay selection: focus the chosen pane
  wezterm.on('helm-session-selected', function(window, pane, id)
    if not id or id == '' then return end
    local pane_id = tonumber(id)
    if not pane_id then return end
    local ok, target = pcall(wezterm.mux.get_pane, pane_id)
    if ok and target then
      -- Find the tab containing this pane and activate it
      for _, win in ipairs(wezterm.mux.all_windows()) do
        for _, tab in ipairs(win:tabs()) do
          for _, p in ipairs(tab:panes()) do
            if p:pane_id() == pane_id then
              tab:activate()
              -- Also activate the specific pane within the tab
              local gui_wins = wezterm.gui.gui_windows()
              for _, gw in ipairs(gui_wins) do
                if gw:mux_window():window_id() == win:window_id() then
                  gw:focus()
                  break
                end
              end
              return
            end
          end
        end
      end
    end
  end)

  Helm.keys.bind(config)
end

-- ── Helm bottom status bar ──────────────────────────────────
-- WezTerm renders status text ON the tab bar (no standalone status widget),
-- so to get a single clean status LINE at the very bottom and NO boxy tabs at
-- the top we: keep the tab bar enabled (it hosts the status text), switch it to
-- the retro/text style, push it to the bottom, and recolor tabs so they blend
-- into the bar (the tiny ● / · markers come from Helm.status.tab_title).
config.enable_tab_bar = true            -- MUST stay true: hosts set_left/right_status
config.use_fancy_tab_bar = false        -- retro/text style — no rounded tab boxes
config.tab_bar_at_bottom = true         -- move the whole bar to the bottom
config.hide_tab_bar_if_only_one_tab = false  -- always show the status line
config.show_new_tab_button_in_tab_bar = false
config.tab_max_width = 6                -- markers are tiny; keep them tight

config.colors = config.colors or {}
config.colors.tab_bar = {
  background = '#16161e',
  active_tab         = { bg_color = '#16161e', fg_color = '#8a8fa3' },
  inactive_tab       = { bg_color = '#16161e', fg_color = '#3b4048' },
  inactive_tab_hover = { bg_color = '#16161e', fg_color = '#565f73', italic = false },
  new_tab            = { bg_color = '#16161e', fg_color = '#3b4048' },
  new_tab_hover      = { bg_color = '#16161e', fg_color = '#565f73' },
}

Helm.apply(config)
return config
