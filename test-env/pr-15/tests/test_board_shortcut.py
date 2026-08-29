"""Regression test: pressing "B" jumps keyboard focus onto the board.

Requested live, alongside the other letter shortcuts: once you've
tabbed off the board to reach a button, there was no shortcut back onto
it -- you had to Shift+Tab (or Tab all the way around) past every
control again. "B" (for Board) moves real focus onto whatever cell is
currently selected, or the board's own roving tab-stop cell if nothing
is selected yet, from anywhere else on the page.
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

        # Select a specific cell first (like a normal click would), then
        # tab focus away from the board entirely.
        page.evaluate("() => onCellClick(board.children[15])")
        page.evaluate("() => document.getElementById('pencilToggle').focus()")
        active_before = page.evaluate("() => document.activeElement.id")
        if active_before != "pencilToggle":
            failures.append(f"setup failed: expected focus on pencilToggle, got {active_before!r}")

        page.keyboard.press("b")
        page.wait_for_timeout(80)

        landed = page.evaluate(
            """() => ({
                activeIsCell: document.activeElement.classList.contains('cell'),
                activeIsSelectedCell: document.activeElement === board.children[15],
            })"""
        )
        if not landed["activeIsCell"]:
            failures.append("'b' didn't move focus onto the board")
        elif not landed["activeIsSelectedCell"]:
            failures.append("'b' moved focus onto the board, but not the previously selected cell")

        # From the board itself, 'b' shouldn't do anything unexpected --
        # it's a no-op there since focus is already on the board (guarded
        # implicitly: the board's own keydown handler only recognizes
        # arrows/Enter/Space/digits, and returns before reaching document's
        # shortcut listener since it doesn't preventDefault... but this
        # confirms the shortcut doesn't need special-casing to be safe).
        before_after_puzzle = page.evaluate("() => JSON.stringify(puzzle)")
        page.keyboard.press("b")
        page.wait_for_timeout(80)
        after_after_puzzle = page.evaluate("() => JSON.stringify(puzzle)")
        if before_after_puzzle != after_after_puzzle:
            failures.append("'b' pressed while already on the board unexpectedly changed the puzzle")

        browser.close()

    if failures:
        print("FAIL: the Board keyboard shortcut is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: 'b' jumps keyboard focus onto the board, landing on the previously selected cell")


if __name__ == "__main__":
    main()
