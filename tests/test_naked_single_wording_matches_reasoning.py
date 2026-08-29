"""Regression test: a Naked Single hint never claims "already present" for
a digit that was only ruled out by an earlier hint's own elimination.

Reported live: after cycling several hints' tiers to completion without
placing anything (the chaining fix a few commits back lets those
eliminations persist), a Naked Single showed up saying "All digits except
8 are already present across Row 6, Column 8, or Box 6." The player
checked that row/column/box for placed digits and couldn't find several
of the named digits there -- because they weren't placed anywhere; they'd
only been eliminated as candidates by earlier hints. The wording claimed
a much simpler (and false) justification than what was actually true.

findNakedSingle used to always use this "already present" phrasing,
written back when candGrid could only ever be pure, placed-digit-derived
candidates (before hints could chain). Now that showHint() reuses and
narrows a persistent confirmedCandGrid across presses, a cell can drop to
one candidate two different ways: every other digit really is placed
somewhere in its row/column/box (the original case this wording is
accurate for), or some of those digits were only eliminated by an
earlier hint. Fixed by checking with isSafe() against the actual
placed-digit grid whether the single candidate is explainable by
placement alone, and using different, honest wording when it isn't --
mirroring the same distinction findHiddenSingle already draws between
"Cross-Hatching" (blocked by placed digits) and "Hidden Single" (needs
candidate eliminations).
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
                // Hand-build a case where a cell's basic (placed-digit-only)
                // candidates are {5, 6, 8}, but an earlier hint has already
                // eliminated 5 and 6 from the *working* candidate grid --
                // exactly the live scenario, without depending on randomly
                // generated puzzles to happen to produce one.
                const grid = Array.from({ length: 9 }, () => Array(9).fill(0));
                // A minimal, conflict-free set of placements chosen so that
                // isSafe() alone leaves exactly {5, 6, 8} at (5, 7):
                // row 5 accounts for 1-4, column 7 accounts for 7 and 9.
                const placements = [
                    [0, 7, 7], [1, 7, 9],
                    [5, 0, 1], [5, 1, 2], [5, 2, 3], [5, 3, 4],
                ];
                for (const [r, c, v] of placements) grid[r][c] = v;

                const basic = [1,2,3,4,5,6,7,8,9].filter(n => isSafe(grid, 5, 7, n));

                const trueCand = getCandidatesGridPure(grid);
                trueCand[5][7] = trueCand[5][7].filter(x => x !== 5 && x !== 6); // simulate prior chained eliminations

                const chained = findNakedSingle(trueCand, grid);

                // And the ordinary, non-chained case for comparison: no
                // extra elimination applied, so it should keep the
                // original "already present" wording.
                const basicOnly = findNakedSingle(getCandidatesGridPure(grid), grid);

                return {
                    basicCandidateCount: basic.length,
                    chainedVal: chained && chained.val,
                    chainedTier3: chained && chained.tier3,
                    basicOnlyFound: !!basicOnly,
                };
            }"""
        )

        if result["basicCandidateCount"] != 3:
            failures.append(
                f"test setup didn't produce the intended 3-candidate basic state "
                f"(got {result['basicCandidateCount']} candidates) -- adjust the hand-built grid"
            )
        elif not result["chainedVal"]:
            failures.append("findNakedSingle didn't fire on the chained-elimination candidate grid at all")
        elif "already present" in (result["chainedTier3"] or ""):
            failures.append(
                f"Naked Single still claims digits are 'already present' when they were only "
                f"ruled out by an earlier hint's elimination: {result['chainedTier3']!r}"
            )

        browser.close()

    if failures:
        print("FAIL: Naked Single wording doesn't match its actual reasoning:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: Naked Single only claims digits are 'already present' when that's actually true")


if __name__ == "__main__":
    main()
