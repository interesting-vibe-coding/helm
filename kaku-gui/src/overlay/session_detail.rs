//! Session-detail overlay for Kaku/Kaji.
//!
//! Activated via Ctrl+O on a focused agent pane. Renders a read-only,
//! full-pane TUI describing the session that owns this pane:
//!   1. a top **phase ribbon** (init -> active -> review, reconstructed from
//!      the event stream),
//!   2. a vertical **glyph event stream** (one row per logged event), and
//!   3. a **NOW status line** (harness, project, live state, runtime).
//!
//! Built exactly like `overlay/ai_chat`: a `TermWizTerminal` running in its own
//! thread, a raw-mode poll loop, and termwiz `Change` sequences for rendering.
//! It only READS data produced by the Lua session tracker and the Brain event
//! logger; it never writes. Every data source is optional and the overlay
//! degrades gracefully when a file is missing or malformed (never panics).
//!
//! Data sources (all under `~/.helm/sessions/`):
//!   - `runtime.json`  : `{ "<pane_id>": { harness, cwd, state, start_time, last_accessed } }`
//!   - `events.jsonl`  : one JSON object per line, `{ ts, ev, pane, ... }`

use mux::pane::PaneId;
use mux::termwiztermtab::TermWizTerminal;
use std::time::Duration;
use termwiz::cell::{unicode_column_width, AttributeChange, CellAttributes, Intensity};
use termwiz::color::{ColorAttribute, SrgbaTuple};
use termwiz::input::{InputEvent, KeyCode, Modifiers};
use termwiz::surface::{Change, CursorVisibility, Position};
use termwiz::terminal::Terminal;

// --- Palette (theme colors captured on the GUI thread) -----------------------

/// Colors sampled from Kaku's active theme on the GUI thread and passed into the
/// overlay thread so rendering adapts to the user's palette. Mirrors
/// `ai_chat::ChatPalette`'s capture-then-ship pattern.
#[derive(Clone)]
pub struct DetailPalette {
    pub bg: SrgbaTuple,
    pub fg: SrgbaTuple,
    pub border: SrgbaTuple,
}

/// Semantic state colors, derived once from the captured palette so the overlay
/// reuses the existing Kaji vocabulary (persimmon = "needs you", and nothing
/// else; calm fg = working; muted = background; ash = idle/done).
struct StateColors {
    /// SUN / persimmon -- waiting / needs you. The single meaning of orange.
    sun: SrgbaTuple,
    /// INK -- primary text / working agents.
    ink: SrgbaTuple,
    /// MUTE -- secondary text / background agents.
    mute: SrgbaTuple,
    /// ASH -- quiet / idle / done.
    ash: SrgbaTuple,
    /// Error red.
    err: SrgbaTuple,
}

fn luminance(c: SrgbaTuple) -> f32 {
    0.2126 * c.0 + 0.7152 * c.1 + 0.0722 * c.2
}

fn blend(a: SrgbaTuple, b: SrgbaTuple, amount: f32) -> SrgbaTuple {
    let t = amount.clamp(0.0, 1.0);
    SrgbaTuple(
        a.0 + (b.0 - a.0) * t,
        a.1 + (b.1 - a.1) * t,
        a.2 + (b.2 - a.2) * t,
        1.0,
    )
}

impl DetailPalette {
    fn is_light(&self) -> bool {
        luminance(self.bg) > 0.5
    }

    /// Persimmon SUN: the brand orange is theme-independent (#f25c05), with a
    /// slight darkening on light backgrounds for contrast -- matches cockpit.py.
    fn state_colors(&self) -> StateColors {
        let sun = if self.is_light() {
            SrgbaTuple(0.95, 0.36, 0.02, 1.0)
        } else {
            SrgbaTuple(0.949, 0.361, 0.02, 1.0) // #f25c05
        };
        let err = if self.is_light() {
            SrgbaTuple(0.753, 0.227, 0.169, 1.0) // #c03a2b
        } else {
            SrgbaTuple(0.878, 0.353, 0.282, 1.0) // #e05a48
        };
        StateColors {
            sun,
            ink: self.fg,
            // MUTE/ASH are derived by blending fg toward bg so they track any theme.
            mute: blend(self.fg, self.bg, 0.40),
            ash: blend(self.fg, self.bg, 0.62),
            err,
        }
    }

