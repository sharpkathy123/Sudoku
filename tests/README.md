# Browser regression tests

These complement the in-page `?test` suite built into `index.html`
(open `index.html?test` in a browser and check the console). That
suite is great for pure solving-logic checks — it can call functions
like `findHiddenSingle` or `meetsDifficultyBar` directly — but it
can't check things that only exist once a real browser renders and
interacts with the page: actual pixel output, real offline network
conditions, or a sequence of clicks producing the right DOM state.
That's what the scripts here are for.

Every test here started as a script written to verify one specific
bug fix. They're kept as standalone, runnable regression tests so the
same bug can't silently come back.

## Prerequisites

```
pip install playwright
playwright install chromium
```

(If you're running inside an environment that already provides a
pre-installed Chromium — e.g. Claude Code's sandboxes, which set
`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers` — `tests/_helpers.py`
detects and uses it automatically; you can skip `playwright install`.)

## Running

Each file is a standalone script — no test runner, no server to start
by hand (each one spins up and tears down its own local HTTP server
serving the repo root):

```
python3 tests/test_app_icon.py
python3 tests/test_offline_playability.py
python3 tests/test_deselect_on_outside_tap.py
```

Each prints `PASS: ...` and exits 0 on success, or prints `FAIL: ...`
with specifics and exits 1 on failure.

## What's covered

- **`test_app_icon.py`** — the generated app icon (a `<canvas>` drawing
  exported as a data: URL) is decoded and sampled along all four
  internal grid dividers. Catches a truncated/missing line like the
  one that once left the icon's bottom-right cell without a border.
  Also checks a real favicon is served with no fallback `/favicon.ico` 404.
- **`test_offline_playability.py`** — verifies the Service Worker
  actually activates and controls the page, then uses Playwright's
  real network-offline simulation (not just "the code looks right")
  to confirm the app still loads and renders a full board with the
  network completely cut off.
- **`test_deselect_on_outside_tap.py`** — clicks a cell and a number
  tile to select them, then taps outside the board/controls and
  checks the selection actually clears, while confirming real
  controls (like the Hint button) still work normally afterward.
- **`test_corrupted_save_recovery.py`** — writes an all-zero
  puzzle/solution (the shape of a save made before the very first
  puzzle generation ever completed) into localStorage and checks the
  app discards it and generates a real puzzle, rather than resuming a
  permanently blank, all-glowing board with no way to ever win it.
- **`test_resume_no_spurious_glow.py`** — completes a row for real,
  saves, and reloads, checking that resuming a game with real prior
  progress doesn't re-trigger glow for units that were already done in
  an earlier session.
- **`test_tap_stops_glow.py`** — completes a row and checks that a
  plain tap anywhere immediately clears the in-progress glow, instead
  of forcing you to sit through it.
- **`test_solution_grid_randomness.py`** — generates several puzzles
  and checks their solution grids actually differ, catching a bug
  where every puzzle's real answer key was the exact same grid every
  time (only which cells were removed as givens was ever randomized).
- **`test_hint_trace_persistence.py`** — a hint's highlight survives
  clicking the hinted cell and clicking elsewhere, but clears once the
  hinted cell is correctly filled in.
- **`test_status_height_stable.py`** — #status never overflows its
  fixed height, and the Hint button never physically moves between
  hint tiers (it used to move enough that a third tap in the same
  spot could land on Guard Pencil and silently disable it).
- **`test_build_stamp_persists.py`** — the "App updated" stamp
  survives hint/highlight/toggle status messages instead of being
  permanently destroyed by the first one.
- **`test_auto_pencil_preserves_notes.py`** — Auto-Pencil leaves a
  hand-marked cell alone instead of silently discarding its notes,
  and pencil marks are refused on an already-filled cell.
- **`test_wrong_digit_status_message.py`** — a legal-but-wrong digit
  shows a plain status message naming the digit and cell location
  (not just an easy-to-miss 400ms red flash), never actually lands on
  the board, and doesn't overflow #status's fixed height.
- **`test_board_uses_available_space.py`** — the board fills most of
  the viewport width on phones and keeps growing on larger screens,
  instead of hitting a small fixed pixel cap and going no further.
- **`test_visual_overhaul_colors_and_motion.py`** — "Highlight Fullest"
  no longer uses its old, disliked amber color, and animations/
  transitions collapse to near-zero under `prefers-reduced-motion`.

## Adding a new one

When you fix a bug that the in-page `?test` suite couldn't have
caught (anything needing real rendering, real network conditions, or
a multi-step interaction), consider adding a script here rather than
just fixing it and moving on. Follow the existing pattern: use
`_helpers.serve_repo()` and `_helpers.launch_browser()`, collect
failures into a list, and exit 1 with specifics if any failed.
