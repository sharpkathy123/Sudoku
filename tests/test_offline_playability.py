"""Regression test for real offline play (REQUIREMENTS.md item 1).

An earlier version of this app registered its Service Worker from a
data: URL, which every standards-compliant browser silently refuses —
so "offline support" never actually worked despite the code (and the
README) claiming it did, and despite it appearing to work in casual
testing thanks to incidental browser HTTP caching. This test uses
Playwright's real network-offline simulation (not just "should work
in theory") to verify the page still loads and is playable with the
network fully cut off, after one prior online visit.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)
        context = browser.new_context()
        page = context.new_page()
        page.on("pageerror", lambda e: failures.append(f"page error: {e}"))

        # First visit online, so the Service Worker installs and precaches.
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_timeout(1000)

        sw_state = page.evaluate(
            """async () => {
                const reg = await navigator.serviceWorker.getRegistration();
                return reg ? reg.active?.state : null;
            }"""
        )
        if sw_state != "activated":
            failures.append(f"Service Worker did not activate on first visit (state: {sw_state})")

        # Reload once so this navigation is actually controlled by the SW.
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(500)
        controlled = page.evaluate("() => !!navigator.serviceWorker.controller")
        if not controlled:
            failures.append("Page is not controlled by the Service Worker after a normal reload")

        # Now go truly offline and reload. A missing/broken Service Worker
        # makes this raise outright (no cache to fall back to) rather than
        # just render an incomplete page, so treat that as a failure too.
        context.set_offline(True)
        try:
            page.reload(wait_until="load")
            page.wait_for_timeout(500)
            board_cell_count = page.evaluate("() => document.querySelectorAll('.cell').length")
        except Exception as e:
            board_cell_count = 0
            failures.append(f"Offline reload failed outright: {e}")
        else:
            if board_cell_count != 81:
                failures.append(f"Offline reload did not render a full board (found {board_cell_count} cells)")

        context.set_offline(False)
        browser.close()

    if failures:
        print("FAIL: offline playability is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: the app installs a Service Worker and remains fully playable with the network off")


if __name__ == "__main__":
    main()
