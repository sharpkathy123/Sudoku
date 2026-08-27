"""Regression test: the status area must never change the page layout.

Three independent expert reviews converged on this as the most serious
bug found in a round of usability/UX/visual-design review: #status had
only a min-height, so longer messages (especially hint tier 2, which is
often the longest text in the app) grew the box and physically pushed
every control below it down the page. That wasn't just cosmetic — the
Hint button could move enough between tiers that tapping the same
screen position for tier 3 actually landed on Guard Pencil instead and
silently turned it off.

This checks two things across every difficulty and several puzzles:
1. #status never needs to scroll (its content fits the fixed box) at
   both a very narrow (320px) and a normal (390px) mobile width.
2. The Hint button's on-screen position does not move at all across
   three consecutive presses (which cycle through all 3 hint tiers).
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)

        for width in (320, 390):
            page = browser.new_page(viewport={"width": width, "height": 700})
            page.goto(f"{base_url}/index.html", wait_until="networkidle")
            page.wait_for_timeout(500)

            overflow_samples = page.evaluate(
                """async () => {
                    const overflows = [];
                    for (const diff of ['easy', 'medium', 'hard', 'expert']) {
                        for (let i = 0; i < 6; i++) {
                            const res = await createNewPuzzleAsync(diff);
                            puzzle = res.puzzle;
                            solution = res.solution;
                            buildBoard();
                            for (let t = 0; t < 3; t++) {
                                showHint();
                                const el = document.getElementById('status');
                                if (el.scrollHeight > el.clientHeight + 1) {
                                    overflows.push({ diff, tier: t + 1, text: el.textContent.slice(0, 80) });
                                }
                            }
                        }
                    }
                    return overflows;
                }"""
            )
            if overflow_samples:
                failures.append(
                    f"At {width}px, {len(overflow_samples)} hint message(s) overflowed #status's fixed "
                    f"height, e.g. {overflow_samples[0]}"
                )
            page.close()

        # The concrete reported scenario: tap Hint three times at the exact
        # same screen coordinate and confirm the button never moved and
        # Guard Pencil was never touched.
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(500)

        box0 = page.locator("#HintBtn").bounding_box()
        x, y = box0["x"] + box0["width"] / 2, box0["y"] + box0["height"] / 2
        positions = [box0]
        for _ in range(2):
            page.mouse.click(x, y)
            page.wait_for_timeout(200)
            positions.append(page.locator("#HintBtn").bounding_box())

        if any((p["x"], p["y"]) != (box0["x"], box0["y"]) for p in positions):
            failures.append(f"Hint button moved across tiers: {[(p['x'], p['y']) for p in positions]}")

        page.mouse.click(x, y)  # tier 3 press, at the same original coordinate
        page.wait_for_timeout(200)
        guard_text = page.inner_text("#guardNotesToggle")
        if "ON" not in guard_text:
            failures.append(f"Guard Pencil was toggled off by tapping Hint 3 times at one spot: {guard_text!r}")

        page.close()
        browser.close()

    if failures:
        print("FAIL: #status layout stability is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: #status never overflows or reflows the page, and the Hint button never drifts")


if __name__ == "__main__":
    main()
