"""Regression test: Hint can chain an elimination-only technique into the
technique it unlocks, instead of getting stuck repeating the first one
forever.

Reported live: "This 'acceptable limitation' means that I can't finish
this puzzle without making a wild guess." The player had fully cycled a
Naked Triple hint, erased the pencil marks it named, and asked for
another hint -- and kept getting the exact same Naked Triple, with no
way to progress, even though nothing was actually wrong with the puzzle.

Root cause: the puzzle generator's own solver
(rateSolveWithTierCascade(), and separately the in-page test suite's
testHintObjectsWellFormed) both prove a puzzle solvable by *chaining*
techniques -- applying each one's eliminations into a working candidate
grid, then re-running the cascade so the next technique in the chain
becomes visible. showHint() never did this: every call recomputed
candidates from scratch from placed digits only, with no memory of
eliminations already fully shown. So whenever the *next* logical step
only became visible after an earlier elimination was actually applied,
Hint could never reach it -- the same already-fully-shown hint would
just keep winning the cascade forever, because nothing it looks at ever
changed.

Fixed with confirmedCandGrid: a working candidate grid that persists
across Hint presses (reset only when the real grid changes -- a
placement or a new puzzle) and has each hint's own elimination folded
into it once that hint reaches tier 3, mirroring exactly what the two
already-trusted solvers above do.

This test searches generated puzzles for a state where the very first
fireable technique is elimination-only AND applying its elimination
unlocks a *different* technique that doesn't fire on the raw candidates
-- the exact dependency chain the live report hit -- then drives the
real showHint() through that first hint's 3 tiers (never placing a
digit, exactly like the live report) and confirms the next Hint press
moves to the unlocked technique instead of repeating the first one.
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
            """async () => {
                // A freshly generated puzzle almost always has an easy
                // "place" technique available immediately, so the
                // interesting elimination-chain dependency only shows up
                // once the easy stuff is already used up. This advances a
                // puzzle by repeatedly placing whatever the *first*
                // fireable "place" technique suggests -- recomputing
                // candidates from scratch each round, exactly the way the
                // real showHint() does (never carrying any accumulated
                // elimination state between rounds, since that's precisely
                // the capability being tested) -- until placement alone
                // can't proceed further. At that point, if the first
                // fireable technique is elimination-only AND is the *only*
                // thing fireable on this from-scratch candidate grid AND
                // applying its own elimination unlocks a genuinely
                // different technique that doesn't fire otherwise, this is
                // the exact dependency the live report hit: old code
                // (recomputing fresh every call, no memory of prior
                // eliminations) has nothing else to fall back to and must
                // repeat the same hint forever; the fix should move on.
                for (let attempt = 0; attempt < 60; attempt++) {
                    const diff = ['medium', 'hard', 'expert'][attempt % 3];
                    const res = await createNewPuzzleAsync(diff);
                    const sol = res.solution;
                    let grid = res.puzzle.map(row => row.slice());

                    for (let round = 0; round < 60; round++) {
                        if (grid.flat().every(v => v !== 0)) break;
                        const candGrid = getCandidatesGridPure(grid);

                        let firstHint = null, firstIdx = -1, firstKind = null;
                        for (let i = 0; i < HINT_CASCADE.length; i++) {
                            const h = HINT_CASCADE[i].fn(grid, candGrid, sol);
                            if (h) { firstHint = h; firstIdx = i; firstKind = HINT_CASCADE[i].kind; break; }
                        }
                        if (!firstHint) break; // stuck even before any elimination logic -- abandon

                        if (firstKind === 'place') {
                            grid[firstHint.r][firstHint.c] = sol[firstHint.r][firstHint.c];
                            continue; // next round recomputes candidates fresh from this new grid
                        }

                        if (!firstHint.eliminate || !firstHint.eliminate.length) break;

                        const updated = candGrid.map(row => row.map(c => c.slice()));
                        firstHint.eliminate.forEach(({ r, c, digits }) => {
                            updated[r][c] = updated[r][c].filter(x => !digits.includes(x));
                        });

                        // Hint i must be the ONLY thing fireable on the raw
                        // grid -- otherwise pre-fix code could stumble onto
                        // some unrelated already-fireable technique next
                        // call for a completely different reason, passing
                        // this test without the fix doing anything.
                        let onlyThingFireable = true;
                        for (let k = 0; k < HINT_CASCADE.length; k++) {
                            if (k === firstIdx) continue;
                            const alt = HINT_CASCADE[k].fn(grid, candGrid, sol);
                            if (alt && (alt.r !== firstHint.r || alt.c !== firstHint.c)) {
                                onlyThingFireable = false;
                                break;
                            }
                        }
                        if (!onlyThingFireable) break; // not a clean single-dependency state -- abandon

                        let unlockedIdx = -1;
                        for (let j = 0; j < HINT_CASCADE.length; j++) {
                            if (j === firstIdx) continue;
                            const before = HINT_CASCADE[j].fn(grid, candGrid, sol);
                            const after = HINT_CASCADE[j].fn(grid, updated, sol);
                            if (!before && after) { unlockedIdx = j; break; }
                        }
                        if (unlockedIdx === -1) break; // no dependency here -- abandon this puzzle

                        // Found the target state -- hand this exact
                        // mid-solve board to the real app and drive it with
                        // real Hint presses, never placing a digit,
                        // exactly like the live report (pencil marks
                        // erased by hand, nothing placed).
                        puzzle = grid.map(row => row.slice());
                        solution = sol;
                        buildBoard();

                        showHint();
                        const first = { r: hintTraceTarget.r, c: hintTraceTarget.c };
                        showHint();
                        showHint(); // tier 3 -- fold-in happens here

                        showHint(); // should move on now
                        const afterTarget = { r: hintTraceTarget.r, c: hintTraceTarget.c };

                        return {
                            firstMethod: firstHint.method,
                            first, after: afterTarget,
                            moved: afterTarget.r !== first.r || afterTarget.c !== first.c,
                        };
                    }
                }
                return { error: 'no puzzle found with a chained elimination dependency in 60 attempts' };
            }"""
        )

        if result.get("error"):
            failures.append(result["error"])
        elif not result["moved"]:
            failures.append(
                f"Hint kept repeating the same {result['firstMethod']} hint at {result['first']} "
                f"even though a different technique should have been unlocked by its elimination"
            )

        browser.close()

    if failures:
        print("FAIL: Hint doesn't chain elimination-only techniques:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: fully cycling an elimination-only hint unlocks the next technique instead of repeating forever")


if __name__ == "__main__":
    main()
