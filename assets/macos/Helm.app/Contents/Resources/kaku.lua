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

-- CMD+SHIFT+M: 轮转 kiro 模型 sonnet ↔ opus
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

config.restore_previous_session = true

-- ════════════════════════════════════════════════════════════
-- Helm Sessions 🪖 — Layer 1: session tracker + Cmd+Shift+S overlay
-- ════════════════════════════════════════════════════════════

-- helm_sessions[pane_id] = { harness, cwd, start_time, state }
-- Stored in wezterm.GLOBAL so it survives config reloads.
wezterm.GLOBAL.helm_sessions = wezterm.GLOBAL.helm_sessions or {}

-- Known harness process names → display labels
local HARNESS_NAMES = {
  ['kiro-cli']  = 'Kiro',
  kiro          = 'Kiro',
  ['claude']    = 'Claude',
  opencode      = 'opencode',
  codex         = 'Codex',
  aider         = 'Aider',
}

local function detect_harness(process_name)
  if not process_name then return nil end
  local base = process_name:match('([^/]+)$') or process_name
  -- strip common wrappers: node, python, ruby, etc.
  for key, label in pairs(HARNESS_NAMES) do
    if base:lower():find(key, 1, true) then return label end
  end
  return nil
end

local function cwd_basename(cwd_url)
  if not cwd_url then return '?' end
  local path = tostring(cwd_url)
  -- strip file:// prefix
  path = path:gsub('^file://[^/]*', '')
  -- strip trailing slash
  path = path:gsub('/$', '')
  return path:match('([^/]+)$') or path
end

local function now_secs()
  return tonumber(wezterm.strftime('%s')) or 0
end

local function fmt_duration(secs)
  local s = math.floor(secs)
  return string.format('%02d:%02d:%02d', math.floor(s/3600), math.floor((s%3600)/60), s%60)
end

-- Update or insert a session record for this pane
local function helm_track(pane)
  local sessions = wezterm.GLOBAL.helm_sessions
  local id = tostring(pane:pane_id())
  local proc = pane:get_foreground_process_name()
  local harness = detect_harness(proc)
  if not harness then return end  -- only track known harnesses

  if not sessions[id] then
    sessions[id] = {
      harness       = harness,
      cwd           = cwd_basename(pane:get_current_working_dir()),
      start_time    = now_secs(),
      last_accessed = now_secs(),
      state         = 'working',
    }
  else
    -- refresh cwd and harness on every check
    sessions[id].harness = harness
    sessions[id].cwd     = cwd_basename(pane:get_current_working_dir())
  end
  wezterm.GLOBAL.helm_sessions = sessions
end

-- Returns sessions sorted by last_accessed descending (most recent first)
local function get_lru_sessions()
  local sessions = wezterm.GLOBAL.helm_sessions
  local list = {}
  for pane_id, s in pairs(sessions) do
    table.insert(list, { pane_id = pane_id, session = s })
  end
  table.sort(list, function(a, b)
    return (a.session.last_accessed or 0) > (b.session.last_accessed or 0)
  end)
  return list
end

-- Remove a session record
local function helm_untrack(pane_id)
  local sessions = wezterm.GLOBAL.helm_sessions
  sessions[tostring(pane_id)] = nil
  wezterm.GLOBAL.helm_sessions = sessions
end

-- Hook: update on every right-status tick (fires ~every second per active window)
wezterm.on('update-right-status', function(_, pane)
  helm_track(pane)
end)

-- Hook: clean up closed panes
wezterm.on('pane-removed', function(pane)
  if pane then helm_untrack(pane:pane_id()) end
end)

-- Hook: update last_accessed on pane focus
wezterm.on('pane-focused', function(pane)
  local sessions = wezterm.GLOBAL.helm_sessions
  local id = tostring(pane:pane_id())
  if sessions[id] then
    sessions[id].last_accessed = now_secs()
    wezterm.GLOBAL.helm_sessions = sessions
  end
end)

