"""Regression test: the keyboard focus/selection indicator on the board.

Reported live: using arrow keys to navigate, the selection indicator (a
thin 2px outline) got lost the moment focus landed on a filled cell,
since that also lights up every other cell holding the same digit in a
pale yellow -- with everything else competing for attention, the outline
marking "you are here" was easy to lose track of.

Two things were fixed:
1. The outline itself: thicker (3px), pulled inward with outline-offset,
   and a darker, more saturated blue -- clearly visible against the
   same-number highlight instead of blending into the background noise.
2. A real gap this surfaced: only arrow-key movement explicitly kept
   selectedCell in sync with focus. A plain Tab landing directly on the
   board's one tab-stop cell left selection completely out of sync,
   relying on the browser's own (inconsistent, and here suppressed)
   default focus ring instead of this app's own. Fixed with a single
   focusin listener on the board so selection always follows focus,
   however it arrives.
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

        # 1. A plain Tab-style focus (not via arrow keys) must sync selection.
        page.evaluate("() => board.children[0].focus()")
        page.wait_for_timeout(100)
        synced = page.evaluate(
            "() => selectedCell === board.children[0] && board.children[0].classList.contains('selected')"
        )
        if not synced:
            failures.append("Focusing a cell directly (not via arrow keys) didn't sync selectedCell/'.selected'")

        # 2. Arrow-navigating onto a filled cell (triggering same-number
        # highlighting) must still show a clearly visible selection outline
        # -- thick, inset, and high z-index so it's never buried.
        target_c = page.evaluate(
            "() => { const g = getCurrentGrid(); for (let c = 0; c < 9; c++) if (g[0][c] !== 0) return c; }"
        )
        page.evaluate("() => board.children[0].focus()")
        page.wait_for_timeout(50)
        for _ in range(target_c):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(30)
        page.wait_for_timeout(150)

        style = page.evaluate(
            f"""() => {{
                const cell = board.children[{target_c}];
                const cs = getComputedStyle(cell);
                return {{
                    hasSelectedClass: cell.classList.contains('selected'),
                    outlineWidth: cs.outlineWidth,
                    outlineColor: cs.outlineColor,
                    zIndex: cs.zIndex,
                }};
            }}"""
        )
        if not style["hasSelectedClass"]:
            failures.append("Arrow-navigating onto a filled cell didn't select it")
        if float(style["outlineWidth"].rstrip("px") or 0) < 3:
            failures.append(f"Selection outline is thinner than expected: {style['outlineWidth']!r}")
        z_index = style["zIndex"]
        if z_index == "auto" or int(z_index) < 3:
            failures.append(f"Selection z-index isn't raised above highlight layers: {z_index!r}")

        browser.close()

    if failures:
        print("FAIL: keyboard focus/selection visibility is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: selection stays visibly in sync with focus, however focus arrives, even amid same-number highlighting")


if __name__ == "__main__":
    main()
