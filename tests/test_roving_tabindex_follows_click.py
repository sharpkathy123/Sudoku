"""Regression test: clicking/selecting a cell updates the roving tabindex,
not just arrow-key moves and Hint.

Reported live, as the third part of the same report as
test_pencil_toggle_keeps_selection_visible.py: "I then hit B (for board)
and one of the cells that had been selected by the Hint was selected" --
even though the player had since clicked a different cell. Root cause:
onCellClick() (what a plain click/tap runs) never touched the roving
tabindex, only arrow-key movement and Hint's own focus helper did. So
the one cell marked tabindex="0" -- what "B" and a bare Tab fall back to
whenever selectedCell is momentarily null -- could keep pointing at
wherever Hint last put it long after the player had clicked elsewhere.

Fixed by having onCellClick() itself keep the roving tabindex in sync
with whatever cell was just selected, the same bookkeeping arrow-key
movement already did inline.
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

        # Simulate Hint having previously put the roving tabindex on some
        # cell (cell 0), then the player plainly clicking a totally
        # different cell (cell 40) afterward.
        page.evaluate(
            """() => {
                board.children[0].tabIndex = 0;
                onCellClick(board.children[40]);
            }"""
        )

        tabbable_id = page.evaluate(
            """() => {
                const el = board.querySelector('.cell[tabindex="0"]');
                return el ? [...board.children].indexOf(el) : -1;
            }"""
        )
        if tabbable_id != 40:
            failures.append(f"expected the roving tabindex to follow the click onto cell 40, got cell {tabbable_id}")

        only_one_tabbable = page.evaluate(
            "() => board.querySelectorAll('.cell[tabindex=\"0\"]').length === 1"
        )
        if not only_one_tabbable:
            failures.append("more than one cell ended up with tabindex=0 after a plain click")

        browser.close()

    if failures:
        print("FAIL: the roving tabindex doesn't follow a plain cell click:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: clicking a cell moves the roving tabindex there too, not just arrow keys and Hint")


if __name__ == "__main__":
    main()
