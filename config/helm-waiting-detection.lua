-- Helm: improved agent waiting detection + macOS notifications
-- Appended to ~/.config/kaku/kaku.lua (or sourced as an overlay)
-- This block adds to the update-right-status event handler.

-- ===== Helm Agent Waiting Detection =====

local helm_agent_state = {}  -- keyed by pane_id: { state = 'working'|'waiting', last_notified = 0 }
local helm_notify_cooldown_secs = 10  -- debounce: only one notification per transition

local function helm_detect_harness(lines)
  for _, line in ipairs(lines) do
    if line:find('default %· claude%-sonnet', 1, true)
      or line:find('default · claude%-sonnet', 1, true)
      or line:find('kiro', 1, true) then
      return 'kiro'
    end
    if line:find('claude%-code', 1, true)
      or line:find('claude_code', 1, true) then
      return 'claude-code'
    end
    if line:find('opencode', 1, true) then
      return 'opencode'
    end
  end
  return nil
end

local function helm_detect_waiting(lines, harness)
  for _, line in ipairs(lines) do
    -- kiro: waiting prompt line at bottom
    if harness == 'kiro' then
      if line:find('default %· claude%-sonnet', 1, true)
        or line:find('default · claude%-sonnet', 1, true) then
        return true
      end
    end
    -- claude-code: '>' prompt or 'Waiting for your response'
    if harness == 'claude-code' then
      if line:match('^%s*>%s*$') or line:find('Waiting for your response', 1, true) then
        return true
      end
    end
    -- opencode: input prompt indicator
    if harness == 'opencode' then
      if line:match('^%s*[>»]%s*$') or line:find('Send a message', 1, true) then
        return true
      end
    end
  end
  return false
end

local function helm_maybe_notify(pane_id, harness, new_state)
  local prev = helm_agent_state[pane_id] or { state = 'unknown', last_notified = 0 }
  local now = now_secs()

  if prev.state ~= 'waiting' and new_state == 'waiting' then
    -- State transition: working → waiting
    if (now - prev.last_notified) >= helm_notify_cooldown_secs then
      local label = harness or 'Agent'
      os.execute('osascript -e \'display notification "' .. label .. ' needs your input" with title "Helm"\' &')
      helm_agent_state[pane_id] = { state = 'waiting', last_notified = now }
      return
    end
  end

  helm_agent_state[pane_id] = { state = new_state, last_notified = prev.last_notified }
end

wezterm.on('update-right-status', function(window, pane)
  -- Run Helm detection on the active pane's visible text
  local active = resolve_active_pane(window, pane)
  if not active then return end

  local pane_id_ok, pane_id_value = pcall(function() return active:pane_id() end)
  if not pane_id_ok or not pane_id_value then return end
  local pane_id = tostring(pane_id_value)

  local lines_text = ''
  pcall(function() lines_text = active:get_lines_as_text(20) or '' end)

  local lines = {}
  for line in (lines_text .. '\n'):gmatch('([^\n]*)\n') do
    lines[#lines + 1] = line
  end

  local harness = helm_detect_harness(lines)
  if harness then
    local waiting = helm_detect_waiting(lines, harness)
    helm_maybe_notify(pane_id, harness, waiting and 'waiting' or 'working')
  end
end)