    fn attr(&self, fg: SrgbaTuple) -> CellAttributes {
        let mut a = CellAttributes::default();
        a.set_foreground(ColorAttribute::TrueColorWithDefaultFallback(fg));
        a.set_background(ColorAttribute::TrueColorWithDefaultFallback(self.bg));
        a
    }
    fn attr_bold(&self, fg: SrgbaTuple) -> CellAttributes {
        let mut a = self.attr(fg);
        a.apply_change(&AttributeChange::Intensity(Intensity::Bold));
        a
    }
    fn bg_color(&self) -> ColorAttribute {
        ColorAttribute::TrueColorWithDefaultFallback(self.bg)
    }
    fn plain(&self) -> CellAttributes {
        self.attr(self.fg)
    }
    fn border_cell(&self) -> CellAttributes {
        self.attr(self.border)
    }
}

// --- Context shipped from the GUI thread -------------------------------------

/// Captured on the GUI thread before entering the overlay, then moved into the
/// overlay thread. Same shape/role as `ai_chat::TerminalContext`.
pub struct SessionDetailContext {
    /// Working directory of the focused pane (best-effort; may be empty).
    pub cwd: String,
    pub colors: DetailPalette,
}

// --- Loaded session data (read from disk inside the overlay thread) ----------

#[derive(Clone, Copy, PartialEq, Eq)]
enum SessionState {
    Waiting,
    Working,
    Background,
    Idle,
    Done,
    Error,
    Unknown,
}

impl SessionState {
    fn parse(s: &str) -> Self {
        match s {
            "waiting" => SessionState::Waiting,
            "working" => SessionState::Working,
            "background" => SessionState::Background,
            "idle" => SessionState::Idle,
            "done" => SessionState::Done,
            "error" => SessionState::Error,
            _ => SessionState::Unknown,
        }
    }
    /// Status dot glyph: filled for active states, empty for inactive/terminal.
    fn glyph(self) -> &'static str {
        match self {
            SessionState::Idle | SessionState::Done => "\u{25CB}", // ○
            _ => "\u{25CF}",                                       // ●
        }
    }
    fn color(self, c: &StateColors) -> SrgbaTuple {
        match self {
            SessionState::Waiting => c.sun,
            SessionState::Working => c.ink,
            SessionState::Background => c.mute,
            SessionState::Idle | SessionState::Done => c.ash,
            SessionState::Error => c.err,
            SessionState::Unknown => c.mute,
        }
    }
    fn label(self) -> &'static str {
        match self {
            SessionState::Waiting => "waiting",
            SessionState::Working => "working",
            SessionState::Background => "background",
            SessionState::Idle => "idle",
            SessionState::Done => "done",
            SessionState::Error => "error",
            SessionState::Unknown => "unknown",
        }
    }
}

/// The "now" snapshot for this pane, read from `runtime.json`.
struct NowSnapshot {
    harness: String,
    project: String,
    state: SessionState,
    start_time: i64,
    last_accessed: i64,
}

/// One reconstructed activity event for this pane, read from `events.jsonl`.
struct ActivityEvent {
    ts: i64,
    /// "spawn" | "dispatch" | "state".
    kind: String,
    /// For "state": the target state. For "spawn": harness. Else empty.
    detail: String,
    /// Free-text payload: task (spawn) or text (dispatch).
    text: String,
}

/// Everything the overlay knows about this session after a load pass.
struct SessionData {
    now: Option<NowSnapshot>,
    events: Vec<ActivityEvent>,
    /// True when neither file yielded usable data for this pane.
    empty: bool,
    /// Number of events dropped by the cap (0 = none); for the truncation note.
    truncated: usize,
}

/// Cap on retained events to keep render cheap on very long histories.
const MAX_EVENTS: usize = 2000;

/// Path to `~/.helm/sessions/`. Returns None if HOME cannot be resolved.
fn helm_sessions_dir() -> Option<std::path::PathBuf> {
    dirs_next::home_dir().map(|h| h.join(".helm").join("sessions"))
}

