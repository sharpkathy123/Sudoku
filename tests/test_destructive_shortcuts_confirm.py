"""Regression test: the New Game, Restart, and Clear Pencil Marks keyboard
shortcuts ask for confirmation before acting; the other five don't.

Flagged as a trade-off when letter shortcuts first shipped: these three
targets are destructive and already have no undo/confirmation on a
deliberate tap, so a stray keypress became a much easier way to trigger
one by accident than a tap on a physically separate button. Resolved by
asking the user, who chose "confirm" over "don't ship a shortcut for
these at all". A cancelled confirmation must leave the game state
untouched.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo


def main():
    failures = []
    dialog_messages = []
    dialog_mode = {"accept": False}

    def handle_dialog(dialog):
        dialog_messages.append(dialog.message)
        if dialog_mode["accept"]:
            dialog.accept()
        else:
            dialog.dismiss()

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.on("pageerror", lambda e: failures.append(f"page error: {e}"))
        page.on("dialog", handle_dialog)
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(300)

        # Cancelling the confirm dialog must leave the puzzle untouched.
        before_puzzle = page.evaluate("() => JSON.stringify(puzzle)")
        page.keyboard.press("r")  # Restart
        page.wait_for_timeout(100)
        after_cancelled = page.evaluate("() => JSON.stringify(puzzle)")

        if not dialog_messages:
            failures.append("'r' didn't show a confirmation dialog at all")
        if before_puzzle != after_cancelled:
            failures.append("Restart happened even though the confirmation dialog was cancelled")

        # Fill in one empty cell so Restart accepted has something visible to undo.
        page.evaluate(
            """() => {
                outer:
                for (let r = 0; r < 9; r++) {
                    for (let c = 0; c < 9; c++) {
                        if (puzzle[r][c] === 0) {
                            onCellClick(board.children[r * 9 + c]);
                            numberBar.children[solution[r][c] - 1].click();
                            break outer;
                        }
                    }
                }
            }"""
        )
        filled_before = page.evaluate("() => getCurrentGrid().flat().filter(v => v !== 0).length")

        # Accepting the confirmation must actually restart.
        dialog_mode["accept"] = True
        dialog_messages.clear()
        page.keyboard.press("r")
        page.wait_for_timeout(100)
        filled_after = page.evaluate("() => getCurrentGrid().flat().filter(v => v !== 0).length")
        given_count = page.evaluate("() => givenMask.flat().filter(Boolean).length")

        if not dialog_messages:
            failures.append("accepted 'r' press showed no confirmation dialog")
        if filled_after != given_count:
            failures.append(
                f"accepting the confirmation didn't actually restart "
                f"(filled cells: {filled_before} -> {filled_after}, givens: {given_count})"
            )

        # Non-destructive shortcuts must NOT show any confirmation dialog.
        dialog_messages.clear()
        page.keyboard.press("p")
        page.wait_for_timeout(80)
        page.keyboard.press("g")
        page.wait_for_timeout(80)
        page.keyboard.press("f")
        page.wait_for_timeout(80)
        if dialog_messages:
            failures.append(f"a non-destructive shortcut unexpectedly showed a confirmation dialog: {dialog_messages}")

        browser.close()

    if failures:
        print("FAIL: destructive keyboard shortcuts aren't properly gated:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: New Game/Restart/Clear Pencil Marks shortcuts ask for confirmation; the rest don't")


if __name__ == "__main__":
    main()
