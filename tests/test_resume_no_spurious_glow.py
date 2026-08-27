"""Regression test: resuming a saved game shouldn't re-glow old progress.

A player reported that resuming a saved game (a legitimate one, with
real progress — not the corrupted-save bug covered by
test_corrupted_save_recovery.py) made every cell glow on load. Root
cause: buildBoard() resets the completedRows/Cols/Boxes/Digits
tracking arrays to false, and loadSavedGameState() then called
checkAndBoldCompletedNumbers() normally — so every unit that had
already been completed in a *previous* session looked "newly"
completed and glowed all over again, all at once.

This completes a real row during play (checking it glows, as it
should for a genuinely new completion), lets the glow clear, saves,
reloads, and checks that resuming does NOT re-trigger glow for that
same already-completed row, while the progress itself is still there.
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

        # Legitimately complete row 0 by filling in the real solution values,
        # then run the normal (non-silent) completion check exactly as live
        # play would.
        glowing_on_real_completion = page.evaluate(
            """() => {
                for (let c = 0; c < 9; c++) {
                    const cell = document.querySelectorAll('.cell')[c];
                    if (!givenMask[0][c]) cell.querySelector('.cell-value').textContent = solution[0][c];
                }
                checkAndBoldCompletedNumbers();
                return document.querySelectorAll('.cell.glow').length;
            }"""
        )
        if glowing_on_real_completion == 0:
            failures.append("Completing a row for the first time produced no glow at all (test setup problem)")

        page.wait_for_timeout(2200)  # let the real glow's own 2s timer clear

        page.evaluate("() => saveGameState()")
        page.reload(wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(300)

        glowing_on_resume = page.evaluate("() => document.querySelectorAll('.cell.glow').length")
        row0_filled = page.evaluate(
            """() => {
                let count = 0;
                for (let c = 0; c < 9; c++) {
                    if (document.querySelectorAll('.cell')[c].querySelector('.cell-value').textContent.trim()) count++;
                }
                return count;
            }"""
        )

        if glowing_on_resume > 0:
            failures.append(f"{glowing_on_resume} cells glowed on resume for a unit completed in a prior session")
        if row0_filled != 9:
            failures.append(f"Resuming lost real progress (row 0 has {row0_filled}/9 cells filled)")

        browser.close()

    if failures:
        print("FAIL: resuming a saved game re-glows old progress:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: resuming preserves progress without re-glowing already-completed units")


if __name__ == "__main__":
    main()
