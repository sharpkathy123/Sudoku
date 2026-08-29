"""Regression test: every plain button must have an explicit tabindex.

Reported live using an attached keyboard on iOS: after leaving the
difficulty dropdown, Tab jumped straight to the first number tile,
skipping New Game, Restart, Clear Pencil Marks, Highlight Fullest,
Guard Pencil, Auto-Pencil, Pencil Mode, and Hint entirely -- every plain
<button> in between. Root cause is a well-documented iOS Safari default:
with an external keyboard, Tab only stops at form fields (like a
<select>) and elements with an *explicit* tabindex attribute, skipping
plain buttons entirely -- unless the device has Settings > Accessibility
> Keyboards > Full Keyboard Access turned on. Since only the number tiles
and board cells had ever been given an explicit tabindex (for the
roving-focus keyboard work), they were the only things left to land on.

Chromium doesn't have this restrictive default (it already Tab-stops on
plain buttons), so this can't reproduce the actual skip the way most
tests here do. It instead freezes the fix directly: every button this
app defines must carry an explicit tabindex="0", which is the documented
workaround that makes a button Tab-reachable on iOS regardless of that
device setting.
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

        missing = page.evaluate(
            """() => {
                const missing = [];
                document.querySelectorAll('button').forEach(btn => {
                    if (!btn.hasAttribute('tabindex')) missing.push(btn.id || btn.textContent.trim());
                });
                return missing;
            }"""
        )
        if missing:
            failures.append(f"Button(s) with no explicit tabindex (iOS Tab will skip them): {missing}")

        browser.close()

    if failures:
        print("FAIL: some buttons aren't reliably Tab-reachable:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: every button has an explicit tabindex, so Tab reaches it even without iOS Full Keyboard Access")


if __name__ == "__main__":
    main()
