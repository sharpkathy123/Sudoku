"""Regression test: two wording problems from the learning-design review.

1. Tier 1 (and, for Naked Single, tier 2) for the "visual scanning" techniques
   -- Full House, Naked Single, Hidden Single/Cross-Hatching -- used to name
   the exact answer cell ("Look at Row 3, Column 5...") before the player had
   done any of the actual finding. For these techniques, locating the cell
   *is* the skill being taught, so naming it up front skipped straight past
   it. Tier 1 (and Naked Single's tier 2) should narrow to a unit/area, not
   name the answer cell outright; the full "Row R, Column C" reveal should
   only show up at tier 3.
2. XY-Wing and XYZ-Wing's tier3 text explained the elimination ("eliminate
   it from every cell that can see both of them") without ever naming which
   digit -- unhelpful if you're trying to actually apply it. Both now name
   the eliminated digit explicitly.
"""
import re
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

        # Default difficulty on a first-ever visit should be Easy, not Medium.
        localStorage_cleared_default = page.evaluate("() => document.getElementById('difficulty').value")
        if localStorage_cleared_default != "easy":
            failures.append(f"Default difficulty on first load is {localStorage_cleared_default!r}, expected 'easy'")

        # Walk the hint cascade across several generated puzzles at every
        # difficulty, collecting every distinct method's tier1/tier2/tier3 --
        # mirrors the in-page testHintObjectsWellFormed's own approach, but
        # checks wording content instead of just structural validity.
        samples = page.evaluate(
            """async () => {
                const seen = {};
                for (const diff of ['easy', 'medium', 'hard', 'expert']) {
                    for (let i = 0; i < 6; i++) {
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
                                if (!seen[hint.method]) {
                                    seen[hint.method] = {
                                        tier1: hint.tier1, tier2: hint.tier2, tier3: hint.tier3,
                                        eliminateDigits: (hint.eliminate || []).map(e => e.digits).flat()
                                    };
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
                return seen;
            }"""
        )

        coord_pattern = re.compile(r"Row \d+, Col(?:umn)? \d+")

        for method in ("Full House", "Naked Single", "Hidden Single", "Cross-Hatching"):
            hint = samples.get(method)
            if not hint:
                continue  # not every technique is guaranteed to appear in this sample
            if coord_pattern.search(hint["tier1"]):
                failures.append(f"{method} tier1 still names the exact answer cell: {hint['tier1']!r}")
            if method == "Naked Single" and coord_pattern.search(hint["tier2"]):
                failures.append(f"{method} tier2 still names the exact answer cell: {hint['tier2']!r}")

        for method in ("XY-Wing", "XYZ-Wing"):
            hint = samples.get(method)
            if not hint:
                continue  # rare techniques; may not appear in this sample
            digits_in_tier3 = {int(d) for d in re.findall(r"\d", hint["tier3"].split("Row")[0])}
            if not (set(hint["eliminateDigits"]) & digits_in_tier3):
                failures.append(f"{method} tier3 doesn't name the eliminated digit: {hint['tier3']!r}")

        browser.close()

    if failures:
        print("FAIL: hint curriculum wording regression:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: visual-scanning hints don't give away the answer cell early, wing hints name their digit, and Easy is the default")


if __name__ == "__main__":
    main()
