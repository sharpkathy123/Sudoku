"""Regression test: placing a correct digit clears a leftover wrong-digit
status message instead of leaving it on screen.

Reported live, right after the keyboard-focus fix let typing wrong-then-
correct digits work smoothly for the first time: "...and then nothing
happens when I type the correct digit." The digit was actually being
placed correctly the whole time -- but the status area still showed the
stale "X doesn't belong in row Y, column Z" message from the earlier
wrong attempt, since the correct-placement code path never touched
#status at all. With no visible change to point to, it read as if the
correct keypress had been silently ignored.

Fixed by clearing the status text as part of a successful placement,
the same way onCellClick() already clears one specific stale nudge
("Select a cell first.") when it goes stale.
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

        target = page.evaluate(
            """() => {
                for (let r = 0; r < 9; r++) {
                    for (let c = 0; c < 9; c++) {
                        if (puzzle[r][c] === 0) {
                            const correct = solution[r][c];
                            const wrong = correct === 9 ? 1 : correct + 1;
                            const cell = board.children[r * 9 + c];
                            cell.tabIndex = 0;
                            onCellClick(cell);
                            cell.focus();
                            return { r, c, correct, wrong };
                        }
                    }
                }
            }"""
        )

        page.keyboard.press(str(target["wrong"]))
        page.wait_for_timeout(100)
        status_after_wrong = page.evaluate("() => document.getElementById('status').textContent")
        if "doesn't belong" not in status_after_wrong:
            failures.append(f"setup failed: no wrong-digit message shown ({status_after_wrong!r})")

        page.keyboard.press(str(target["correct"]))
        page.wait_for_timeout(100)

        value = page.evaluate(f"() => getCurrentGrid()[{target['r']}][{target['c']}]")
        status_after_correct = page.evaluate("() => document.getElementById('status').textContent")

        if value != target["correct"]:
            failures.append(f"correct digit wasn't placed (grid value: {value})")
        if "doesn't belong" in status_after_correct:
            failures.append(
                f"stale wrong-digit message survived a correct placement: {status_after_correct!r}"
            )

        browser.close()

    if failures:
        print("FAIL: a correct placement doesn't clear a stale wrong-digit message:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: placing the correct digit clears a leftover wrong-digit status message")


if __name__ == "__main__":
    main()
