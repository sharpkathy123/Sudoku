"""Regression test for the persistent hint-trace highlight.

A player reported that hint highlighting used to leave a visible trace
of what the hint was about, so they wouldn't lose their place while
figuring out how to act on it — and that they only ever glimpsed
remnants of it (a flash from blue to amber) before it vanished. Root
cause: the hinted cell(s) got the same "highlight-least" class
Highlight Fullest uses, but onCellClick()'s clearNumberHighlights()
strips that class from every cell — and clicking the hinted cell (or
any cell) to act on the hint is exactly what triggers onCellClick().
So the trace was wiped the moment anyone tried to use it.

Fixed with a dedicated "hint-trace" class, deliberately untouched by
clearNumberHighlights(), cleared only by showHint() (a new hint
supersedes the old trace) or by correctly placing the value in the
hint's own primary cell.

This checks: a hint's trace survives clicking the hinted cell, and
survives clicking an unrelated cell, but clears once the hinted cell
is correctly filled in.
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

        page.click("#HintBtn")
        page.wait_for_timeout(300)
        target = page.evaluate("() => hintTraceTarget")
        if not target:
            failures.append("showHint() did not set a hintTraceTarget")
            print("FAIL:", failures)
            sys.exit(1)

        target_idx = target["r"] * 9 + target["c"]
        trace_count_initial = page.evaluate("() => document.querySelectorAll('.cell.hint-trace').length")
        if trace_count_initial == 0:
            failures.append("No .hint-trace cells appeared after requesting a hint")

        # Clicking the hinted cell itself (the natural first step in acting
        # on a hint) must not clear the trace.
        page.locator(".cell").nth(target_idx).click()
        page.wait_for_timeout(200)
        if page.evaluate("() => document.querySelectorAll('.cell.hint-trace').length") != trace_count_initial:
            failures.append("Clicking the hinted cell cleared the hint trace")

        # Clicking an unrelated cell must not clear it either.
        other_idx = page.evaluate(
            """(skip) => {
                for (let i = 0; i < 81; i++) {
                    if (i === skip) continue;
                    const cell = document.querySelectorAll('.cell')[i];
                    if (!cell.classList.contains('given') && !cell.querySelector('.cell-value').textContent.trim()) {
                        return i;
                    }
                }
                return -1;
            }""",
            target_idx,
        )
        if other_idx >= 0:
            page.locator(".cell").nth(other_idx).click()
            page.wait_for_timeout(200)
            if page.evaluate("() => document.querySelectorAll('.cell.hint-trace').length") != trace_count_initial:
                failures.append("Clicking an unrelated cell cleared the hint trace")

        # Correctly placing the hinted value in its own target cell should
        # clear the trace — the hint has been acted on.
        correct_val = page.evaluate(f"() => solution[{target['r']}][{target['c']}]")
        page.locator(".cell").nth(target_idx).click()
        page.wait_for_timeout(150)
        page.locator("#numberBar .number-tile").nth(correct_val - 1).click()
        page.wait_for_timeout(300)
        if page.evaluate("() => document.querySelectorAll('.cell.hint-trace').length") != 0:
            failures.append("Hint trace did not clear after correctly placing the hinted value")

        browser.close()

    if failures:
        print("FAIL: hint-trace persistence is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: hint trace survives ordinary clicking and clears once the hint is acted on")


if __name__ == "__main__":
    main()
