local wezterm = require 'wezterm'

-- Kaji is a standalone, self-contained config (like upstream Kaku's). It does
-- NOT load a separate "bundled" file: doing so caused the bundled copy to go
-- stale vs. the dev-linked / user copy, and the loader could recurse into
-- itself. Everything Kaji needs is defined directly in this file; the
-- 'Kaku Dark' color scheme is built into the binary.
local config = {}


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

-- Theme follows the macOS appearance, exactly like Kaku: warm cream 'Kaku Light'
-- in light mode, 'Kaku Dark' in dark mode. These resolvers are ported verbatim
-- from Kaku; the `resolve_kaku_color_scheme(...)` call (after the palettes are
-- registered, below) is also how the engine detects "Auto" and swaps its
-- built-in light/dark palette to match the system.
local function is_macos_dark_appearance()
  local handle = io.popen('defaults read -g AppleInterfaceStyle 2>/dev/null')
  if not handle then return true end
  local result = handle:read('*a') or ''
  handle:close()
  return result:find('Dark') ~= nil
end

local function resolve_appearance_color_scheme()
  local gui = wezterm.gui
  if gui and type(gui.get_appearance) == 'function' then
    local ok, appearance = pcall(gui.get_appearance)
    if ok and type(appearance) == 'string' then
      return appearance:find('Dark', 1, true) and 'Kaku Dark' or 'Kaku Light'
    end
  end
  return is_macos_dark_appearance() and 'Kaku Dark' or 'Kaku Light'
end

local function resolve_kaku_color_scheme(scheme)
  if scheme == 'Auto' then return resolve_appearance_color_scheme() end
  if not scheme or scheme == '' then return resolve_appearance_color_scheme() end
  return scheme
end
config.window_decorations = 'INTEGRATED_BUTTONS|RESIZE'

-- ════════════════════════════════════════════════════════════
-- Rendering / typography — aligned with Kaku's bundled config so glyphs,
-- spacing and font weights match the Kaku aesthetic. (The 'Kaku Dark' color
-- scheme itself is built into the binary; this block is the font + render
-- polish that Kaji's rewritten kaku.lua had dropped.)
-- Kaji is dark-only, so we use Kaku's dark-theme weights statically:
--   base = Regular, bold = Medium.
-- ════════════════════════════════════════════════════════════

-- Low-resolution screen detection drives font size + window padding (like Kaku).
local function helm_is_low_res()
  local ok, screens = pcall(function() return wezterm.gui.screens() end)
  if ok and screens and screens.main then
    local m = screens.main
    local short_edge = math.min(tonumber(m.width or 0) or 0, tonumber(m.height or 0) or 0)
    local name = string.lower(tostring(m.name or ''))
    local builtin = name == 'color lcd'
      or string.find(name, 'built-in', 1, true)
      or string.find(name, 'built in', 1, true)
      or string.find(name, '内建', 1, true)
    if short_edge > 0 then
      if builtin then return short_edge <= 1700 end
      return short_edge < 1800
    end
  end
  return false
end
local helm_low_res = helm_is_low_res()

-- Font stack: JetBrains Mono (bundled) + Nerd symbols + PingFang SC (CJK) + emoji
config.font = wezterm.font_with_fallback({
  { family = 'JetBrains Mono', weight = 'Regular' },
  { family = 'Symbols Nerd Font Mono' },
  { family = 'PingFang SC', weight = 'Regular' },
  'Apple Color Emoji',
})
config.font_rules = {
  -- Half intensity: keep base weight (avoid thin)
  { intensity = 'Half', font = wezterm.font_with_fallback({
    { family = 'JetBrains Mono', weight = 'Regular' },
    { family = 'Symbols Nerd Font Mono' },
    { family = 'PingFang SC', weight = 'Regular' },
    'Apple Color Emoji',
  })},
  -- Italic: disable real italics (keep upright, like Kaku)
  { intensity = 'Normal', italic = true, font = wezterm.font_with_fallback({
    { family = 'JetBrains Mono', weight = 'Regular', italic = false },
    { family = 'Symbols Nerd Font Mono' },
    { family = 'PingFang SC', weight = 'Regular' },
    'Apple Color Emoji',
  })},
  -- Bold: heavier weight
  { intensity = 'Bold', font = wezterm.font_with_fallback({
    { family = 'JetBrains Mono', weight = 'Medium' },
    { family = 'Symbols Nerd Font Mono' },
    { family = 'PingFang SC', weight = 'Medium' },
    'Apple Color Emoji',
  })},
}

-- Auto font size by screen DPI (Kaku: 15 on low-res, 17 otherwise)
config.font_size = helm_low_res and 15.0 or 17.0
config.line_height = 1.28
config.cell_width = 1.0
config.bold_brightens_ansi_colors = false
config.use_cap_height_to_scale_fallback_fonts = false
config.harfbuzz_features = { 'calt=0', 'clig=0', 'liga=0' }
config.custom_block_glyphs = true
config.unicode_version = 14

-- Cursor (Kaku: sharp blinking bar)
config.default_cursor_style = 'BlinkingBar'
config.cursor_thickness = '2px'
config.cursor_blink_rate = 500
config.cursor_blink_ease_in = 'Constant'
config.cursor_blink_ease_out = 'Constant'

-- Scrollback / selection / window
config.scrollback_lines = 10000
config.selection_word_boundary = ' \t\n{}[]()"\'-'
config.use_resize_increments = false
config.window_background_opacity = 1.0
config.text_background_opacity = 1.0
config.window_padding = helm_low_res
  and { left = '26px', right = '26px', top = '26px', bottom = '0px' }
  or  { left = '40px', right = '40px', top = '40px', bottom = '0px' }

-- Initial window size (Kaku defaults)
config.initial_cols = 110
config.initial_rows = 22

-- ════════════════════════════════════════════════════════════
-- Color scheme — 'Kaku Dark' palette ported from Kaku so the background and
-- ANSI colors match exactly (soft charcoal #15141b, not pure black). Kaji's
-- rewritten config had dropped this, leaving a flat pure-black fallback.
-- ════════════════════════════════════════════════════════════
local KAKU = {
  BLACK = '#15141b',
  ANSI_BLACK = '#110f18',
  WHITE = '#d5d4d6',
  GRAY = '#6d6d6d',
  PURPLE = '#8e6ad9',
  PURPLE_FADING = 'rgba(61,55,94,0.5)',
  SURFACE = '#1f1d28',
  SURFACE_ACTIVE = '#29263c',
  GREEN = '#58d8ad',
  ORANGE = '#daae76',
  PINK = '#d383da',
  BLUE = '#68afda',
  BRIGHT_BLUE = '#90c9e6',
  RED = '#d85d5d',
}

local kaku_theme = {
  foreground = KAKU.WHITE,
  background = KAKU.BLACK,
  cursor_bg = '#f25c05',   -- Kaji persimmon: the cursor is where you act
  cursor_fg = KAKU.BLACK,
  cursor_border = '#f25c05',
  selection_bg = 'rgba(242,92,5,0.28)',
  selection_fg = 'none',
  ansi = {
    KAKU.ANSI_BLACK, KAKU.RED, KAKU.GREEN, KAKU.ORANGE,
    KAKU.BLUE, KAKU.PURPLE, KAKU.GREEN, KAKU.WHITE,
  },
  brights = {
    KAKU.GRAY, KAKU.RED, KAKU.GREEN, KAKU.ORANGE,
    KAKU.BRIGHT_BLUE, KAKU.PURPLE, KAKU.GREEN, KAKU.WHITE,
  },
  split = KAKU.SURFACE_ACTIVE,
  color_overrides = {
    ['#6d6d6d'] = '#3A3942',
    ['#6E6E6E'] = '#3A3942',
    ['#8EC3FF'] = '#3A3942',
  },
}

config.color_schemes = config.color_schemes or {}
config.color_schemes['Kaku Dark'] = kaku_theme
config.color_schemes['Kaku Theme'] = kaku_theme

-- 'Kaku Light' — Kaku's warm cream palette (#FFFCF0 bg), ported verbatim so
-- Auto mode shows the same warm light theme Kaku does in daylight.
local kaku_light = {
  foreground = '#100F0F',
  background = '#FFFCF0',
  cursor_bg = '#343331',
  cursor_fg = '#FFFCF0',
  cursor_border = '#343331',
  selection_bg = '#E8E6DB',
  selection_fg = '#100F0F',
  ansi = {
    '#100F0F', '#AF3029', '#536907', '#8E6B02',
    '#205EA6', '#A02F6F', '#1C6C66', '#575653',
  },
  brights = {
    '#6F6E69', '#C03E35', '#66790D', '#8E6B02',
    '#3171B2', '#B74583', '#2F968D', '#403E3C',
  },
  scrollbar_thumb = '#C9C2B1',
  split = '#DDDBCF',
  tab_bar = {
    background = '#FFFCF0',
    inactive_tab_edge = '#FFFCF0',
    active_tab   = { bg_color = '#E8E6DB', fg_color = '#100F0F', intensity = 'Bold' },
    inactive_tab = { bg_color = '#FFFCF0', fg_color = '#4A4946', intensity = 'Normal' },
    inactive_tab_hover = { bg_color = '#E8E6DB', fg_color = '#100F0F', italic = false },
    new_tab       = { bg_color = '#FFFCF0', fg_color = '#4A4946' },
    new_tab_hover = { bg_color = '#E8E6DB', fg_color = '#100F0F' },
  },
  color_overrides = {
    ['#575653'] = '#F2F0EB', ['#585754'] = '#F2F0EB', ['#225FA6'] = '#F2F0EB',
    ['#205EA6'] = '#F2F0EB', ['#1C6C66'] = '#F2F0EB', ['#536907'] = '#F2F0EB',
    ['#8E6B02'] = '#F2F0EB',
  },
  -- Pale agent/Claude Code text that is readable on dark themes but nearly
  -- invisible against the cream background — remap to a legible base tone.
  -- Ported verbatim from Kaku Light, which is why Kaku has no contrast issue.
  foreground_color_overrides = {
    ['#FFFFDB'] = '#575653',  -- pale yellow text
    ['#FFFFDC'] = '#575653',  -- pale yellow text variant
  },
}
config.color_schemes['Kaku Light'] = kaku_light

-- Resolve the scheme against the system appearance (Kaku's mechanism). Keeping
-- the literal call `resolve_kaku_color_scheme(...)` on this line is also what
-- lets the engine recognise Auto mode and swap its built-in palette.
config.color_scheme = (wezterm.gui and wezterm.gui.get_appearance() or 'Dark'):find('Dark') and 'Kaku Dark' or 'Kaku Light'

-- ════════════════════════════════════════════════════════════
-- Behaviour / window settings — ported from Kaku so Kaji matches its feel:
-- dark title bar, no close prompts, WebGpu rendering, macOS key handling.
-- ════════════════════════════════════════════════════════════

-- Title bar — theme-aware so it matches the terminal background (cream in Kaku
-- Light, charcoal in Kaku Dark). Mirrors Kaku's get_window_frame_colors.
local _is_light = (config.color_scheme == 'Kaku Light')
config.window_frame = {
  font = wezterm.font({ family = 'JetBrains Mono', weight = 'Regular' }),
  font_size = 14.0,
  active_titlebar_bg            = _is_light and '#FFFCF0' or KAKU.BLACK,
  inactive_titlebar_bg          = _is_light and '#F8F5EA' or KAKU.BLACK,
  active_titlebar_fg            = _is_light and '#100F0F' or KAKU.WHITE,
  inactive_titlebar_fg          = _is_light and '#575653' or KAKU.GRAY,
  active_titlebar_border_bottom = _is_light and '#E8E1D0' or KAKU.BLACK,
  inactive_titlebar_border_bottom = _is_light and '#EDE6D6' or KAKU.BLACK,
  border_left_width = 0,
  border_right_width = 0,
  border_top_height = 0,
  border_bottom_height = 0,
}

-- Close protection: never prompt (Kaku's smart-skip behaviour). This also
-- removes the close-confirmation overlay that used to reference the old name.
config.window_close_confirmation = 'NeverPrompt'
config.tab_close_confirmation = false
config.pane_close_confirmation = false
config.quit_when_all_windows_are_closed = false

-- macOS behaviour
config.native_macos_fullscreen_mode = true
config.send_composed_key_when_left_alt_is_pressed = false
config.send_composed_key_when_right_alt_is_pressed = true

-- Rendering smoothness. NOTE: we deliberately do NOT set front_end='WebGpu'
-- here — scrolling worked on the default front end before this change and
-- WebGpu appeared to break mouse-wheel scrolling on this build. Leave default.
config.animation_fps = 60
config.max_fps = 60
config.enable_scroll_bar = false
config.status_update_interval = 1000

-- Environment: COLORFGBG hints dark background to TUI apps
config.set_environment_variables = config.set_environment_variables or {}
config.set_environment_variables['COLORFGBG'] = (config.color_scheme == 'Kaku Light') and '0;15' or '15;0'

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

-- NOTE: we deliberately do NOT set config.restore_previous_session = true.
-- WezTerm's native session restore fights Kaji's own gui-startup (which boots
-- into the Brain and rebuilds Kaji-tracked worker sessions from runtime.json),
-- causing stale plain-shell tabs to cover the Brain on launch. Kaji owns startup.

-- ════════════════════════════════════════════════════════════
-- Kaji 🎯 — agent-native terminal layer (on top of WezTerm/Kaku)
-- Organized as one namespace; sub-tables map to the 3 layers.
-- To add a harness: add a row to Kaji.harnesses.list
-- To add a keybind:  add to Kaji.keys.bind(config)
-- ════════════════════════════════════════════════════════════
local Helm = {}

-- ── Tuning constants ────────────────────────────────────────
--   IDLE_THRESHOLD : secs of stable pane content before a session is 'waiting'
--   LRU_LIMIT      : max sessions shown in the Cmd+Shift+S overlay (most-recent first)
--   FP_LINES       : trailing lines hashed for the content-change fingerprint
--   RUNTIME_JSON   : where session state is persisted across restarts
Helm.cfg = {
  IDLE_THRESHOLD = 3,
  LRU_LIMIT      = 6,
  FP_LINES       = 12,
  -- Cooldown (secs) between two WAITING notifications for the SAME pane. Agent
  -- TUIs (e.g. Claude Code) often flap working→waiting→working→waiting within a
  -- second or two after a task finishes — a cursor/spinner/"esc to interrupt"
  -- redraw changes the content fingerprint — which would fire a duplicate
  -- notify. This suppresses the repeat while still allowing a genuine new
  -- waiting after real subsequent work.
  NOTIFY_COOLDOWN = 20,
  RUNTIME_JSON   = (os.getenv('HOME') or '/tmp') .. '/.helm/sessions/runtime.json',
  -- Busy markers (#139): when the trailing pane text contains one of these,
  -- the agent is mid-task no matter how long the fingerprint stays stable —
  -- a long tool run / generation can freeze the screen for >IDLE_THRESHOLD
  -- and must NOT flip the session to 'waiting'. Lowercase substrings.
  BUSY_MARKERS = {
    'esc to interrupt',      -- claude code / codex while working
    'ctrl+c to interrupt',
    'esc again to interrupt',
    'running…', 'running...',
    'thinking…', 'thinking...',
  },
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

-- Pane → harness, looking at the foreground process's NAME and ARGV. The
-- executable alone misses node-shim CLIs (codex runs as `node …/bin/codex`,
-- so the process name is just "node") — argv carries the real identity.
function Helm.harnesses.detect_pane(pane)
  local okn, proc = pcall(function() return pane:get_foreground_process_name() end)
  local hit = okn and Helm.harnesses.detect(proc) or nil
  if hit then return hit end
  local oki, info = pcall(function() return pane:get_foreground_process_info() end)
  if not (oki and info) then return nil end
  local argv = info.argv or {}
  for i = 1, math.min(#argv, 3) do
    hit = Helm.harnesses.detect(tostring(argv[i]))
    if hit then return hit end
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

-- True when the trailing pane text shows a known in-progress marker (#139):
-- a stable screen with "esc to interrupt" on it is a WORKING agent whose
-- output happens to be frozen, not one waiting for input.
function Helm.sessions.looks_busy(text)
  local lower = (text or ''):lower()
  for _, m in ipairs(Helm.cfg.BUSY_MARKERS) do
    if lower:find(m, 1, true) then return true end
  end
  return false
end

-- Update or insert a session record for this pane.
-- State detection via idle heuristic: content changing = working,
-- content stable > IDLE_THRESHOLD = waiting (agent finished, awaiting input).
function Helm.sessions.track(pane)
  local sessions = wezterm.GLOBAL.helm_sessions
  local id = tostring(pane:pane_id())
  local sessions0 = wezterm.GLOBAL.helm_sessions or {}
  local known = sessions0[tostring(pane:pane_id())]
  -- Detection OR registration: kaji-brain spawn registers sessions it creates
  -- (runtime.json → boot restore → helm_sessions), so a node-shim harness
  -- whose process name defeats detect_pane() still gets tracked.
  local harness = Helm.harnesses.detect_pane(pane) or (known and known.harness)
  if not harness then return end  -- unknown pane: not a worker
  -- The Brain (and the other dedicated slots) are agent sessions too, but they
  -- are NOT workers. Never record them in helm_sessions/runtime.json: otherwise
  -- the Brain shows up as a "session" in the Monitor and — worse — kaji-brain
  -- spawn would pick the Brain pane as a split anchor and tile a worker right
  -- next to the Brain instead of opening the Work tab.
  if not Helm.workspace.is_worker(pane:pane_id()) then return end

  local t = Helm.util.now()
  -- cheap content fingerprint of the trailing FP_LINES lines: length + sampled byte sum
  -- (get_lines_as_text returns a String in this engine, not a table)
  local text = pane:get_lines_as_text(Helm.cfg.FP_LINES)
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
      elseif (t - (s.last_change or t)) > Helm.cfg.IDLE_THRESHOLD
          and not Helm.sessions.looks_busy(text) then
        -- working → waiting transition: fire the Brain event exactly ONCE
        -- (the guard `s.state ~= 'waiting'` prevents re-firing every idle tick).
        if s.state ~= 'waiting' then
          s.state = 'waiting'
          -- Suppress duplicate notifications from a working↔waiting flap (TUI
          -- redraw right after a task ends): only notify if past the cooldown.
          if (t - (s.last_notify or 0)) > Helm.cfg.NOTIFY_COOLDOWN then
            s.last_notify = t
            Helm.brain.notify_waiting(id, s.harness, s.cwd)
          end
        end
      end
    end
  end
  wezterm.GLOBAL.helm_sessions = sessions
  Helm.sessions.save()
end

-- Adopt sessions registered by kaji-brain spawn (runtime.json) that this
-- process hasn't seen yet — the registrar knows harness/cwd, so a node-shim
-- harness gets tracked even when process detection can't name it. Throttled.
function Helm.sessions.adopt()
  local now = Helm.util.now()
  if (now - (wezterm.GLOBAL.helm_last_adopt or 0)) < 5 then return end
  wezterm.GLOBAL.helm_last_adopt = now
  local f = io.open(Helm.cfg.RUNTIME_JSON, 'r')
  if not f then return end
  local body = f:read('*a'); f:close()
  local ok, data = pcall(wezterm.json_parse, body)
  if not (ok and type(data) == 'table') then return end
  local sessions = wezterm.GLOBAL.helm_sessions or {}
  local changed = false
  for id, rec in pairs(data) do
    if not sessions[id] and type(rec) == 'table' and rec.harness then
      sessions[id] = {
        harness       = rec.harness,
        cwd           = rec.cwd,
        cwd_full      = rec.cwd_full,
        start_time    = rec.start_time or now,
        last_accessed = rec.last_accessed or now,
        state         = rec.state or 'working',
      }
      changed = true
    end
  end
  if changed then wezterm.GLOBAL.helm_sessions = sessions end
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
  if not f then
    -- Parent dir may be missing on a fresh machine (first_run not yet run).
    -- io.open('w') fails silently in that case, which would leave the Monitor
    -- permanently empty. Create it and retry once so tracking self-heals.
    os.execute('mkdir -p "' .. Helm.cfg.RUNTIME_JSON:gsub('/[^/]*$', '') .. '"')
    f = io.open(Helm.cfg.RUNTIME_JSON, 'w')
  end
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

-- Calm, low-saturation palette for the view compass — theme-aware so the dots
-- stay readable on both the cream (Kaku Light) and charcoal (Kaku Dark) bar.
local _light_status = (config.color_scheme == 'Kaku Light')
-- Hand the scheme to spawned TUIs (Brain cockpit picks Sun Day/Night by it).
wezterm.GLOBAL.helm_theme = _light_status and 'light' or 'dark'
Helm.status.palette = {
  dim    = _light_status and '#9A988F' or '#565f73',  -- inactive dots
  text   = _light_status and '#403E3C' or '#a9b1d6',  -- primary text
  accent = '#f25c05',  -- active view + waiting quota: ONE persimmon, both themes
}

-- format-tab-title: the bar is now a single clean status line, so tabs shrink
-- to a tiny marker (active ● / inactive ·) instead of boxy browser tabs.
-- The agent + project info now lives in the LEFT status zone (render).
-- format-tab-title: the 4-dot view compass (left status) is now the single
-- source of navigation, so per-tab markers would just add a second, confusing
-- set of dots. Render tabs as blank — the compass tells you where you are.
-- format-tab-title: the 4-dot view compass (left status) is the single source
-- of navigation, so we blank the per-tab title. Return a SPACE, not '' — an
-- empty string makes wezterm fall back to the default (cwd) title, which is
-- where the stray "Users/Users/" came from.
function Helm.status.tab_title(tab)
  -- Tabs are intentionally blank: the view compass (left status) is the single
  -- source of tab identity. Returning a space renders an empty tab cell; the
  -- engine's cwd fallback (which would surface "Users/") is disabled in
  -- tabbar.rs for the None case so this stays blank even mid config-reload.
  return ' '
end

-- Which of the four views the given pane belongs to (1=Brain 2=Work 3=Monitor
-- 4=Terminal). Derived by comparing the pane id against the cached view slots;
-- anything that isn't Brain/Monitor/Terminal is a Work(er) pane.
function Helm.status.current_view(pane)
  local id = pane:pane_id()
  if id == wezterm.GLOBAL.helm_brain_pane    then return 1 end
  if id == wezterm.GLOBAL.helm_top_pane      then return 3 end
  if id == wezterm.GLOBAL.helm_terminal_pane then return 4 end
  return 2  -- Work
end

-- Liveness of each view, used to render the compass dynamically: a dot only
-- shows for a view that currently exists. Brain is always considered live (you
-- never "close" it — closing the Brain quits Kaji).
function Helm.status.work_alive()
  if Helm.workspace.empty_pane() then return true end
  for _, win in ipairs(wezterm.mux.all_windows()) do
    for _, tab in ipairs(win:tabs()) do
      for _, p in ipairs(tab:panes()) do
        if Helm.workspace.is_worker(p:pane_id()) then return true end
      end
    end
  end
  return false
end

-- update-right-status render: a dynamic VIEW COMPASS. One dot per LIVE view, in
-- fixed order (Brain · Work · Monitor · Terminal); the view you're in lights up
-- in Kaji persimmon with its name, the rest stay dim. Closing a view drops its dot.
function Helm.status.render(window, pane)
  local P = Helm.status.palette
  local view = Helm.status.current_view(pane)

  -- The standalone Settings TUI is spawned as `helm config` in its own window
  -- (see frontend.rs open_kaku_config). When the active pane is that process,
  -- the view compass is meaningless here — show a single "Settings" label so
  -- the top bar matches the screen instead of falling back to "Work".
  do
    local okp, proc = pcall(function() return pane:get_foreground_process_name() end)
    if okp and type(proc) == 'string' then
      local base = proc:match('[^/]+$') or proc
      if base == 'helm' or base == 'kaku' then
        local label = '● Settings'
        local w = 2 + #('Settings')
        local cols = 0
        local okd, d = pcall(function() return pane:get_dimensions() end)
        if okd and d and d.cols then cols = d.cols end
        local pad = math.floor((cols - w) / 2) - 8
        if pad < 0 then pad = 0 end
        window:set_left_status(wezterm.format({
          { Text = string.rep(' ', pad) },
          { Foreground = { Color = P.accent } },
          { Text = label },
        }))
        window:set_right_status('')
        return
      end
    end
  end

  local slots = {
    { idx = 1, name = 'Mission Control', live = true },                      -- always
    { idx = 2, name = 'Work',            live = Helm.status.work_alive() },
    { idx = 4, name = 'Terminal',        live = Helm.workspace.terminal_pane() ~= nil },
  }

  -- build the compass and measure its display width (in cells)
  local elems = {}
  local w = 0
  local first = true
  for _, s in ipairs(slots) do
    if s.live then
      if not first then
        elems[#elems+1] = { Text = '   ' }  -- separator
        w = w + 3
      end
      first = false
      if s.idx == view then
        elems[#elems+1] = { Foreground = { Color = P.accent } }
        elems[#elems+1] = { Text = '● ' .. s.name }
        w = w + 2 + #s.name
      else
        elems[#elems+1] = { Foreground = { Color = P.dim } }
        elems[#elems+1] = { Text = '·' }
        w = w + 1
      end
    end
  end

  -- center the compass across the window (approx via the active pane's columns).
  -- The integrated macOS traffic-light buttons sit at the bar's left and push
  -- left_status to the right, so subtract their width (~cells) to compensate.
  local BUTTON_CELLS = 8
  local cols = 0
  local ok, d = pcall(function() return pane:get_dimensions() end)
  if ok and d and d.cols then cols = d.cols end
  local pad = math.floor((cols - w) / 2) - BUTTON_CELLS
  if pad < 0 then pad = 0 end
  table.insert(elems, 1, { Text = string.rep(' ', pad) })

  window:set_left_status(wezterm.format(elems))
  -- Right edge: quota water level + the one navigation hint that matters.
  local dest = (view == 1) and 'Work' or 'Mission Control'
  local right = {}
  local pct = Helm.status.quota_pct()
  if pct then
    -- persimmon means "needs you" everywhere in Kaji; ≥80% the budget does.
    table.insert(right, { Foreground = { Color = (pct >= 80) and P.accent or P.dim } })
    table.insert(right, { Text = '5h ' .. pct .. '%   ' })
  end
  table.insert(right, { Foreground = { Color = P.dim } })
  table.insert(right, { Text = '⌘/ ' .. dest .. '  ' })
  window:set_right_status(wezterm.format(right))
end

-- Claude 5h-window usage percent, read from helm-quota's 180s disk cache.
-- File read throttled to one per 10s; zero API calls from the Lua side.
function Helm.status.quota_pct()
  local now = os.time()
  local g = wezterm.GLOBAL
  if not g.helm_quota_ts or (now - g.helm_quota_ts) > 10 then
    g.helm_quota_ts = now
    local f = io.open(wezterm.home_dir .. '/.helm/sessions/claude-limits-cache.json', 'r')
    if f then
      local raw = f:read('*a')
      f:close()
      local ok, data = pcall(wezterm.json_parse, raw)
      if ok and type(data) == 'table' and tonumber(data.five_hour_used_percent) then
        g.helm_quota_pct = math.floor(tonumber(data.five_hour_used_percent) + 0.5)
      end
    end
  end
  return g.helm_quota_pct
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
    wezterm.executable_dir:gsub('MacOS/?$', 'Resources') .. '/tools/kaji-brain/launch-brain.sh',
    home .. '/workspace/helm-terminal/tools/kaji-brain/launch-brain.sh',
    home .. '/.config/kaku/tools/kaji-brain/launch-brain.sh',
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
          -- activate the PANE too: tab:activate() alone leaves focus on the
          -- tab's previously-active pane — with same-tab splits the compass
          -- (and keystrokes) stayed on the Brain after a "switch".
          pcall(function() p:activate() end)
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
  local theme = wezterm.GLOBAL.helm_theme or 'dark'
  local tab, pane = mux_window:spawn_tab {
    args = { '/bin/bash', '-l', '-c',
      "KAJI_THEME=" .. theme .. " exec '" .. launcher .. "'" },
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
      -- currently on the Brain → flip back to the worker we came from;
      -- if that's gone (or we never came from one), any live worker will do.
      local last = wezterm.GLOBAL.helm_last_worker
      if not (last and Helm.brain.focus_pane(last)) then
        wezterm.GLOBAL.helm_last_worker = nil
        for _, win in ipairs(wezterm.mux.all_windows()) do
          for _, tab in ipairs(win:tabs()) do
            for _, p in ipairs(tab:panes()) do
              if Helm.workspace.is_worker(p:pane_id()) then
                Helm.brain.focus_pane(p:pane_id())
                return
              end
            end
          end
        end
      end
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
  -- The cockpit TUI Brain polls fleet state itself — injected text would land
  -- in its 舵 input buffer as garbage. Only inject into an LLM-harness Brain.
  do
    local okp, proc = pcall(function() return bpane:get_foreground_process_name() end)
    if okp and type(proc) == 'string' and proc:lower():find('python', 1, true) then
      return
    end
  end
  bpane:send_text(string.format(
    '\n[helm-event] session %s (%s · %s) is now WAITING for input.\n',
    tostring(worker_id), harness or '?', project or '?'
  ))
end

-- ════════════════════════════════════════════════════════════
-- Kaji.top — the Monitor layer (helm-top, an htop-style session list)
-- ════════════════════════════════════════════════════════════
-- Philosophy: zero friction, out of the box, focus on shipping. helm-top is a
-- stdlib-only Python viewer over `kaji-brain sessions` — no deps, no state of
-- its own. You stay at the helm; this just shows who's working / waiting so you
-- can jump to the one that needs you and get back to shipping.
Helm.top = {}

-- Resolve the helm-top script once (bundle Resources, dev repo, ~/.config),
-- cached in GLOBAL. Same strategy as Kaji.brain.launcher().
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
-- Kaji.workspace — the Workspace layer (the worker panes you actually drive)
-- ════════════════════════════════════════════════════════════
Helm.workspace = {}

-- Cmd+4 Terminal slot: a dedicated plain login shell for running commands.
-- This is its OWN view, distinct from the Work(space) — it is NOT recorded as a
-- worker, so Cmd+2 never lands here. Only sets the Terminal slot id.
function Helm.workspace.spawn_terminal(window)
  local shell = os.getenv('SHELL') or '/bin/sh'
  local tab = window:mux_window():spawn_tab { args = { shell, '-l' } }
  local p = tab:active_pane()
  wezterm.GLOBAL.helm_terminal_pane = p:pane_id()
  tab:activate()
  return p
end

-- The empty-Workspace state: shown by Cmd+2 when NO agent session is running.
-- Deliberately NOT an interactive shell — Work is for agent sessions only, so
-- this is a calm branded hint that points you to the Brain. (Cmd+4 is the place
-- for a free shell.) The pane just holds the message open as a state.
function Helm.workspace.spawn_empty(window)
  local msg =
    'clear; printf "\\n\\n\\n"; ' ..
    'printf "   \\033[38;2;187;154;247m●\\033[0m  No active session\\n\\n"; ' ..
    'printf "   \\033[38;2;120;130;150mNothing is running in your Workspace right now.\\n"; ' ..
    'printf "   Press \\033[0m\\033[38;2;169;177;214m⌘/\\033[0m\\033[38;2;120;130;150m for Mission Control to start an agent,\\n"; ' ..
    'printf "   or \\033[0m\\033[38;2;169;177;214m⌘T\\033[0m\\033[38;2;120;130;150m for a free Terminal.\\033[0m\\n"; ' ..
    'while :; do sleep 86400; done'
  local tab = window:mux_window():spawn_tab { args = { '/bin/bash', '-c', msg } }
  local p = tab:active_pane()
  wezterm.GLOBAL.helm_empty_pane = p:pane_id()
  tab:activate()
  return p
end

-- Return the live empty-state hint pane, or nil (clearing the stale id).
function Helm.workspace.empty_pane()
  local id = wezterm.GLOBAL.helm_empty_pane
  if not id then return nil end
  local ok, p = pcall(wezterm.mux.get_pane, id)
  if ok and p then return p end
  wezterm.GLOBAL.helm_empty_pane = nil
  return nil
end

-- A pane is a Work(er) iff it isn't one of the dedicated slots (Brain / Monitor
-- / Terminal / the empty-state hint). Agent sessions are workers.
function Helm.workspace.is_worker(id)
  return id ~= wezterm.GLOBAL.helm_brain_pane
     and id ~= wezterm.GLOBAL.helm_top_pane
     and id ~= wezterm.GLOBAL.helm_terminal_pane
     and id ~= wezterm.GLOBAL.helm_empty_pane
end

-- Return the live Terminal-slot pane, or nil (clearing the stale id). Same
-- pattern as Kaji.top.pane()/Helm.brain.pane(): Cmd+4 is a view SLOT, not a
-- "spawn a new terminal" action — it switches back to the same shell.
function Helm.workspace.terminal_pane()
  local id = wezterm.GLOBAL.helm_terminal_pane
  if not id then return nil end
  local ok, p = pcall(wezterm.mux.get_pane, id)
  if ok and p then return p end
  wezterm.GLOBAL.helm_terminal_pane = nil
  return nil
end

-- Cmd+2: the Workspace is for AGENT SESSIONS only.
--   • return to the worker you were last on, else any live agent worker;
--   • if nothing is running, show the calm "No active session" hint (never a
--     plain terminal — that's what Cmd+4 is for).
function Helm.workspace.focus(window, _pane)
  local last = wezterm.GLOBAL.helm_last_worker
  if last and Helm.workspace.is_worker(last) and Helm.brain.focus_pane(last) then
    return
  end
  for _, win in ipairs(wezterm.mux.all_windows()) do
    for _, tab in ipairs(win:tabs()) do
      for _, p in ipairs(tab:panes()) do
        local id = p:pane_id()
        if Helm.workspace.is_worker(id) then
          wezterm.GLOBAL.helm_last_worker = id
          Helm.brain.focus_pane(id)
          return
        end
      end
    end
  end
  -- No agent session → show the empty-Workspace hint (reuse it if it's alive).
  local ep = Helm.workspace.empty_pane()
  if ep then Helm.brain.focus_pane(ep:pane_id()) else Helm.workspace.spawn_empty(window) end
end

-- Remember the current pane as "the worker" if it's an agent session (not one
-- of the dedicated slots), so Cmd+2 can return to it.
function Helm.workspace.remember(pane)
  local id = pane:pane_id()
  if Helm.workspace.is_worker(id) then
    wezterm.GLOBAL.helm_last_worker = id
  end
end

-- ════════════════════════════════════════════════════════════
-- Keybindings — all Cmd+Shift+* binds + the Cmd+L / Cmd+Shift+M overrides
-- ════════════════════════════════════════════════════════════
Helm.keys = {}

-- A small Kaji-branded yes/no confirmation, shown as a selector overlay. The
-- title carries the question; `yes_label` is the affirmative choice. `on_yes`
-- runs only if the user picks it (Esc / Cancel does nothing). Guards the
-- destructive Cmd+W paths (quitting Kaji, closing a running session).
function Helm.keys.confirm(window, pane, title, yes_label, on_yes)
  window:perform_action(
    wezterm.action.InputSelector {
      title = title,
      choices = {
        { id = 'no',  label = 'Cancel' },
        { id = 'yes', label = yes_label },
      },
      fuzzy = false,
      action = wezterm.action_callback(function(w, p, id, _label)
        if id == 'yes' and on_yes then on_yes(w, p) end
      end),
    },
    pane
  )
end

function Helm.keys.bind(config)
  config.keys = config.keys or {}

  -- ── Two views only (Kaji Sun decision): Mission Control ⇄ Work ─────────
  -- Cmd+/ flips between the Mission Control (Brain cockpit) and the worker
  -- pane you were last on. Cmd+1/2/3/4 are gone — one key, two places.
  table.insert(config.keys, {
    key = '/',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      Helm.brain.toggle(window, pane)
    end),
  })

  -- Cmd+T: the Terminal slot — a single plain login shell (focused if alive,
  -- spawned on first use). Standard terminal muscle memory; not a "view".
  table.insert(config.keys, {
    key = 't',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      Helm.workspace.remember(pane)
      local tp = Helm.workspace.terminal_pane()
      if tp then Helm.brain.focus_pane(tp:pane_id()) else Helm.workspace.spawn_terminal(window) end
    end),
  })

  -- Cmd+W: close the CURRENT view, with semantics that match Kaji's model.
  --   • Brain    → quit Kaji entirely (no Brain = no Kaji). Confirmed.. Confirmed.
  --   • Work      → close the running agent session (confirmed); if it's the
  --                 empty "no active session" hint, just close the view.
  --   • Monitor   → close the Monitor view.
  --   • Terminal  → close it, like a normal terminal.
  -- Closing a view drops its dot from the compass.
  table.insert(config.keys, {
    key = 'w',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      local view = Helm.status.current_view(pane)
      local id = pane:pane_id()
      local close = wezterm.action.CloseCurrentPane { confirm = false }
      if view == 1 then
        -- Brain → quit the whole app
        Helm.keys.confirm(window, pane,
          'Quit Kaji? The First Mate and all sessions will stop.', 'Quit Kaji',
          function(w, p) w:perform_action(wezterm.action.QuitApplication, p) end)
      elseif view == 3 then
        wezterm.GLOBAL.helm_top_pane = nil
        window:perform_action(close, pane)
      elseif view == 4 then
        wezterm.GLOBAL.helm_terminal_pane = nil
        window:perform_action(close, pane)
      else
        -- Work
        if id == wezterm.GLOBAL.helm_empty_pane then
          wezterm.GLOBAL.helm_empty_pane = nil
          window:perform_action(close, pane)
        else
          Helm.keys.confirm(window, pane,
            'Close this session? The agent running here will stop.', 'Close session',
            function(w, p)
              if wezterm.GLOBAL.helm_last_worker == p:pane_id() then
                wezterm.GLOBAL.helm_last_worker = nil
              end
              w:perform_action(wezterm.action.CloseCurrentPane { confirm = false }, p)
            end)
        end
      end
    end),
  })

  -- Cmd+,: open Settings — the Kaji config file, where every binding and option
  -- lives. (macOS Preferences convention.) Opens in a new tab with $EDITOR.
  table.insert(config.keys, {
    key = ',',
    mods = 'CMD',
    action = wezterm.action.SpawnCommandInNewTab {
      args = { '/bin/bash', '-l', '-c',
        'exec "${EDITOR:-nano}" "$HOME/.config/helm/kaku.lua"' },
    },
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

  -- Cmd+Shift+A: toggle the cockpit's dispatch mode (confirm ⇄ auto). Only
  -- meaningful on the Brain pane — forwards a Tab, which the cockpit maps to
  -- the mode switch. No-op elsewhere.
  table.insert(config.keys, {
    key = 'A',
    mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      local b = Helm.brain.pane()
      if b and pane:pane_id() == b:pane_id() then
        pane:send_text('\t')
      end
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

  -- Cmd+Shift+K: Kaji Harness Launcher 🚀 — workers live in the WORK area.
  -- Never split the pane you happen to be on (that tiled workers next to the
  -- Brain): anchor on a live worker pane and split it, or open a new tab.
  table.insert(config.keys, {
    key = 'K',
    mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      window:perform_action(
        wezterm.action.InputSelector {
          action = wezterm.action_callback(function(w, p, id, label)
            if not id then return end
            local cmd = { args = { '/bin/bash', '-l', '-c', 'exec ' .. id } }
            -- find a live worker pane to anchor on
            local anchor = nil
            for _, win in ipairs(wezterm.mux.all_windows()) do
              for _, tab in ipairs(win:tabs()) do
                for _, wp in ipairs(tab:panes()) do
                  local wid = wp:pane_id()
                  if Helm.workspace.is_worker(wid)
                     and wezterm.GLOBAL.helm_sessions
                     and wezterm.GLOBAL.helm_sessions[tostring(wid)] then
                    anchor = wp
                    break
                  end
                end
                if anchor then break end
              end
              if anchor then break end
            end
            if anchor then
              anchor:split { direction = 'Right', args = cmd.args }
            else
              w:mux_window():spawn_tab { args = cmd.args }
            end
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
          title       = '  Kaji Sessions',
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

  -- Override Cmd+L: Kaji doesn't need the built-in AI chat (use your own harness).
  -- Remap to clear screen (send Ctrl+L to the shell), the conventional terminal behavior.
  table.insert(config.keys, {
    key = 'l',
    mods = 'CMD',
    action = wezterm.action.SendKey { key = 'l', mods = 'CTRL' },
  })
end

-- ════════════════════════════════════════════════════════════
-- Hooks + wiring — call once with the config table to activate Kaji.
-- ════════════════════════════════════════════════════════════
function Helm.apply(config)
  -- Session state lives in GLOBAL so it survives config reloads.
  wezterm.GLOBAL.helm_sessions = wezterm.GLOBAL.helm_sessions or {}

  -- The help bar (bottom cheat-sheet) is VISIBLE by default; ⌘/ toggles it.
  -- Register event handlers once per CONFIG EVALUATION. A config reload builds
  -- a fresh Lua context (empty handler table), so the guard must reset with it:
  -- key it on the per-eval Helm table, NOT wezterm.GLOBAL. A GLOBAL flag
  -- survives the reload while the handlers do not — after any reload every
  -- handler was silently gone (tabs fell back to cwd titles, the compass froze).
  if not Helm.__handlers_registered then
    Helm.__handlers_registered = true

  -- The single update-right-status handler: (1) track EVERY agent pane's session
  -- (working/waiting idle heuristic) — not just the active one, so a worker in a
  -- background tab still flips working→waiting and fires notify_waiting while the
  -- captain sits in the Brain; (2) render the HUD + window title for the active
  -- pane. track() early-returns for non-worker panes, so this only costs a cheap
  -- fingerprint per live worker each ~1s tick.
  wezterm.on('update-right-status', function(win, pane)
    Helm.sessions.adopt()
    for _, w in ipairs(wezterm.mux.all_windows()) do
      for _, tab in ipairs(w:tabs()) do
        for _, p in ipairs(tab:panes()) do
          Helm.sessions.track(p)
        end
      end
    end
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
    -- Persist last run's workers so the Brain can OFFER to restore them (Y/N) on
    -- boot, instead of auto-rebuilding. Written before the live table is reset.
    do
      local lp = Helm.cfg.RUNTIME_JSON:gsub('runtime%.json$', 'last_session.json')
      local lf = io.open(lp, 'w')
      if lf then lf:write(sessions_to_json(snapshot)); lf:close() end
    end
    -- start live tracking from a clean slate: the snapshot's pane ids are stale,
    -- live panes re-register via update-right-status.
    wezterm.GLOBAL.helm_sessions = {}

    -- create the initial window running the Brain as its first tab (falls back
    -- to a plain shell if the Brain launcher can't be found)
    local launcher = Helm.brain.launcher()

    -- First-run onboarding: if there's no state.json yet, run first_run.sh once
    -- in the Brain's tab *before* the Brain takes over. first_run.sh writes
    -- ~/.config/kaku/state.json (and brain.conf, picking the Brain harness) on
    -- exit, so subsequent launches skip onboarding and land straight in the Brain.
    local home = os.getenv('HOME') or ''
    local state_file = home .. '/.config/kaku/state.json'
    local sf = io.open(state_file, 'r')
    local is_first_run = (sf == nil)
    if sf then sf:close() end
    local first_run_script = nil
    if is_first_run then
      local candidates = {
        wezterm.executable_dir:gsub('MacOS/?$', 'Resources') .. '/first_run.sh',
        home .. '/workspace/helm-terminal/assets/shell-integration/first_run.sh',
      }
      for _, p in ipairs(candidates) do
        local f = io.open(p, 'r')
        if f then f:close(); first_run_script = p; break end
      end
    end

    local spawn_args
    if launcher and first_run_script then
      -- run onboarding, then hand the same tab over to the Brain
      spawn_args = { args = { '/bin/bash', '-l', '-c',
        "bash '" .. first_run_script .. "'; exec '" .. launcher .. "'" } }
    elseif launcher then
      spawn_args = { args = { '/bin/bash', '-l', '-c', "exec '" .. launcher .. "'" } }
    else
      spawn_args = (cmd or {})
    end
    -- Size the startup window explicitly to the configured initial dimensions.
    -- Without this, the gui-startup-spawned window does NOT inherit
    -- config.initial_cols/initial_rows (unlike Cmd+N), so the first window came
    -- up at a different size than every subsequent window.
    if type(spawn_args) == 'table' then
      spawn_args.width  = config.initial_cols
      spawn_args.height = config.initial_rows
    end
    local ok, brain_tab, _brain_pane, mux_window = pcall(wezterm.mux.spawn_window, spawn_args)
    if not ok or not mux_window then return end
    if launcher then
      wezterm.GLOBAL.helm_brain_tab  = brain_tab:tab_id()
      wezterm.GLOBAL.helm_brain_pane = _brain_pane:pane_id()
    end

    -- Restore is now Brain-driven (opt-in): we do NOT auto-rebuild workers here.
    -- The snapshot was saved to last_session.json above; on boot the Brain runs
    -- `kaji-brain last-session` and offers the captain a Y/N restore (see the
    -- helm-first-mate skill), respawning via `kaji-brain spawn` so restored
    -- workers tile into the Work view exactly like fresh ones.

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

  end  -- end helm_handlers_registered guard

  Helm.keys.bind(config)
end

-- ── Kaji bottom status bar ──────────────────────────────────
-- WezTerm renders status text ON the tab bar (no standalone status widget),
-- so to get a single clean status LINE at the very bottom and NO boxy tabs at
-- the top we: keep the tab bar enabled (it hosts the status text), switch it to
-- the retro/text style, push it to the bottom, and recolor tabs so they blend
-- into the bar (the tiny ● / · markers come from Kaji.status.tab_title).
config.enable_tab_bar = true            -- MUST stay true: hosts set_left/right_status
config.use_fancy_tab_bar = false        -- retro/text style — no rounded tab boxes
config.tab_bar_at_bottom = false
config.hide_tab_bar_if_only_one_tab = false  -- always show the status line
config.show_new_tab_button_in_tab_bar = false
config.tab_max_width = 6                -- markers are tiny; keep them tight

config.colors = config.colors or {}
if _is_light then
  config.colors.tab_bar = {
    background = '#FFFCF0',
    active_tab         = { bg_color = '#FFFCF0', fg_color = '#100F0F' },
    inactive_tab       = { bg_color = '#FFFCF0', fg_color = '#9A988F' },
    inactive_tab_hover = { bg_color = '#E8E6DB', fg_color = '#100F0F', italic = false },
    new_tab            = { bg_color = '#FFFCF0', fg_color = '#9A988F' },
    new_tab_hover      = { bg_color = '#E8E6DB', fg_color = '#100F0F' },
  }
else
  config.colors.tab_bar = {
    background = '#16161e',
    active_tab         = { bg_color = '#16161e', fg_color = '#8a8fa3' },
    inactive_tab       = { bg_color = '#16161e', fg_color = '#3b4048' },
    inactive_tab_hover = { bg_color = '#16161e', fg_color = '#565f73', italic = false },
    new_tab            = { bg_color = '#16161e', fg_color = '#3b4048' },
    new_tab_hover      = { bg_color = '#16161e', fg_color = '#565f73' },
  }
end

Helm.apply(config)
return config
