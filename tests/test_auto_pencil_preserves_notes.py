"""Regression test: Auto-Pencil must not delete a player's own pencil marks.

autoFillAllPencils() used to clear and refill every empty cell
unconditionally, silently discarding any marks a player had entered by
hand, with no warning and no undo. Fixed so a cell with even one active
mark is left completely alone; only cells with zero marks get auto-filled.

Also checks the sibling fix: pencil marks are refused entirely on a
cell that already has a placed value (previously possible with Guard
Pencil off, producing an illegible overlap of a pencil mark drawn on
top of the final digit).
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
        page.wait_for_timeout(500)

        # Hand-mark one actually-valid candidate in an empty cell.
        info = page.evaluate(
            """() => {
                const grid = getCurrentGrid();
                for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++) {
                    if (grid[r][c] === 0) {
                        for (let n = 1; n <= 9; n++) {
                            if (isSafe(grid, r, c, n)) return { idx: r * 9 + c, digit: n };
                        }
                    }
                }
            }"""
        )
        page.locator(".cell").nth(info["idx"]).click()
        page.click("#pencilToggle")
        page.wait_for_timeout(100)
        page.locator("#numberBar .number-tile").nth(info["digit"] - 1).click()
        page.wait_for_timeout(200)

        marks_before = page.evaluate(
            f"""() => {{
                const cell = document.querySelectorAll('.cell')[{info['idx']}];
                const active = [];
                for (let n = 1; n <= 9; n++) if (cell._pencilDigits[n].classList.contains('active')) active.push(n);
                return active;
            }}"""
        )
        if marks_before != [info["digit"]]:
            failures.append(f"Setup failed: hand mark wasn't applied ({marks_before})")

        page.click("#autoPencilBtn")
        page.wait_for_timeout(300)

        marks_after = page.evaluate(
            f"""() => {{
                const cell = document.querySelectorAll('.cell')[{info['idx']}];
                const active = [];
                for (let n = 1; n <= 9; n++) if (cell._pencilDigits[n].classList.contains('active')) active.push(n);
                return active;
            }}"""
        )
        if marks_after != marks_before:
            failures.append(f"Auto-Pencil altered a hand-marked cell: was {marks_before}, now {marks_after}")

        # Pencil marks must be refused on an already-filled cell, even with
        # Guard Pencil off.
        page.click("#pencilToggle")  # back to normal mode
        fill_idx = page.evaluate(
            """() => {
                const grid = getCurrentGrid();
                for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++) {
                    if (grid[r][c] === 0 && !givenMask[r][c]) return r * 9 + c;
                }
            }"""
        )
        page.locator(".cell").nth(fill_idx).click()
        correct_val = page.evaluate(
            f"() => solution[Math.floor({fill_idx}/9)][{fill_idx}%9]"
        )
        page.locator("#numberBar .number-tile").nth(correct_val - 1).click()
        page.wait_for_timeout(200)

        # Guard off, then try a pencil mark on the now-filled cell.
        guard_text = page.inner_text("#guardNotesToggle")
        if "ON" in guard_text:
            page.click("#guardNotesToggle")
        page.click("#pencilToggle")
        page.locator(".cell").nth(fill_idx).click()
        other_digit = 1 if correct_val != 1 else 2
        page.locator("#numberBar .number-tile").nth(other_digit - 1).click()
        page.wait_for_timeout(200)

        marks_on_filled = page.evaluate(
            f"""() => {{
                const cell = document.querySelectorAll('.cell')[{fill_idx}];
                const active = [];
                for (let n = 1; n <= 9; n++) if (cell._pencilDigits[n].classList.contains('active')) active.push(n);
                return active;
            }}"""
        )
        if marks_on_filled:
            failures.append(f"A pencil mark was drawn on an already-filled cell: {marks_on_filled}")

        browser.close()

    if failures:
        print("FAIL: pencil-mark safety is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: Auto-Pencil preserves hand-written notes, and filled cells refuse pencil marks")


if __name__ == "__main__":
    main()
