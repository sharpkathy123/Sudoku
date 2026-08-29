"""Regression test: activating Hint moves real keyboard focus onto the
hinted cell, not just a purple highlight on top of a cell that isn't
actually selected/focused.

Reported live (after Tab-reaching Hint and pressing Enter/Space, not
tapping it): the hinted cell lit up purple, but the actual thing that
looked "selected" -- and the thing that still had real keyboard focus --
was the Hint button itself. Arrow keys and digit keys did nothing,
because real focus, and therefore the board's own keydown handler, never
left the button.

Root cause was two-fold:
1. showHint() only ran onCellClick(cell), which adds the "selected" CSS
   class but never moves real document.activeElement focus.
2. Even fixing (1) alone wasn't enough: a separate iOS tap-focus
   workaround (see test_tap_sets_real_focus.py) re-focuses whatever was
   actually clicked/activated on every click, including the synthetic
   click a keyboard Enter/Space produces on a focused button -- so it was
   silently stealing focus back onto the Hint button a tick later.

Fixed with moveSelectionAndFocusTo(), which updates the roving tabindex
and calls cell.focus() in addition to onCellClick(), and a shared
intentionalFocusTarget flag the iOS workaround checks so it defers to a
click handler's own deliberate focus move instead of overriding it.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.on("pageerror", lambda e: failures.append(f"page error: {e}"))
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(300)

        # Reach Hint the way the bug was reported: keyboard focus lands on
        # the button (not a tap), then it's activated with Enter -- the
        # same synthetic-click path the iOS tap-focus workaround also
        # reacts to.
        page.evaluate("() => document.getElementById('HintBtn').focus()")
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)

        info = page.evaluate(
            """() => {
                const active = document.activeElement;
                const target = hintTraceTarget;
                if (!target) return { error: 'no hintTraceTarget set after Hint' };
                const cell = board.children[target.r * 9 + target.c];
                return {
                    activeIsCell: active.classList.contains('cell'),
                    activeIsTargetCell: active === cell,
                    cellHasSelectedClass: cell.classList.contains('selected'),
                    activeId: active.id || null,
                };
            }"""
        )

        if info.get("error"):
            failures.append(info["error"])
        else:
            if not info["activeIsCell"]:
                failures.append(
                    f"real focus stayed off the board after Hint (activeElement.id={info['activeId']!r})"
                )
            if not info["activeIsTargetCell"]:
                failures.append("real focus landed on a cell, but not the one Hint actually targeted")
            if not info["cellHasSelectedClass"]:
                failures.append("the hinted cell never got the 'selected' class")

        # With real focus now on the board, an arrow key should move
        # selection immediately -- proving the board's own keydown handler
        # is actually receiving events, not the Hint button.
        before = page.evaluate("() => ({ r: selectedCell.dataset.row, c: selectedCell.dataset.col })")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(80)
        after = page.evaluate("() => ({ r: selectedCell.dataset.row, c: selectedCell.dataset.col })")
        if before == after and before["c"] != "8":
            failures.append("ArrowRight after Hint didn't move selection -- real focus wasn't actually on the board")

        browser.close()

    if failures:
        print("FAIL: Hint doesn't move real focus onto its target cell:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: activating Hint moves real keyboard focus onto the hinted cell, and arrow keys work immediately after")


if __name__ == "__main__":
    main()
