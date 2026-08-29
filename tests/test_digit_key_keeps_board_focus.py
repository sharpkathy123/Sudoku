"""Regression test: typing a digit on the keyboard doesn't steal real focus
away from the board cell onto the (invisible-to-the-player) number tile.

Reported live: "When I type a wrong digit I don't see our error message.
I do when I use the old method to enter a digit [tapping the number
tile]." Both paths call the exact same code (the board's digit-key
handler calls `numberBar.children[n-1].click()`, the same click a tap
fires), and the wrong-digit status message is set synchronously either
way -- so the DOM text was never actually missing. The real bug was
focus: the iOS tap-focus workaround (see test_tap_sets_real_focus.py)
reacts to ANY click whose target isn't the current activeElement,
including a click our own code dispatches via `.click()` -- so typing a
digit silently yanked real keyboard focus off the cell and onto the
number tile div it happens to relay through, which on a real device can
scroll that tile into view and push the status text off-screen even
though it's sitting right there in the DOM.

Fixed by gating the workaround on `event.isTrusted`, which is false for
a click dispatched by `element.click()` and true only for a genuine
tap/mouse click -- so keyboard-driven input (digit keys, and every
letter-key shortcut, which relays through a button's `.click()` the same
way) no longer moves focus off wherever Tab/arrow-keys legitimately left
it, while real taps on iOS still get the original fix.
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

        target = page.evaluate(
            """() => {
                for (let r = 0; r < 9; r++) {
                    for (let c = 0; c < 9; c++) {
                        if (puzzle[r][c] === 0) {
                            const correct = solution[r][c];
                            const wrong = correct === 9 ? 1 : correct + 1;
                            const cell = board.children[r * 9 + c];
                            cell.tabIndex = 0;
                            onCellClick(cell);
                            cell.focus();
                            return { r, c, correct, wrong };
                        }
                    }
                }
            }"""
        )

        # Typing a WRONG digit must show the status message and leave real
        # focus on the cell, not the number tile.
        page.evaluate("() => setStatusText('')")
        page.keyboard.press(str(target["wrong"]))
        page.wait_for_timeout(100)

        status = page.evaluate("() => document.getElementById('status').textContent")
        active_is_cell = page.evaluate("() => document.activeElement.classList.contains('cell')")
        active_is_target = page.evaluate(
            f"() => document.activeElement === board.children[{target['r']} * 9 + {target['c']}]"
        )

        if not status.strip():
            failures.append("no status message shown after typing a wrong digit via keyboard")
        if not active_is_cell:
            failures.append("real focus left the board (landed on the number tile) after typing a wrong digit")
        elif not active_is_target:
            failures.append("real focus moved to a different cell than the one the digit was typed into")

        # Typing the CORRECT digit afterward must also leave focus on the
        # board (now the next cell the game auto-advances to, or the same
        # cell if it doesn't) rather than the number tile.
        page.keyboard.press(str(target["correct"]))
        page.wait_for_timeout(100)
        active_is_cell_after_correct = page.evaluate("() => document.activeElement.classList.contains('cell')")
        if not active_is_cell_after_correct:
            failures.append("real focus left the board after typing the correct digit via keyboard")

        browser.close()

    if failures:
        print("FAIL: typing a digit steals focus off the board:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: typing a digit (right or wrong) shows the status message and keeps real focus on the board")


if __name__ == "__main__":
    main()
