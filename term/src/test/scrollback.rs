//! Regression tests for scrollback accumulation.
//!
//! The GUI mouse-wheel → viewport-offset path can't run headless, but the
//! scrollback model it drives can: lines that scroll off the top of the screen
//! must be preserved in (and retrievable from) scrollback when scrollback is
//! enabled, and discarded when it is not. These guard against regressions in
//! the model that scrolling depends on.

use super::*;

fn line_texts(lines: &[Line]) -> Vec<String> {
    lines
        .iter()
        .map(|l| l.as_str().trim_end().to_string())
        .collect()
}

#[test]
fn scrollback_retains_scrolled_off_lines() {
    // 3 visible rows, generous scrollback.
    let mut term = TestTerm::new(3, 10, 100);
    for i in 0..10 {
        term.print(format!("line{}\r\n", i));
    }

    let screen = term.term.screen();

    // 10 lines printed into a 3-row screen → the overflow lives in scrollback,
    // so the total retained rows must exceed the visible height.
    assert!(
        screen.scrollback_rows() >= 10,
        "expected scrollback to retain the scrolled-off lines, got {} rows",
        screen.scrollback_rows()
    );

    // The oldest line must still be reachable (this is what scrolling up shows).
    let all = line_texts(&screen.all_lines());
    assert!(
        all.iter().any(|l| l == "line0"),
        "line0 should be retrievable from scrollback: {:?}",
        all
    );

    // The newest line stays on the visible screen.
    let visible = line_texts(&screen.visible_lines());
    assert!(
        visible.iter().any(|l| l == "line9"),
        "line9 should be visible: {:?}",
        visible
    );
}

#[test]
fn no_scrollback_discards_scrolled_off_lines() {
    // scrollback = 0 → scrolled-off lines are dropped, only the screen remains.
    let mut term = TestTerm::new(3, 10, 0);
    for i in 0..10 {
        term.print(format!("line{}\r\n", i));
    }

    let screen = term.term.screen();

    assert!(
        screen.scrollback_rows() <= 4,
        "expected no scrollback retention, got {} rows",
        screen.scrollback_rows()
    );

    let all = line_texts(&screen.all_lines());
    assert!(
        !all.iter().any(|l| l == "line0"),
        "line0 should have been discarded with scrollback disabled: {:?}",
        all
    );
}
