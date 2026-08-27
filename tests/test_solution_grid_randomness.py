"""Regression test: every generated puzzle's solution should differ.

A player reported recognizing the same pattern across many "different"
puzzles — row 1 always 1..9 in order, row 2 always 4..9 then 1..3, and
so on. Root cause: solveSudoku(), used to generate each puzzle's full
answer key by solving a blank grid, always tried digits 1-9 in the
same fixed order and always scanned cells in the same order — so it
always found the exact same "first" solution to an empty grid, every
single time, for every difficulty. Only which cells got removed as
givens was ever randomized; the underlying solved grid never varied
at all, so an experienced player could eventually recognize and
memorize it.

This generates several puzzles and checks their solution grids are
not all identical (astronomically unlikely by chance if solveSudoku
is genuinely randomized, and always true of the bug it replaces).
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
        page.wait_for_timeout(500)

        # Easy is fast to generate and has no seed pool, so this exercises
        # the actual solveSudoku()-driven path directly.
        solutions = page.evaluate(
            """async () => {
                const grids = [];
                for (let i = 0; i < 5; i++) {
                    const res = await createNewPuzzleAsync('easy');
                    grids.push(res.solution.map(row => row.join('')).join('|'));
                }
                return grids;
            }"""
        )

        unique_solutions = set(solutions)
        if len(unique_solutions) == 1:
            failures.append(
                f"All {len(solutions)} generated solutions were identical: {solutions[0][:27]}... "
                f"— solveSudoku() is producing the same grid every time again"
            )

        browser.close()

    if failures:
        print("FAIL: generated puzzles are not actually randomized:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print(f"PASS: {len(unique_solutions)}/{len(solutions)} generated solution grids were unique")


if __name__ == "__main__":
    main()
