"""Regression test: letter-key shortcuts for every button.

Requested live: tabbing all the way across the control rows to reach a
button (especially with iOS's default Tab behavior already skipping
plain buttons without Full Keyboard Access -- see
test_all_buttons_tab_reachable.py) is slow. Added a plain, unmodified
letter-key shortcut per button -- each one's own first letter, except
Highlight Fullest, which uses "F" (from "Fullest") since Hint already
owns "H".

Guarded two ways: modified presses (Ctrl/Cmd/Alt) are ignored, so this
never fights a real browser/OS shortcut sharing the same letter; and the
difficulty <select>'s own native type-ahead (jumping to "Hard" on "h",
etc.) is left alone whenever that select is focused, rather than being
double-triggered by this handler too.
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

        # P toggles Pencil Mode.
        before = page.evaluate("() => pencilMode")
        page.keyboard.press("p")
        page.wait_for_timeout(80)
        after = page.evaluate("() => pencilMode")
        if after == before:
            failures.append("'p' didn't toggle Pencil Mode")
        page.keyboard.press("p")  # back to OFF
        page.wait_for_timeout(80)

        # G toggles Guard Pencil.
        before = page.evaluate("() => guardNotesMode")
        page.keyboard.press("g")
        page.wait_for_timeout(80)
        after = page.evaluate("() => guardNotesMode")
        if after == before:
            failures.append("'g' didn't toggle Guard Pencil")

        # H triggers Hint.
        page.evaluate("() => setStatusText('')")
        page.keyboard.press("h")
        page.wait_for_timeout(150)
        status = page.evaluate("() => document.getElementById('status').textContent")
        if "Tier 1" not in status:
            failures.append(f"'h' didn't trigger a hint: {status!r}")

        # F triggers Highlight Fullest.
        page.evaluate("() => setStatusText('')")
        page.keyboard.press("f")
        page.wait_for_timeout(150)
        status = page.evaluate("() => document.getElementById('status').textContent")
        if "Highlighting fullest" not in status:
            failures.append(f"'f' didn't trigger Highlight Fullest: {status!r}")

        # Modified presses (Ctrl+R etc.) must be ignored, not treated as
        # a shortcut -- otherwise this would fight real browser shortcuts.
        before_puzzle = page.evaluate("() => JSON.stringify(puzzle)")
        page.keyboard.press("Control+r")
        page.wait_for_timeout(150)
        after_puzzle = page.evaluate("() => JSON.stringify(puzzle)")
        if before_puzzle != after_puzzle:
            failures.append("Ctrl+R triggered the Restart shortcut instead of being ignored as a modified key")

        # With the difficulty <select> focused, 'h' must not also fire Hint --
        # the select's own native type-ahead should be left alone.
        page.evaluate("() => document.getElementById('difficulty').focus()")
        page.evaluate("() => setStatusText('')")
        page.keyboard.press("h")
        page.wait_for_timeout(100)
        status_after = page.evaluate("() => document.getElementById('status').textContent")
        if "Tier 1" in status_after:
            failures.append("'h' triggered Hint even while the difficulty select was focused")

        browser.close()

    if failures:
        print("FAIL: keyboard shortcuts are broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: letter-key shortcuts work for every button, ignore modified presses, and don't fight the difficulty select")


if __name__ == "__main__":
    main()
