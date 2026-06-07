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
--   match : substring matched against the foreground process name
--   name  : display label used in tab titles / HUD
--   cmd   : command run by the launcher
--   label : menu label shown in the launcher
-- ════════════════════════════════════════════════════════════
Helm.harnesses = {}
Helm.harnesses.list = {
  { match = 'kiro',     name = 'Kiro',     cmd = 'kiro-cli chat --trust-all-tools --agent default --effort medium', label = '🤖 kiro  (default, medium effort)' },
  { match = 'claude',   name = 'Claude',   cmd = 'claude --dangerously-skip-permissions',                           label = '🟣 claude-code  (auto-approve)' },
  { match = 'opencode', name = 'opencode', cmd = 'opencode',                                                        label = '⚡ opencode' },
  { match = 'codex',    name = 'Codex',    cmd = 'codex',                                                           label = '🔵 codex' },
}

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
      '"%s":{"harness":%q,"cwd":%q,"start_time":%d,"last_accessed":%d,"state":%q}',
      id, s.harness or '', s.cwd or '', s.start_time or 0, s.last_accessed or 0, s.state or 'working'
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
    -- idle detection (skip if user backgrounded it)
    if s.state ~= 'background' then
      if fp ~= s.fp then
        s.fp = fp
        s.last_change = t
        s.state = 'working'
      elseif (t - (s.last_change or t)) > Helm.cfg.IDLE_THRESHOLD then
        s.state = 'waiting'
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
function Helm.status.render(window, pane)
  local t = Helm.util.now()
  local P = Helm.status.palette

  -- ── LEFT: current pane's agent ──────────────────────────────
  local proc = pane:get_foreground_process_name()
  local harness = Helm.harnesses.detect(proc)
  local left
  if harness then
    local project = Helm.util.cwd_basename(pane:get_current_working_dir())
    local sess = (wezterm.GLOBAL.helm_sessions or {})[tostring(pane:pane_id())]
    local state = (sess and sess.state) or 'working'
    local scolor, sicon, slabel
    if state == 'waiting' then
      scolor, sicon, slabel = P.waiting, '◐', 'waiting'
    elseif state == 'background' then
      scolor, sicon, slabel = P.dim, '⏸', 'background'
    else
      scolor, sicon, slabel = P.working, '▶', 'working'
    end
    local runtime = sess and Helm.util.fmt_short(t - (sess.start_time or t)) or ''
    left = {
      { Foreground = { Color = P.ghost } }, { Text = ' ' .. Helm.GHOST .. ' ' },
      { Foreground = { Color = P.text } },  { Text = harness:lower() },
      { Foreground = { Color = P.dim } },   { Text = ' · ' },
      { Foreground = { Color = P.text } },  { Text = project .. '  ' },
      { Foreground = { Color = scolor } },  { Text = sicon .. ' ' .. slabel .. ' ' .. runtime .. ' ' },
    }
  else
    left = {
      { Foreground = { Color = P.ghost } }, { Text = ' ' .. Helm.GHOST .. ' ' },
      { Foreground = { Color = P.dim } },   { Text = 'helm · idle ' },
    }
  end
  window:set_left_status(wezterm.format(left))

  -- ── RIGHT: global summary + live usage ──────────────────────
  local bg_count, waiting_count, total = 0, 0, 0
  for _, entry in ipairs(Helm.sessions.lru()) do
    total = total + 1
    local st = entry.session.state
    if st == 'background' then bg_count = bg_count + 1
    elseif st == 'waiting' then waiting_count = waiting_count + 1 end
  end

  local right = {}
  local function sep()
    table.insert(right, { Foreground = { Color = P.dim } })
    table.insert(right, { Text = ' · ' })
  end
  if bg_count > 0 then
    table.insert(right, { Foreground = { Color = P.dim } })
    table.insert(right, { Text = '○ ' .. bg_count .. ' bg' })
  end
  if waiting_count > 0 then
    if bg_count > 0 then sep() else table.insert(right, { Text = '' }) end
    table.insert(right, { Foreground = { Color = P.waiting } })
    table.insert(right, { Text = '◐ ' .. waiting_count .. ' waiting' })
  end

  local usage = Helm.status.usage_summary()
  if #usage > 0 then
    table.insert(right, { Foreground = { Color = P.dim } })
    table.insert(right, { Text = '    ' })  -- gap between counts and usage
    for i, u in ipairs(usage) do
      if i > 1 then
        table.insert(right, { Foreground = { Color = P.dim } })
        table.insert(right, { Text = ' · ' })
      end
      table.insert(right, { Foreground = { Color = P.usage } })
      table.insert(right, { Text = u })
    end
  end
  table.insert(right, { Text = ' ' })
  window:set_right_status(wezterm.format(right))

  -- ── Window title: "Helm — N agents (M waiting)" ─────────────
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
-- Keybindings — all Cmd+Shift+* binds + the Cmd+L / Cmd+Shift+M overrides
-- ════════════════════════════════════════════════════════════
Helm.keys = {}

function Helm.keys.bind(config)
  config.keys = config.keys or {}

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

  -- Cmd+Shift+U: jump to the most-recent waiting session
  table.insert(config.keys, {
    key = 'U', mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      local sessions = wezterm.GLOBAL.helm_sessions or {}
      local best_id, best_t = nil, 0
      for id, s in pairs(sessions) do
        if s.state == 'waiting' and (s.last_accessed or 0) > best_t then
          best_id = tonumber(id); best_t = s.last_accessed or 0
        end
      end
      if best_id then
        for _, mux_win in ipairs(wezterm.mux.all_windows()) do
          for _, tab in ipairs(mux_win:tabs()) do
            for _, p in ipairs(tab:panes()) do
              if p:pane_id() == best_id then tab:activate(); mux_win:gui_window():focus(); return end
            end
          end
        end
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

  -- restore persisted sessions on startup
  wezterm.on('gui-startup', function()
    Helm.sessions.restore()
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
