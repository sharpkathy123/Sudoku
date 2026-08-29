"""Regression test: the board, number bar, and status/toggle controls must
be operable and legible without a mouse or touch.

Before this fix, the board and number bar were plain <div>s with zero
keyboard handlers -- a keyboard-only or screen-reader user had no way to
play at all. This checks:
- Arrow keys move focus around the board (roving tabindex), and moving
  focus selects the cell, matching what a tap does.
- Digit keys 1-9, while a cell is focused, place/pencil-mark that digit
  through the same number-tile logic a mouse/touch user would trigger.
- Each cell's aria-label describes its position and state, and updates
  after a placement.
- Number tiles are focusable, have role="button", and an aria-label.
- #status is an ARIA live region, so hint/status text is announced.
- Pencil Mode / Guard Pencil toggles expose aria-pressed, kept in sync.
- The win overlay is aria-hidden until an actual win.
- The page has exactly one <h1> (was an un-preceded <h2>) inside a <main>
  landmark.
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

        # Landmarks/headings.
        if not page.evaluate("() => !!document.querySelector('h1')"):
            failures.append("No <h1> found")
        if page.evaluate("() => !!document.querySelector('h2')"):
            failures.append("An <h2> still exists (should be the page's h1 now)")
        if not page.evaluate("() => !!document.querySelector('main')"):
            failures.append("No <main> landmark found")

        # Status live region.
        status_role, status_live = page.evaluate(
            "() => [document.getElementById('status').getAttribute('role'), "
            "document.getElementById('status').getAttribute('aria-live')]"
        )
        if status_role != "status" or status_live != "polite":
            failures.append(f"#status isn't a polite live region: role={status_role!r}, aria-live={status_live!r}")

        # Win overlay hidden by default.
        if page.evaluate("() => document.getElementById('winOverlay').getAttribute('aria-hidden')") != "true":
            failures.append("#winOverlay isn't aria-hidden by default")

        # Board semantics.
        board_role, board_label = page.evaluate(
            "() => [board.getAttribute('role'), board.getAttribute('aria-label')]"
        )
        if board_role != "grid" or not board_label:
            failures.append(f"Board is missing grid role/label: role={board_role!r}, label={board_label!r}")

        # Toggle aria-pressed, kept in sync.
        if page.evaluate("() => document.getElementById('pencilToggle').getAttribute('aria-pressed')") != "false":
            failures.append("pencilToggle should start aria-pressed=false")
        if page.evaluate("() => document.getElementById('guardNotesToggle').getAttribute('aria-pressed')") != "true":
            failures.append("guardNotesToggle should start aria-pressed=true (Guard Pencil defaults ON)")
        page.click("#pencilToggle")
        if page.evaluate("() => document.getElementById('pencilToggle').getAttribute('aria-pressed')") != "true":
            failures.append("pencilToggle's aria-pressed didn't flip to true after clicking it")
        page.click("#pencilToggle")  # back to OFF for the rest of the test

        # Number tile keyboard operability.
        page.evaluate("() => document.querySelectorAll('#numberBar .number-tile')[0].focus()")
        tile_role, tile_label = page.evaluate(
            "() => [document.activeElement.getAttribute('role'), document.activeElement.getAttribute('aria-label')]"
        )
        if tile_role != "button" or not tile_label:
            failures.append(f"Number tile missing role/label: role={tile_role!r}, label={tile_label!r}")

        # Arrow-key navigation + roving tabindex + selection sync.
        page.evaluate("() => board.children[0].focus()")
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(100)
        focused_idx = page.evaluate("() => [...board.children].indexOf(document.activeElement)")
        if focused_idx != 11:  # row 1, col 2 (0-indexed) = index 11
            failures.append(f"Arrow keys didn't move focus to the expected cell (got index {focused_idx}, expected 11)")
        if not page.evaluate("() => document.activeElement === selectedCell"):
            failures.append("Moving focus with arrow keys didn't select the cell (selectedCell mismatch)")

        # Digit key placement through the real number-tile logic.
        setup = page.evaluate(
            """() => {
                const grid = getCurrentGrid();
                for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++) {
                    if (grid[r][c] === 0 && !givenMask[r][c]) return { idx: r * 9 + c, digit: solution[r][c] };
                }
            }"""
        )
        page.evaluate(f"() => board.children[{setup['idx']}].focus()")
        page.wait_for_timeout(100)
        page.keyboard.press(str(setup["digit"]))
        page.wait_for_timeout(200)
        placed = page.evaluate(f"() => board.children[{setup['idx']}].querySelector('.cell-value').textContent")
        if placed.strip() != str(setup["digit"]):
            failures.append(f"Pressing a digit key didn't place it (expected {setup['digit']}, got {placed!r})")
        label_after = page.evaluate(f"() => board.children[{setup['idx']}].getAttribute('aria-label')")
        if not label_after or "you entered" not in label_after:
            failures.append(f"aria-label wasn't updated after keyboard placement: {label_after!r}")

        browser.close()

    if failures:
        print("FAIL: keyboard/screen-reader accessibility is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: the board and controls are operable via keyboard and expose correct ARIA semantics")


if __name__ == "__main__":
    main()