/// Load the runtime.json record for `pane_id`, if present and parseable.
fn load_now(pane_id: PaneId) -> Option<NowSnapshot> {
    let dir = helm_sessions_dir()?;
    let raw = std::fs::read_to_string(dir.join("runtime.json")).ok()?;
    let root: serde_json::Value = serde_json::from_str(&raw).ok()?;
    let key = pane_id.to_string();
    let rec = root.get(&key)?;
    let harness = rec
        .get("harness")
        .and_then(|v| v.as_str())
        .unwrap_or("?")
        .to_string();
    let project = rec
        .get("cwd")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let state = SessionState::parse(rec.get("state").and_then(|v| v.as_str()).unwrap_or(""));
    let start_time = rec.get("start_time").and_then(|v| v.as_i64()).unwrap_or(0);
    let last_accessed = rec
        .get("last_accessed")
        .and_then(|v| v.as_i64())
        .unwrap_or(start_time);
    Some(NowSnapshot {
        harness,
        project,
        state,
        start_time,
        last_accessed,
    })
}

/// Load and filter events.jsonl for this pane. Corrupt lines are skipped, the
/// way `brain.read_events()` does. Oldest-first (file order). Capped to the most
/// recent `MAX_EVENTS`; the count of dropped older events is returned alongside.
fn load_events(pane_id: PaneId) -> (Vec<ActivityEvent>, usize) {
    let mut out = Vec::new();
    let dir = match helm_sessions_dir() {
        Some(d) => d,
        None => return (out, 0),
    };
    let raw = match std::fs::read_to_string(dir.join("events.jsonl")) {
        Ok(r) => r,
        Err(_) => return (out, 0),
    };
    // PaneId is a newtype over usize; compare against the integer `pane` field.
    let want = pane_id.as_usize() as i64;
    for line in raw.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let v: serde_json::Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(_) => continue, // skip corrupt line, exactly like brain.read_events
        };
        let pane = v.get("pane").and_then(|p| p.as_i64());
        if pane != Some(want) {
            continue;
        }
        let ts = v.get("ts").and_then(|t| t.as_i64()).unwrap_or(0);
        let kind = v
            .get("ev")
            .and_then(|e| e.as_str())
            .unwrap_or("?")
            .to_string();
        let (detail, text) = match kind.as_str() {
            "spawn" => (
                v.get("harness")
                    .and_then(|h| h.as_str())
                    .unwrap_or("")
                    .to_string(),
                v.get("task")
                    .and_then(|t| t.as_str())
                    .unwrap_or("")
                    .to_string(),
            ),
            "dispatch" => (
                String::new(),
                v.get("text")
                    .and_then(|t| t.as_str())
                    .unwrap_or("")
                    .to_string(),
            ),
            "state" => (
                v.get("to")
                    .and_then(|t| t.as_str())
                    .unwrap_or("")
                    .to_string(),
                String::new(),
            ),
            _ => (String::new(), String::new()),
        };
        out.push(ActivityEvent {
            ts,
            kind,
            detail,
            text,
        });
    }
    // Cap to the most-recent MAX_EVENTS; report how many were dropped.
    let truncated = out.len().saturating_sub(MAX_EVENTS);
    if truncated > 0 {
        out.drain(0..truncated);
    }
    (out, truncated)
}

fn load_session_data(pane_id: PaneId) -> SessionData {
    let now = load_now(pane_id);
    let (events, truncated) = load_events(pane_id);
    let empty = now.is_none() && events.is_empty();
    SessionData {
        now,
        events,
        empty,
        truncated,
    }
}

// --- Time / text helpers -----------------------------------------------------

fn unix_now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// "1h 23m", "4m 12s", "37s" -- compact human duration for non-negative seconds.
fn fmt_duration(secs: i64) -> String {
    let s = secs.max(0);
    if s >= 3600 {
        format!("{}h {}m", s / 3600, (s % 3600) / 60)
    } else if s >= 60 {
        format!("{}m {}s", s / 60, s % 60)
    } else {
        format!("{}s", s)
    }
}

