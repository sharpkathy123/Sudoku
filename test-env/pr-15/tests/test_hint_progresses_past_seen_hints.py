"""Regression test: Hint moves on to a new technique once the current one
has been fully shown, instead of repeating it forever.

Reported live: a player correctly applied a Pointing Pair hint's tier-3
instruction by erasing the named pencil marks by hand, then asked for
another hint -- and got the exact same Pointing Pair hint again. This
isn't a correctness bug (hints deliberately reason only from placed
digits, never from the player's own pencil marks -- see
test_hints_ignore_pencil_marks.py), but it's a real progression gap: an
elimination-only hint (Naked Pair, Pointing/Claiming, X-Wing/Swordfish,
the wings, Unique Rectangle) doesn't itself change the grid, so asking
for another hint before placing anything recomputes the exact same
candidates from the exact same placed digits and finds the exact same
hint, forever.

Fixed with a "seen" set: once a hint's 3rd tier (the full reveal) has
been shown, its (method-independent) cell key is remembered, and the
next Hint press skips any technique that resolves to an already-seen
key, falling back to it only if every fireable technique has been
fully shown. Cleared whenever the grid actually changes (a real
placement, or a new puzzle).
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
                for (let attempt = 0; attempt < 30; attempt++) {
                    const diff = ['medium', 'hard', 'expert'][attempt % 3];
                    const res = await createNewPuzzleAsync(diff);
                    puzzle = res.puzzle; solution = res.solution;
                    buildBoard();
                    const grid = getCurrentGrid();
                    const cand = getCandidatesGridPure(grid);
                    const fired = new Set();
                    for (const { fn } of HINT_CASCADE) {
                        const h = fn(grid, cand, solution);
                        if (h) fired.add(h.method);
                    }
                    if (fired.size < 2) continue;

                    showHint();
                    const first = { r: hintTraceTarget.r, c: hintTraceTarget.c };
                    showHint();
                    showHint(); // now at tier 3 for the first hint

                    showHint(); // should move to a different hint now
                    const after = { r: hintTraceTarget.r, c: hintTraceTarget.c };

                    return {
                        distinctMethods: fired.size,
                        first, after,
                        moved: after.r !== first.r || after.c !== first.c,
                    };
                }
                return { error: 'no puzzle with 2+ distinct firing techniques found in 30 attempts' };
            }"""
        )

        if result.get("error"):
            failures.append(result["error"])
        elif not result["moved"]:
            failures.append(
                f"Hint repeated the same cell {result['first']} after fully cycling it, "
                f"even though {result['distinctMethods']} distinct techniques were available"
            )

        browser.close()

    if failures:
        print("FAIL: Hint doesn't progress past already-fully-shown hints:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: asking for another hint after fully cycling one moves on to a different technique")


if __name__ == "__main__":
    main()
