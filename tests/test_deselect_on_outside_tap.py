"""Regression test for tapping outside the board/controls.

Tapping anywhere that isn't the board, a button, the difficulty
select, or a number tile should clear the current cell selection and
every highlight derived from it (same-number highlighting, Highlight
Fullest) — see the "Clear cell/number selection when tapping outside
the board and controls" commit. This exercises the actual click
handler end-to-end rather than just checking the code exists.
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
        # Initial puzzle generation is async and rebuilds the whole board
        # (buildBoard()) when it finishes; wait for that to actually
        # happen, rather than a fixed delay, so clicks land on stable
        # cells instead of ones about to be replaced mid-test.
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(500)

        # 1. Selecting a cell should mark it selected.
        page.locator(".cell").nth(10).click()
        page.wait_for_timeout(200)
        if not page.evaluate("() => !!document.querySelector('.cell.selected')"):
            failures.append("Clicking a cell did not select it (test setup problem, not the fix itself)")

        # 2. Tapping outside the board/controls should clear that selection.
        page.locator("h1").click()
        page.wait_for_timeout(200)
        if page.evaluate("() => !!document.querySelector('.cell.selected')"):
            failures.append("Cell selection survived a tap outside the board and controls")

        # 3. Selecting a number tile should mark it selected.
        page.locator("#numberBar .number-tile").nth(2).click()
        page.wait_for_timeout(200)
        if not page.evaluate("() => !!document.querySelector('.number-tile.selected')"):
            failures.append("Clicking a number tile did not select it (test setup problem, not the fix itself)")

        # 4. Tapping outside should clear the number tile selection too.
        page.locator("#status").click()
        page.wait_for_timeout(200)
        if page.evaluate("() => !!document.querySelector('.number-tile.selected')"):
            failures.append("Number tile selection survived a tap outside the board and controls")

        # 5. Real controls must still work normally (not swallowed by the
        # new outside-tap listener).
        page.click("#HintBtn")
        page.wait_for_timeout(500)
        if not page.inner_text("#status").strip():
            failures.append("Clicking Hint produced no status text — outside-tap listener may be interfering")

        browser.close()

    if failures:
        print("FAIL: tap-outside-to-deselect is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: tapping outside the board/controls clears selection; real controls still work")


if __name__ == "__main__":
    main()
