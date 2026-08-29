"""Regression test: tapping anywhere should stop in-progress unit glow,
without wiping out the glow it was itself just responsible for causing.

The app used to let a tap anywhere on screen cut short the celebratory
glow when you complete a row/column/box/digit, so finishing several
units in a row didn't force you to sit through a queued string of
2-second glows before you could act again. That was restored as a
capture-phase document click listener — but the first version fired on
*every* click unconditionally, including the very click (a number-tile
tap) that completes a unit and adds its own fresh glow in the same
synchronous event dispatch, wiping the glow before it ever rendered.
So the completing click must be a real click through the game's own
UI, not a direct JS call, or this regression wouldn't be caught.

This completes a row via a real cell-select + number-tile click (the
actual path a player uses), checks the glow survived that same click,
then makes a separate, later click and checks that one clears it.
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

        # Fill all of row 0 except one non-given cell, leaving that one
        # cell as the "last missing piece" of the row.
        setup = page.evaluate(
            """() => {
                let targetCol = -1;
                for (let c = 0; c < 9; c++) if (!givenMask[0][c]) { targetCol = c; break; }
                if (targetCol === -1) return { error: 'row 0 is fully given' };
                for (let c = 0; c < 9; c++) {
                    const cell = document.querySelectorAll('.cell')[c];
                    if (c === targetCol) {
                        cell.querySelector('.cell-value').textContent = '';
                    } else if (!givenMask[0][c]) {
                        cell.querySelector('.cell-value').textContent = solution[0][c];
                    }
                }
                placements[solution[0][targetCol]] = placements[solution[0][targetCol]].filter(i => i !== targetCol);
                return { targetCol, missingVal: solution[0][targetCol] };
            }"""
        )
        if "error" in setup:
            print(f"SKIP: {setup['error']} for this randomly generated puzzle — rerun to try a different one")
            browser.close()
            return

        # The actual player path: select the empty cell, then tap the
        # number tile that completes the row.
        page.locator(".cell").nth(setup["targetCol"]).click()
        page.wait_for_timeout(100)
        page.locator("#numberBar .number-tile").nth(setup["missingVal"] - 1).click()
        page.wait_for_timeout(100)

        glowing_from_completion = page.evaluate("() => document.querySelectorAll('.cell.glow').length")
        if glowing_from_completion == 0:
            failures.append(
                "Completing the row via a real click produced no glow — the completing click "
                "wiped its own glow in the same dispatch instead of letting it render"
            )

        # A later, separate tap should now clear it.
        page.locator("h1").click()
        page.wait_for_timeout(100)
        glowing_after_next_tap = page.evaluate("() => document.querySelectorAll('.cell.glow').length")
        if glowing_after_next_tap > 0:
            failures.append(f"{glowing_after_next_tap} cells were still glowing after a subsequent tap")

        browser.close()

    if failures:
        print("FAIL: tap-to-stop-glow is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: completing a unit still glows, and a later tap clears it")


if __name__ == "__main__":
    main()