/// Clock-of-day "HH:MM:SS". We avoid pulling in `chrono`: derive H:M:S from the
/// unix timestamp modulo a day. This is wall-clock UTC time-of-day; good enough
/// for an at-a-glance relative timeline (durations elsewhere are exact).
fn fmt_clock(ts: i64) -> String {
    if ts <= 0 {
        return "--:--:--".to_string();
    }
    let day = ts.rem_euclid(86_400);
    let h = day / 3600;
    let m = (day % 3600) / 60;
    let s = day % 60;
    format!("{:02}:{:02}:{:02}", h, m, s)
}

/// Truncate to a visual-column budget, appending an ellipsis when clipped.
fn truncate_cols(s: &str, max_cols: usize) -> String {
    if unicode_column_width(s, None) <= max_cols {
        return s.to_string();
    }
    if max_cols == 0 {
        return String::new();
    }
    let budget = max_cols.saturating_sub(1);
    let mut out = String::new();
    let mut w = 0usize;
    for ch in s.chars() {
        let cw = unicode_column_width(&ch.to_string(), None);
        if w + cw > budget {
            break;
        }
        out.push(ch);
        w += cw;
    }
    out.push('\u{2026}'); // …
    out
}

/// Pad with spaces to a visual-column width (right-pad).
fn pad_cols(s: &str, target: usize) -> String {
    let w = unicode_column_width(s, None);
    if w >= target {
        s.to_string()
    } else {
        let mut out = s.to_string();
        out.push_str(&" ".repeat(target - w));
        out
    }
}

// --- Rendering ---------------------------------------------------------------

/// A styled run: (attributes, text). The renderer concatenates runs on a row.
type Run = (CellAttributes, String);

/// Emit one bordered content row: left border, padded styled runs clipped to
/// `inner_w`, right border. Mirrors ai_chat's `emit_styled_line` shape but
/// without selection handling (this overlay is read-only and non-selectable).
fn emit_row(
    changes: &mut Vec<Change>,
    row: usize,
    inner_w: usize,
    pal: &DetailPalette,
    runs: &[Run],
) {
    changes.push(Change::CursorPosition {
        x: Position::Absolute(0),
        y: Position::Absolute(row),
    });
    changes.push(Change::AllAttributes(pal.border_cell()));
    changes.push(Change::Text("\u{2502}".to_string())); // │

    let mut used = 0usize;
    for (attr, text) in runs {
        if used >= inner_w {
            break;
        }
        let remaining = inner_w - used;
        let clipped = truncate_cols(text, remaining);
        let w = unicode_column_width(&clipped, None);
        if w == 0 {
            continue;
        }
        changes.push(Change::AllAttributes(attr.clone()));
        changes.push(Change::Text(clipped));
        used += w;
    }
    if used < inner_w {
        changes.push(Change::AllAttributes(pal.plain()));
        changes.push(Change::Text(" ".repeat(inner_w - used)));
    }

    changes.push(Change::AllAttributes(pal.border_cell()));
    changes.push(Change::Text("\u{2502}".to_string())); // │
}

/// Emit a blank bordered row.
fn emit_blank(changes: &mut Vec<Change>, row: usize, inner_w: usize, pal: &DetailPalette) {
    emit_row(changes, row, inner_w, pal, &[]);
}

/// Phase ribbon segment derived from the event stream.
struct Phase {
    glyph: &'static str,
    label: &'static str,
    color: SrgbaTuple,
    active: bool,
}

/// Reconstruct the documented three-phase timeline from the events:
///   spawn..first dispatch  = initialization
///   dispatch..state:waiting = active work
///   state:waiting..         = review / awaiting input
/// The currently-active phase is highlighted; the others are dimmed.
fn build_phases(data: &SessionData, sc: &StateColors) -> Vec<Phase> {
    let has_dispatch = data.events.iter().any(|e| e.kind == "dispatch");
    let waiting_now = matches!(
        data.now.as_ref().map(|n| n.state),
        Some(SessionState::Waiting)
    ) || data
        .events
        .last()
        .map(|e| e.kind == "state" && e.detail == "waiting")
        .unwrap_or(false);

    // Determine the live phase index: 0 init, 1 active, 2 review.
    let live = if waiting_now {
        2
    } else if has_dispatch {
        1
    } else {
        0
    };

    vec![
        Phase {
            glyph: "\u{25C6}", // ◆
            label: "init",
            color: sc.ink,
            active: live == 0,
        },
        Phase {
            glyph: "\u{25C6}", // ◆
            label: "active",
            color: sc.ink,
            active: live == 1,
        },
        Phase {
            glyph: "\u{25C6}", // ◆
            label: "review",
            color: sc.sun,
            active: live == 2,
        },
    ]
}

