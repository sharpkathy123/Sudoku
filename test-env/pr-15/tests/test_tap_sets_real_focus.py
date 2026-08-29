"""Regression test: tapping any button/select/tabindex'd control must set
real keyboard focus (document.activeElement), not just visually react.

Reported live: on iOS Safari with an attached external keyboard, tapping
a button (e.g. Hint) with a finger, then pressing Tab, always resumed
from the same place regardless of which button had just been tapped.
Root cause is a long-standing iOS Safari quirk -- unlike every other
browser, Safari on iOS doesn't give a tapped <button> or <select> real
keyboard focus by default (it visually reacts -- looks pressed, opens a
picker -- without document.activeElement ever actually changing), so Tab
afterward continues from wherever focus last genuinely was, not from
what was just tapped.

Note: Chromium (which these tests run in) doesn't have this quirk --
its own default behavior already focuses on click, so this test can't
show a real before/after contrast the way most tests here can, since the
actual bug is iOS-only. It still freezes the underlying invariant (tap
sets real focus) that the fix is built on. The fix itself is a single
delegated click listener that explicitly calls .focus() on whatever
button/select/tabindex'd element was tapped.
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

        checks = [
            ("#HintBtn", "HintBtn"),
            ("#pencilToggle", "pencilToggle"),
            ("#guardNotesToggle", "guardNotesToggle"),
            ("#highlightLeastBtn", "highlightLeastBtn"),
            ("#difficulty", "difficulty"),
        ]
        for selector, expected_id in checks:
            page.click(selector)
            page.wait_for_timeout(50)
            active_id = page.evaluate("() => document.activeElement.id")
            if active_id != expected_id:
                failures.append(f"Tapping {selector} didn't set real focus (activeElement.id={active_id!r})")

        # A board cell, too (also tabindex'd).
        page.click(".cell >> nth=5")
        page.wait_for_timeout(50)
        cell_focused = page.evaluate("() => document.activeElement.classList.contains('cell')")
        if not cell_focused:
            failures.append("Tapping a board cell didn't set real focus on it")

        browser.close()

    if failures:
        print("FAIL: tapping controls doesn't reliably set real keyboard focus:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: tapping any button/select/board cell sets real keyboard focus, so Tab continues from there")


if __name__ == "__main__":
    main()
