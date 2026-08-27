"""Regression test: tapping anywhere should stop in-progress unit glow.

The app used to let a tap anywhere on screen cut short the celebratory
glow when you complete a row/column/box/digit, so finishing several
units in a row didn't force you to sit through a queued string of
2-second glows before you could act again. This checks that a plain
click (not tied to the end-of-puzzle win celebration, which has its
own separate tap-to-skip handling) clears any cell still glowing.
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

        glowing_before = page.evaluate(
            """() => {
                for (let c = 0; c < 9; c++) {
                    const cell = document.querySelectorAll('.cell')[c];
                    if (!givenMask[0][c]) cell.querySelector('.cell-value').textContent = solution[0][c];
                }
                checkAndBoldCompletedNumbers();
                return document.querySelectorAll('.cell.glow').length;
            }"""
        )
        if glowing_before == 0:
            failures.append("Completing a row produced no glow at all (test setup problem)")

        page.locator("h2").click()
        page.wait_for_timeout(100)

        glowing_after = page.evaluate("() => document.querySelectorAll('.cell.glow').length")
        if glowing_after > 0:
            failures.append(f"{glowing_after} cells were still glowing immediately after a tap")

        browser.close()

    if failures:
        print("FAIL: tapping does not stop in-progress unit glow:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: a tap anywhere immediately clears any in-progress unit-completion glow")


if __name__ == "__main__":
    main()