/// Verb for an event row in the stream.
fn event_verb(ev: &ActivityEvent) -> String {
    match ev.kind.as_str() {
        "spawn" => "spawned".to_string(),
        "dispatch" => "dispatch".to_string(),
        "state" => format!(
            "\u{2192} {}", // →
            if ev.detail.is_empty() {
                "?"
            } else {
                &ev.detail
            }
        ),
        other => other.to_string(),
    }
}

/// Build the styled runs for a single event-stream row.
fn event_row_runs(ev: &ActivityEvent, pal: &DetailPalette, sc: &StateColors) -> Vec<Run> {
    // State + color of the dot glyph for this event row.
    let state = match ev.kind.as_str() {
        "spawn" => SessionState::Working,
        "dispatch" => SessionState::Working,
        "state" => SessionState::parse(&ev.detail),
        _ => SessionState::Unknown,
    };
    let dot_color = state.color(sc);
    let glyph = match ev.kind.as_str() {
        "spawn" => "\u{25CF}",    // ●
        "dispatch" => "\u{25B8}", // ▸
        "state" => state.glyph(),
        _ => "\u{00B7}", // ·
    };

    let mut runs: Vec<Run> = Vec::new();
    runs.push((pal.attr(sc.ash), format!(" {}  ", fmt_clock(ev.ts))));
    runs.push((pal.attr(dot_color), format!("{} ", glyph)));
    runs.push((pal.attr_bold(pal.fg), pad_cols(&event_verb(ev), 10)));

    let payload = match ev.kind.as_str() {
        "spawn" if !ev.detail.is_empty() => {
            // spawn carries harness (detail) + task (text); show both compactly.
            if ev.text.is_empty() {
                format!(" {}", ev.detail)
            } else {
                format!(" {} \u{00B7} {}", ev.detail, ev.text) // ·
            }
        }
        "spawn" => format!(" {}", ev.text),
        "dispatch" => format!(" {}", ev.text),
        _ => String::new(),
    };
    if !payload.is_empty() {
        runs.push((pal.attr(sc.mute), payload));
    }
    runs
}

