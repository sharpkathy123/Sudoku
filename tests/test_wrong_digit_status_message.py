"""Regression test: entering a legal-but-wrong digit tells you it's wrong.

Previously a wrong digit gave zero feedback beyond a brief 400ms red flash
on the cell -- easy to miss, and gave no clue *why* it was rejected. Per
explicit product direction, this is deliberately NOT a mistake counter or
an "undo" feature -- the player doesn't want mistakes made into a big deal,
since a wrong digit was never actually written to the board in the first
place (nothing to undo). It's just a plain-language status message naming
the digit and the cell's location, using the same #status area as every
other message, so it can't overflow the fixed-height layout.
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

        info = page.evaluate(
            """() => {
                const grid = getCurrentGrid();
                for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++) {
                    if (grid[r][c] === 0 && !givenMask[r][c]) {
                        const correct = solution[r][c];
                        const wrong = correct === 9 ? 1 : correct + 1;
                        return { idx: r * 9 + c, r, c, correct, wrong };
                    }
                }
            }"""
        )

        page.locator(".cell").nth(info["idx"]).click()
        page.locator("#numberBar .number-tile").nth(info["wrong"] - 1).click()
        page.wait_for_timeout(150)

        status_text = page.inner_text("#status")
        expected = f"{info['wrong']} doesn't belong in row {info['r'] + 1}, column {info['c'] + 1}"
        if expected not in status_text:
            failures.append(f"Expected status to contain {expected!r}, got {status_text!r}")

        # The wrong digit must still never actually land on the board.
        cell_value = page.evaluate(
            f"() => document.querySelectorAll('.cell')[{info['idx']}].querySelector('.cell-value').textContent"
        )
        if cell_value.strip() != "":
            failures.append(f"Wrong digit was written to the board: {cell_value!r}")

        # Placing the correct digit afterwards must work normally.
        page.locator("#numberBar .number-tile").nth(info["correct"] - 1).click()
        page.wait_for_timeout(150)
        cell_value_after = page.evaluate(
            f"() => document.querySelectorAll('.cell')[{info['idx']}].querySelector('.cell-value').textContent"
        )
        if cell_value_after.strip() != str(info["correct"]):
            failures.append(f"Correct digit wasn't placed after a wrong attempt: {cell_value_after!r}")

        # #status must still never overflow its fixed height.
        overflowed = page.evaluate(
            """() => {
                const el = document.getElementById('status');
                return el.scrollHeight > el.clientHeight + 1;
            }"""
        )
        if overflowed:
            failures.append("The wrong-digit message overflowed #status's fixed height")

        browser.close()

    if failures:
        print("FAIL: wrong-digit status message is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: a wrong digit gets a plain-language status message naming the cell, with no counter and no board change")


if __name__ == "__main__":
    main()
