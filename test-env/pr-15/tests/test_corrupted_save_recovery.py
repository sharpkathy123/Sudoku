"""Regression test for a corrupted saved-game state.

A player reported "Resumed saved game" showing a completely blank
board with every cell glowing. Root cause: localStorage held a saved
state whose puzzle/solution were both all-zero grids — the app's own
initial placeholder values (see `let puzzle = ...fill(0)` at the top
of index.html) — most likely from a save that happened before the
very first puzzle generation ever completed. loadSavedGameState()
trusted this blindly: an all-zero board matches an all-zero
"solution" in every row/column/box/digit, so every completion check
reads true and the whole board glows at once, and there's no way to
ever win (and thus self-heal via the normal
`localStorage.removeItem()` on a real win) a puzzle with no givens.

This writes exactly that corrupted shape into localStorage, loads the
page, and checks the app discards it and generates a real puzzle
instead of resuming the broken one.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo

STORAGE_KEY = "sudoku_active_game_v1"


def corrupted_state():
    zero_grid = [[0] * 9 for _ in range(9)]
    cells = [{"r": r, "c": c, "val": 0, "pencils": []} for r in range(9) for c in range(9)]
    return {
        "puzzle": zero_grid,
        "solution": zero_grid,
        "difficulty": "medium",
        "givenMask": [[False] * 9 for _ in range(9)],
        "guardNotesMode": True,
        "cells": cells,
    }


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.on("pageerror", lambda e: failures.append(f"page error: {e}"))

        # First load normally so the app's own code (not this script) is
        # what's running when we inject the corrupted save.
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.evaluate(
            "([key, state]) => localStorage.setItem(key, JSON.stringify(state))",
            [STORAGE_KEY, corrupted_state()],
        )

        page.reload(wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(500)

        filled_cells = page.evaluate(
            "() => [...document.querySelectorAll('.cell-value')].filter(v => v.textContent.trim()).length"
        )
        glowing_cells = page.evaluate("() => document.querySelectorAll('.cell.glow').length")

        if filled_cells == 0:
            failures.append("App resumed a blank board instead of discarding the corrupted save")
        if glowing_cells > 0:
            failures.append(f"{glowing_cells} cells are glowing — every unit is reading as falsely 'complete'")

        browser.close()

    if failures:
        print("FAIL: corrupted-save recovery is broken:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: an all-zero corrupted saved game is discarded in favor of a real, fresh puzzle")


if __name__ == "__main__":
    main()
