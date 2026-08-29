"""Regression test: toggling a pencil mark (or placing/rejecting a digit)
via a number tile keeps the selected cell visibly selected and keeps real
keyboard focus on the board.

Reported live: "I selected a cell, turned on pencil mode, typed the
digits I wanted to erase, and they erased, but I can't tell that the
cell is selected now. I tried hitting an arrow key to another cell, and
couldn't tell it worked; it did not cause the cell I expected to be
highlighted."

Two compounding bugs:

1. highlightSameNumbers() calls clearNumberHighlights(), which strips
   the "selected" CSS class from every cell, including the one still
   actually selected -- and nothing put it back. onCellClick() happens
   to re-add it as its own last step, which is why selecting a cell
   normally looked fine, but every number-tile branch that calls
   highlightSameNumbers() directly (wrong digit, correct digit, pencil
   toggle) never went through that last step, so the outline silently
   vanished the moment you acted on the cell you'd just selected.

2. A number tile is a real, trusted tap, so the iOS tap-focus workaround
   (see test_digit_key_keeps_board_focus.py) moves real keyboard focus
   onto the tile -- off the board entirely -- exactly like it does for
   every other button. Arrow keys require focus to be on a cell to do
   anything at all, so they went dead immediately after using the number
   bar in pencil mode, or after any digit entry via tapping.

Fixed by having highlightSameNumbers() restore "selected" on
selectedCell after clearNumberHighlights(), and by having the
number-tile handler explicitly refocus selectedCell (keepFocusOnSelectedCell())
after every branch, the same way showHint() already refocuses its own
target cell.
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

        # Pick an empty cell AND a digit that's actually safe there (not a
        # row/col/box conflict) -- otherwise Guard Pencil's own conflict
        # check fires instead, which returns before ever reaching the
        # highlightSameNumbers() call this bug lives in.
        target = page.evaluate(
            """() => {
                const grid = getCurrentGrid();
                for (let r = 0; r < 9; r++) {
                    for (let c = 0; c < 9; c++) {
                        if (puzzle[r][c] !== 0) continue;
                        for (let n = 1; n <= 9; n++) {
                            if (isSafe(grid, r, c, n)) {
                                const cell = board.children[r * 9 + c];
                                cell.tabIndex = 0;
                                onCellClick(cell);
                                cell.focus();
                                return { r, c, idx: r * 9 + c, digit: n };
                            }
                        }
                    }
                }
            }"""
        )

        # Turn on Pencil Mode (a real tap on the button).
        page.click("#pencilToggle")
        page.wait_for_timeout(80)

        # Tap a number tile (a digit confirmed safe for this cell) to
        # toggle a pencil mark on, then again to erase it.
        tile_selector = f"#numberBar .number-tile >> nth={target['digit'] - 1}"
        page.click(tile_selector)
        page.wait_for_timeout(80)
        page.click(tile_selector)  # erase it
        page.wait_for_timeout(80)

        selected_visible = page.evaluate(
            f"() => board.children[{target['idx']}].classList.contains('selected')"
        )
        if not selected_visible:
            failures.append("selected cell lost its 'selected' class after toggling a pencil mark")

        active_is_cell = page.evaluate("() => document.activeElement.classList.contains('cell')")
        if not active_is_cell:
            failures.append("real keyboard focus left the board after tapping a number tile in pencil mode")

        # With focus (allegedly) still on the board, an arrow key should
        # actually move the selection.
        before = page.evaluate(f"() => board.children[{target['idx']}] === selectedCell")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(80)
        moved = page.evaluate(
            f"() => selectedCell !== board.children[{target['idx']}] || {target['c']} === 8"
        )
        if before and not moved:
            failures.append("ArrowRight after a pencil-mark toggle didn't move selection -- focus wasn't really on the board")

        browser.close()

    if failures:
        print("FAIL: number-tile interactions break board selection/focus:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: pencil-mark toggling keeps the cell visibly selected and keeps focus on the board for arrow keys")


if __name__ == "__main__":
    main()
