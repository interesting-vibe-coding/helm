# Release Checklist

## macOS Tab Bar Matrix

Before shipping a release that touches windowing, titlebar coloring, tab bar
layout, or transparency, build the app with `make app` and verify these macOS
config combinations manually:

| Tab position | Tab style | Opacity | Window state | Expected result |
| --- | --- | --- | --- | --- |
| Top | Fancy | Opaque | Windowed | Tab text/icons stay visible below integrated traffic lights. |
| Top | Fancy | Transparent | Windowed | Tab text/icons stay visible; transparent titlebar has no gap. |
| Top | Retro | Opaque | Windowed | Tab text/icons stay visible below integrated traffic lights. |
| Top | Retro | Transparent | Windowed | Tab text/icons stay visible; transparent titlebar has no gap. |
| Bottom | Fancy | Opaque | Windowed | Bottom tab bar is visible and top content clears traffic lights. |
| Bottom | Fancy | Transparent | Windowed | Bottom tab bar is visible; top titlebar area has no gap. |
| Bottom | Retro | Opaque | Windowed | Bottom tab bar is visible and top content clears traffic lights. |
| Bottom | Retro | Transparent | Windowed | Bottom tab bar is visible; top titlebar area has no gap. |
| Top | Fancy | Opaque | Fullscreen | Native titlebar does not cover the rendered tab bar. |
| Bottom | Fancy | Opaque | Fullscreen | Bottom tab bar remains visible after entering and leaving fullscreen. |

The key regression guard is `update_titlebar_background()` in
`window/src/os/macos/window.rs`: native titlebar coloring must remain opt-in for
opaque windows, otherwise `NSTitlebarContainerView` can cover the Metal-rendered
top tab bar.

## 0.10.0 Issue Triage

- #334 cursor disappears: the report only says the cursor sometimes disappears,
  with no repro steps. First split the investigation between the macOS mouse
  pointer path (`hide_mouse_cursor_when_typing` in
  `kaku-gui/src/termwindow/keyevent.rs`) and the terminal text cursor path
  (`kaku-gui/src/termwindow/render/pane.rs` and
  `kaku-gui/src/termwindow/render/screen_line.rs`). Do not block 0.10.0 without
  a reproducible terminal cursor failure.
- #329 copy/paste over SSH to a remote Mac mini: the report does not specify
  whether it uses plain `/usr/bin/ssh`, Kaku remote domains, OSC 52, selection
  copy, or bracketed paste. Plain SSH should still use the local pane clipboard
  path; remote-domain issues should be checked through `mux/src/ssh.rs` plus
  OSC 52 handling in `term/src/terminalstate/performer.rs`. Do not block 0.10.0
  until the failing path is identified.
