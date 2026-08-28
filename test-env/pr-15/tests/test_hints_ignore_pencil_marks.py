"""Regression test: hints must reason from true candidates, never from the
player's own hand-written pencil marks.

Reported live: a Unique Rectangle hint told the player to place a digit
that the game then rejected as wrong. Root cause -- getCandidatesGrid()
(used only by the real showHint(), not by the test harness) silently
substituted the player's own pencil marks for the true candidate set
whenever a cell had ANY marks at all. A player is never obligated to have
hand-marked every valid candidate in a cell; if their marks are incomplete
or stale, a cell that's genuinely tri-valent can look bivalue to the hint
engine. Every technique past Naked/Hidden Single (Naked Pair/Triple,
Locked Candidates, X-Wing/Swordfish, XY-Wing/XYZ-Wing, Unique Rectangle)
is only logically sound when "this cell has exactly these N candidates"
is actually true -- trusting incomplete marks let the engine eliminate or
require digits that directly contradicted the real solution.

Fixed by having showHint() always call getCandidatesGridPure() (the same
constraint-derived computation the test harness already used), and
deleting the DOM-reading getCandidatesGrid() entirely -- it had exactly
one caller.
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

        result = page.evaluate(
            """() => {
                const oldFnExists = typeof window.getCandidatesGrid === 'function';

                let called = false;
                const orig = window.getCandidatesGridPure;
                window.getCandidatesGridPure = function(...args) {
                    called = true;
                    return orig.apply(this, args);
                };

                // Garbage pencil marks on an empty cell -- every digit active.
                // If showHint() read the DOM at all for candidates, this would
                // corrupt its reasoning; if it uses true candidates, this has
                // zero effect on the hint it produces.
                const grid = getCurrentGrid();
                let rigged = null;
                for (let r = 0; r < 9 && !rigged; r++) {
                    for (let c = 0; c < 9 && !rigged; c++) {
                        if (grid[r][c] === 0) rigged = { r, c };
                    }
                }
                const cell = board.children[rigged.r * 9 + rigged.c];
                for (let n = 1; n <= 9; n++) cell._pencilDigits[n].classList.add('active');

                showHint();
                const statusText = document.getElementById('status').textContent;

                window.getCandidatesGridPure = orig;
                return { oldFnExists, called, statusText };
            }"""
        )

        if result["oldFnExists"]:
            failures.append("getCandidatesGrid() (the DOM-reading, pencil-mark-trusting function) still exists")
        if not result["called"]:
            failures.append("showHint() did not call getCandidatesGridPure() -- it may be reading DOM pencil marks again")
        if "Tier 1" not in result["statusText"]:
            failures.append(f"showHint() did not produce a normal hint despite garbage pencil marks: {result['statusText']!r}")

        browser.close()

    if failures:
        print("FAIL: hints are not reliably using true candidates:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: hints always reason from true, constraint-derived candidates, never from the player's own pencil marks")


if __name__ == "__main__":
    main()
