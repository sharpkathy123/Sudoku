"""Regression test: the "App updated" build stamp must survive status
messages.

The build stamp used to be appended as a child of #status. setStatusText()
replaces #status's entire contents via `textContent = text` on every hint,
toggle, or action message — which destroyed the build stamp the very first
time any status message appeared, permanently, until a full page reload.

Fixed by giving the build stamp its own sibling element (#buildInfo),
entirely outside of what setStatusText() touches.
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
        page.wait_for_timeout(500)

        build_before = page.inner_text("#buildInfo")
        if "App updated" not in build_before:
            failures.append(f"Build stamp not present on load: {build_before!r}")

        # Trigger several different status messages in a row.
        page.click("#HintBtn")
        page.wait_for_timeout(200)
        page.click("#highlightLeastBtn")
        page.wait_for_timeout(200)
        page.click("#pencilToggle")
        page.wait_for_timeout(200)

        build_after = page.inner_text("#buildInfo")
        if build_after != build_before:
            failures.append(f"Build stamp changed/disappeared after status messages: {build_after!r}")

        browser.close()

    if failures:
        print("FAIL: build stamp does not survive status messages:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: the build stamp survives hint, highlight, and toggle status messages")


if __name__ == "__main__":
    main()