/// The full frame. `scroll` is the number of rows scrolled up from the bottom
/// of the event stream (0 = pinned to newest).
fn render(
    term: &mut TermWizTerminal,
    pal: &DetailPalette,
    ctx: &SessionDetailContext,
    pane_id: PaneId,
    data: &SessionData,
    scroll: usize,
) -> termwiz::Result<()> {
    let size = term.get_screen_size()?;
    let cols = size.cols.max(4);
    let rows = size.rows.max(6);
    let inner_w = cols.saturating_sub(2);
    let sc = pal.state_colors();

    let mut changes: Vec<Change> = Vec::with_capacity(rows * 6);

    // Atomic frame begin (DECSET 2026) + hide cursor, exactly like ai_chat.
    changes.push(Change::Text("\x1b[?2026h".to_string()));
    changes.push(Change::CursorVisibility(CursorVisibility::Hidden));
    changes.push(Change::AllAttributes(pal.plain()));
    changes.push(Change::ClearScreen(pal.bg_color()));

    // -- Row 0: top border with title ----------------------------------------
    let title =
        " Session Detail \u{00B7} r refresh \u{00B7} \u{2191}\u{2193} scroll \u{00B7} ESC exit ";
    let title_w = unicode_column_width(title, None);
    let fill = inner_w.saturating_sub(title_w);
    let left_fill = 1usize;
    let right_fill = fill.saturating_sub(left_fill);
    let top = format!(
        "\u{256D}{}{}{}\u{256E}", // ╭ ╮
        "\u{2500}".repeat(left_fill),
        title,
        "\u{2500}".repeat(right_fill)
    );
    changes.push(Change::CursorPosition {
        x: Position::Absolute(0),
        y: Position::Absolute(0),
    });
    changes.push(Change::AllAttributes(pal.border_cell()));
    changes.push(Change::Text(truncate_cols(&top, cols)));

    // -- Phase ribbon (rows 1-2) ---------------------------------------------
    let phases = build_phases(data, &sc);
    let mut ribbon: Vec<Run> = vec![(pal.attr(sc.mute), "  ".to_string())];
    for (i, ph) in phases.iter().enumerate() {
        if i > 0 {
            ribbon.push((pal.attr(sc.ash), "  \u{2500}\u{2500}  ".to_string()));
            // ──
        }
        let glyph_color = if ph.active { ph.color } else { sc.ash };
        let label_attr = if ph.active {
            pal.attr_bold(ph.color)
        } else {
            pal.attr(sc.ash)
        };
        ribbon.push((pal.attr(glyph_color), format!("{} ", ph.glyph)));
        ribbon.push((label_attr, ph.label.to_string()));
    }
    emit_row(&mut changes, 1, inner_w, pal, &ribbon);
    emit_blank(&mut changes, 2, inner_w, pal);

    // -- Event stream (rows 3 .. rows-3) -------------------------------------
    // Reserve: row 0 top border, rows 1-2 ribbon, last 2 rows = NOW + bottom border.
    let stream_top = 3usize;
    let stream_bottom = rows.saturating_sub(2); // exclusive
    let stream_h = stream_bottom.saturating_sub(stream_top);

    if data.empty {
        let msg = "  No session data for this pane.";
        emit_row(
            &mut changes,
            stream_top,
            inner_w,
            pal,
            &[(pal.attr(sc.mute), msg.to_string())],
        );
        let hint = "  (not a tracked worker, or runtime.json / events.jsonl missing)";
        if stream_top + 1 < stream_bottom {
            emit_row(
                &mut changes,
                stream_top + 1,
                inner_w,
                pal,
                &[(pal.attr(sc.ash), hint.to_string())],
            );
        }
        for r in (stream_top + 2)..stream_bottom {
            emit_blank(&mut changes, r, inner_w, pal);
        }
    } else if data.events.is_empty() {
        emit_row(
            &mut changes,
            stream_top,
            inner_w,
            pal,
            &[(
                pal.attr(sc.mute),
                "  No activity events recorded yet.".to_string(),
            )],
        );
        for r in (stream_top + 1)..stream_bottom {
            emit_blank(&mut changes, r, inner_w, pal);
        }
    } else {
        let total = data.events.len();
        // Reserve one row for the truncation note when older events were dropped.
        let note_rows = if data.truncated > 0 { 1 } else { 0 };
        let body_h = stream_h.saturating_sub(note_rows);

        if data.truncated > 0 && stream_h > 0 {
            emit_row(
                &mut changes,
                stream_top,
                inner_w,
                pal,
                &[(
                    pal.attr(sc.ash),
                    format!(
                        "  \u{2026} {} earlier events not shown", // …
                        data.truncated
                    ),
                )],
            );
        }
        let body_top = stream_top + note_rows;

        // Pin to newest; `scroll` walks backward from the bottom.
        let max_scroll = total.saturating_sub(body_h);
        let eff_scroll = scroll.min(max_scroll);
        let end = total.saturating_sub(eff_scroll);
        let start = end.saturating_sub(body_h);
        let visible = &data.events[start..end];

        for (i, ev) in visible.iter().enumerate() {
            let row = body_top + i;
            let runs = event_row_runs(ev, pal, &sc);
            emit_row(&mut changes, row, inner_w, pal, &runs);
        }
        // Pad any leftover stream rows.
        for r in (body_top + visible.len())..stream_bottom {
            emit_blank(&mut changes, r, inner_w, pal);
        }
    }

    // -- NOW status line (row rows-2) ----------------------------------------
    let now_row = rows.saturating_sub(2);
    let mut now_runs: Vec<Run> = Vec::new();
    if let Some(n) = &data.now {
        let runtime = fmt_duration(unix_now() - n.start_time);
        let idle = fmt_duration(unix_now() - n.last_accessed);
        now_runs.push((pal.attr_bold(pal.fg), format!("  {} ", n.harness)));
        if !n.project.is_empty() {
            now_runs.push((pal.attr(sc.mute), format!("\u{00B7} {} ", n.project)));
            // ·
        }
        now_runs.push((
            pal.attr(n.state.color(&sc)),
            format!("\u{00B7} {} ", n.state.glyph()), // ·
        ));
        now_runs.push((
            pal.attr(n.state.color(&sc)),
            format!("{} ", n.state.label()),
        ));
        now_runs.push((pal.attr(sc.ash), format!("\u{00B7} up {} ", runtime))); // ·
        now_runs.push((pal.attr(sc.ash), format!("\u{00B7} idle {}", idle))); // ·
    } else {
        // Degrade: no runtime record, but we may still know the pane + cwd.
        let cwd = if ctx.cwd.is_empty() {
            "?".to_string()
        } else {
            ctx.cwd.clone()
        };
        now_runs.push((
            pal.attr(sc.mute),
            format!("  pane {} \u{00B7} {}", pane_id, cwd),
        ));
    }
    emit_row(&mut changes, now_row, inner_w, pal, &now_runs);

    // -- Bottom border (last row) --------------------------------------------
    let bottom = format!("\u{2570}{}\u{256F}", "\u{2500}".repeat(inner_w)); // ╰ ╯
    changes.push(Change::CursorPosition {
        x: Position::Absolute(0),
        y: Position::Absolute(rows.saturating_sub(1)),
    });
    changes.push(Change::AllAttributes(pal.border_cell()));
    changes.push(Change::Text(truncate_cols(&bottom, cols)));

    // Atomic frame end (DECSET 2026 reset).
    changes.push(Change::Text("\x1b[?2026l".to_string()));

    term.render(&changes)?;
    Ok(())
}