-- Build InputSelector choices from current sessions (LRU order)
local function build_session_choices()
  local lru = get_lru_sessions()
  local choices = {}
  local t = now_secs()
  for _, entry in ipairs(lru) do
    local s = entry.session
    local runtime = fmt_duration(t - (s.start_time or t))
    local bg_prefix = (s.state == 'background') and '[BG] ' or ''
    local label = string.format('%s[%s]  %s  %s  (%s)', bg_prefix, s.harness, s.cwd, runtime, s.state)
    table.insert(choices, { label = label, id = entry.pane_id })
  end
  if #choices == 0 then
    table.insert(choices, { label = '(no active harness sessions)', id = '' })
  end
  return choices
end

-- Handle selection: focus the chosen pane
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
    end
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

-- ════════════════════════════════════════════════════════════
-- Layer 2: agent status in tab title
-- Active harness → '🔵 HarnessName (MM:SS)'
-- Shell/other   → default tab title
-- ════════════════════════════════════════════════════════════
wezterm.on('format-tab-title', function(tab, _, _, _, _, _)
  local pane = tab:active_pane()
  local proc = pane:get_foreground_process_name()
  local harness = detect_harness(proc)
  if harness then
    local id = tostring(pane:pane_id())
    local sessions = wezterm.GLOBAL.helm_sessions or {}
    local start = sessions[id] and sessions[id].start_time or now_secs()
    local elapsed = now_secs() - start
    local mm = math.floor(elapsed / 60)
    local ss = elapsed % 60
    return '🔵 ' .. harness .. ' (' .. string.format('%02d:%02d', mm, ss) .. ')'
  end
  -- fallback: pane title set by shell/app
  return tab:get_title()
end)

-- Helm Harness Launcher 🚀 — Cmd+Shift+K
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
              command = { args = { '/bin/bash', '-l', '-c', id } },
            },
            p
          )
        end),
        fuzzy = true,
        title = '  Launch Harness',
        choices = {
          { id = 'kiro-cli chat --trust-all-tools --agent default --effort medium', label = '🤖 kiro  (default, medium effort)' },
          { id = 'claude --dangerously-skip-permissions',                           label = '🟣 claude-code  (auto-approve)' },
          { id = 'opencode',                                                        label = '⚡ opencode' },
          { id = 'codex',                                                           label = '🔵 codex' },
        },
      },
      pane
    )
  end),
})

-- Helm Agent Notifications -- detect waiting state + Cmd+Shift+U + HUD overlay
wezterm.on('update-right-status', function(window, pane)
  local sessions = wezterm.GLOBAL.helm_sessions or {}
  local pid = tostring(pane:pane_id())
  local s = sessions[pid]
  if s then
    local text = table.concat(pane:get_lines_as_text(3), ' '):lower()
    if text:match('[>$] $') or text:match('waiting') then
      s.state = 'waiting'; sessions[pid] = s
      wezterm.GLOBAL.helm_sessions = sessions
    end
  end

  -- Build compact HUD: [kiro 🔵 02:34 | claude 🔵 05:12 | 2 bg]
  local t = now_secs()
  local working_parts = {}
  local bg_count = 0
  for _, entry in ipairs(get_lru_sessions()) do
    local sess = entry.session
    if sess.state == 'background' then
      bg_count = bg_count + 1
    else
      local icon = sess.state == 'waiting' and '🟠' or '🔵'
      local runtime = fmt_duration(t - (sess.start_time or t))
      table.insert(working_parts, sess.harness .. ' ' .. icon .. ' ' .. runtime)
    end
  end
  if #working_parts == 0 and bg_count == 0 then
    window:set_right_status('')
    return
  end
  local hud = table.concat(working_parts, ' | ')
  if bg_count > 0 then
    if hud ~= '' then hud = hud .. ' | ' end
    hud = hud .. bg_count .. ' bg'
  end
  window:set_right_status(wezterm.format({
    { Foreground = { Color = '#a89070' } },
    { Text = ' [' .. hud .. '] ' },
  }))
end)

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

return config
