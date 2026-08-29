"""Audit: no hint's elimination should ever remove the digit that's
actually correct for that cell.

This is a stronger, more general check than any single technique's own
regression test: for every "eliminate"-kind hint (Naked Pair/Triple,
Locked Candidates, X-Wing/Swordfish, XY-Wing/XYZ-Wing, Unique Rectangle),
walk its eliminate list and confirm that for each eliminated cell, the
digit(s) being removed are never that cell's true solution digit. If a
hint ever eliminates the correct answer from a cell, that hint's
underlying logic (or the puzzle/solution pair feeding it) is wrong --
regardless of which specific technique it was.

Run across many fresh puzzles at every difficulty, using the same
getCandidatesGridPure() the real showHint() now uses, so this exercises
freshly-generated puzzles end to end rather than any one hand-built case.
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

        problems = page.evaluate(
            """async () => {
                const problems = [];
                for (const diff of ['easy', 'medium', 'hard', 'expert']) {
                    for (let i = 0; i < 15; i++) {
                        const res = await createNewPuzzleAsync(diff);
                        const grid = deepCopyGrid(res.puzzle);
                        let candGrid = getCandidatesGridPure(grid);
                        let iterations = 0;
                        while (iterations++ < 2000) {
                            if (isGridFull(grid)) break;
                            let acted = false;
                            for (const { kind, fn } of HINT_CASCADE) {
                                const hint = fn(grid, candGrid, res.solution);
                                if (!hint) continue;

                                if (hint.eliminate && hint.eliminate.length) {
                                    for (const { r, c, digits } of hint.eliminate) {
                                        const trueDigit = res.solution[r][c];
                                        if (grid[r][c] === 0 && digits.includes(trueDigit)) {
                                            problems.push(
                                                `${diff} puzzle ${i}: ${hint.method} eliminated the true ` +
                                                `answer ${trueDigit} from Row ${r+1}, Col ${c+1}`
                                            );
                                        }
                                    }
                                }

                                if (kind === 'place') {
                                    grid[hint.r][hint.c] = res.solution[hint.r][hint.c];
                                    candGrid = getCandidatesGridPure(grid);
                                } else if (hint.eliminate && hint.eliminate.length) {
                                    hint.eliminate.forEach(({ r, c, digits }) => {
                                        candGrid[r][c] = candGrid[r][c].filter(x => !digits.includes(x));
                                    });
                                } else {
                                    continue;
                                }
                                acted = true;
                                break;
                            }
                            if (!acted) break;
                        }
                    }
                }
                return problems;
            }"""
        )

        failures.extend(problems)
        browser.close()

    if failures:
        print(f"FAIL: {len(failures)} hint elimination(s) contradicted the true solution:")
        for f in failures[:10]:
            print("  -", f)
        sys.exit(1)

    print("PASS: no hint elimination ever removed a cell's true answer, across 60 freshly generated puzzles")


if __name__ == "__main__":
    main()