// --- Overlay entry point -----------------------------------------------------

pub fn session_detail_overlay(
    pane_id: PaneId,
    mut term: TermWizTerminal,
    ctx: SessionDetailContext,
) -> anyhow::Result<()> {
    term.set_raw_mode()?;

    let pal = ctx.colors.clone();
    let mut data = load_session_data(pane_id);
    let mut scroll = 0usize;
    let mut needs_redraw = true;

    loop {
        if needs_redraw {
            render(&mut term, &pal, &ctx, pane_id, &data, scroll)?;
            needs_redraw = false;
        }

        match term.poll_input(Some(Duration::from_millis(500)))? {
            Some(InputEvent::Key(key)) => match (&key.key, key.modifiers) {
                // Esc / Ctrl+C / Ctrl+O / q all close the overlay.
                (KeyCode::Escape, _)
                | (KeyCode::Char('c'), Modifiers::CTRL)
                | (KeyCode::Char('C'), Modifiers::CTRL)
                | (KeyCode::Char('o'), Modifiers::CTRL)
                | (KeyCode::Char('O'), Modifiers::CTRL)
                | (KeyCode::Char('q'), Modifiers::NONE) => {
                    break;
                }
                // Reload from disk.
                (KeyCode::Char('r'), Modifiers::NONE) | (KeyCode::Char('R'), Modifiers::NONE) => {
                    data = load_session_data(pane_id);
                    scroll = 0;
                    needs_redraw = true;
                }
                // Scroll the event stream upward (toward older).
                (KeyCode::UpArrow, _) | (KeyCode::Char('k'), Modifiers::NONE) => {
                    scroll = scroll.saturating_add(1);
                    needs_redraw = true;
                }
                (KeyCode::PageUp, _) => {
                    scroll = scroll.saturating_add(10);
                    needs_redraw = true;
                }
                // Scroll back toward newest.
                (KeyCode::DownArrow, _) | (KeyCode::Char('j'), Modifiers::NONE) => {
                    scroll = scroll.saturating_sub(1);
                    needs_redraw = true;
                }
                (KeyCode::PageDown, _) => {
                    scroll = scroll.saturating_sub(10);
                    needs_redraw = true;
                }
                _ => {}
            },
            Some(InputEvent::Resized { .. }) => {
                needs_redraw = true;
            }
            Some(_) => {}
            None => {}
        }
    }

    // Clear screen before handing control back to the terminal.
    term.render(&[
        Change::AllAttributes(CellAttributes::default()),
        Change::ClearScreen(ColorAttribute::Default),
        Change::CursorVisibility(CursorVisibility::Visible),
    ])?;

    Ok(())
}
