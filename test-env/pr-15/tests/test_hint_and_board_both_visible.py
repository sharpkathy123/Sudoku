"""Regression test: the hint/status text and the whole board must fit in
one ordinary phone screen together.

Reported live: after the board-space overhaul made the board bigger, the
hint message (up at the top of the page, right under the title) and the
board (much bigger now, near the bottom) no longer fit in the same
viewport -- reading a hint meant scrolling away from the board it was
about. Fixed by moving #status down to sit directly above the number bar
and board, and moving the Hint button down onto the same row as the
Pencil Mode toggle, so requesting and reading a hint both happen right
next to the board instead of requiring a trip back to the top of the page.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(300)

        page.click("#HintBtn")
        page.wait_for_timeout(300)

        layout = page.evaluate(
            """() => {
                const statusRect = document.getElementById('status').getBoundingClientRect();
                const boardRect = document.getElementById('board').getBoundingClientRect();
                const hintRect = document.getElementById('HintBtn').getBoundingClientRect();
                const pencilRect = document.getElementById('pencilToggle').getBoundingClientRect();
                return {
                    statusTop: statusRect.top,
                    boardBottom: boardRect.bottom,
                    viewportHeight: window.innerHeight,
                    hintTop: hintRect.top,
                    pencilTop: pencilRect.top,
                };
            }"""
        )

        if layout["statusTop"] < 0:
            failures.append(f"#status is scrolled above the viewport (top={layout['statusTop']})")
        if layout["boardBottom"] > layout["viewportHeight"]:
            failures.append(
                f"Board doesn't fully fit in the viewport alongside the hint "
                f"(boardBottom={layout['boardBottom']}, viewportHeight={layout['viewportHeight']})"
            )
        if abs(layout["hintTop"] - layout["pencilTop"]) > 2:
            failures.append(
                f"Hint button isn't on the same row as the Pencil Mode toggle "
                f"(hintTop={layout['hintTop']}, pencilTop={layout['pencilTop']})"
            )

        browser.close()

    if failures:
        print("FAIL: hint text and board don't fit together:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: the hint/status text and the whole board both fit in one phone screen, with Hint next to Pencil Mode")


if __name__ == "__main__":
    main()
