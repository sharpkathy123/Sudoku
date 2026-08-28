"""Regression test: two specific outcomes of the color/animation overhaul.

1. "Highlight Fullest" must not use its old amber color. The amber
   (#fef3c7 bg / #d97706 outline) visually clashed with the rest of the
   palette and was too close in meaning to the warm hint-trace/wrong-digit
   tones -- explicit product feedback. It's now a teal, distinct from the
   violet hint-trace and the soft-yellow same-number highlight.
2. Animations and transitions must respect prefers-reduced-motion, rather
   than always running regardless of the player's OS/browser setting.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo

OLD_AMBER_BG = "rgb(254, 243, 199)"  # #fef3c7
OLD_AMBER_OUTLINE_COLOR = "rgb(217, 119, 6)"  # #d97706


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)

        page = browser.new_page()
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(300)

        page.click("#highlightLeastBtn")
        page.wait_for_timeout(150)

        style = page.evaluate(
            """() => {
                const cell = document.querySelector('.cell.highlight-least');
                if (!cell) return null;
                const cs = getComputedStyle(cell);
                return { bg: cs.backgroundColor, outline: cs.outlineColor };
            }"""
        )
        if style is None:
            failures.append("Highlight Fullest didn't highlight any cell -- can't check its color")
        else:
            if style["bg"] == OLD_AMBER_BG or style["outline"] == OLD_AMBER_OUTLINE_COLOR:
                failures.append(f"Highlight Fullest is still using the old amber color: {style}")

        page.close()

        # Reduced motion: transitions/animations should collapse to ~instant.
        page2 = browser.new_page()
        page2.emulate_media(reduced_motion="reduce")
        page2.goto(f"{base_url}/index.html", wait_until="networkidle")
        page2.wait_for_function("() => document.querySelectorAll('.cell').length === 81")
        page2.wait_for_timeout(200)

        cell_transition = page2.evaluate(
            "() => getComputedStyle(document.querySelector('.cell')).transitionDuration"
        )
        # The cell has several transitioned properties, so this can be a
        # comma-separated list (e.g. "0.15s, 0.15s, 0.15s, 0.2s") -- check
        # the slowest of them. Any real duration is >= 0.01s; reduced
        # motion should collapse all of them far below that (we set 0.001ms).
        durations = [float(part.strip().rstrip("s")) for part in cell_transition.split(",")]
        if max(durations) > 0.001:
            failures.append(f"Cell transition duration under prefers-reduced-motion is {cell_transition}, expected ~0")

        page2.close()
        browser.close()

    if failures:
        print("FAIL: visual overhaul regression:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: Highlight Fullest no longer uses the disliked amber, and prefers-reduced-motion is respected")


if __name__ == "__main__":
    main()
