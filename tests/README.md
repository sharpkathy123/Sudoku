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
- **`test_hint_curriculum_wording.py`** — Full House/Naked Single/
  Hidden Single/Cross-Hatching no longer name the exact answer cell
  in tier 1 (or, for Naked Single, tier 2), XY-Wing/XYZ-Wing's tier 3
  names the digit being eliminated, and a first-ever visit defaults
  to Easy difficulty.
- **`test_hints_ignore_pencil_marks.py`** — hints always reason from
  the true, constraint-derived candidate set, never from the player's
  own (possibly incomplete or stale) hand-written pencil marks. Catches
  the exact bug that once let a Unique Rectangle hint tell a player to
  place a digit the game then rejected as wrong.
- **`test_hint_and_board_both_visible.py`** — the hint/status text and
  the whole board fit in one ordinary phone screen at the same time,
  and the Hint button sits on the same row as the Pencil Mode toggle.
- **`test_keyboard_accessibility.py`** — the board and number bar are
  fully operable via keyboard (arrow keys to move, digits 1-9 to place),
  cells expose a live-updating `aria-label`, `#status` is an ARIA live
  region, toggle buttons expose `aria-pressed`, the win overlay is
  `aria-hidden` until an actual win, and the page has one `<h1>` inside
  a `<main>` landmark.
- **`test_eliminations_never_contradict_solution.py`** — audits 60
  freshly generated puzzles across every difficulty and confirms no
  hint ever eliminates a cell's actual solution digit. Catches the
  `countSolutions()` uniqueness-check bug where some "Hard" puzzles
  weren't really uniquely solvable, which broke Unique Rectangle's
  eliminations in particular (its whole premise is that keeping a
  digit would create a second solution — meaningless if one already
  exists elsewhere).
- **`test_glow_visible_under_reduced_motion.py`** — completion glow
  and the hint arrival-glow are still visibly present (a steady ring,
  not a pulse) under `prefers-reduced-motion`, instead of being
  collapsed to an animation so fast nobody can ever see it.
- **`test_keyboard_focus_stays_visible.py`** — the selection outline
  stays clearly visible after arrow-navigating onto a filled cell (amid
  its same-number highlight), and a plain Tab landing directly on the
  board's tab-stop cell syncs selection too, not just arrow-key moves.
- **`test_tap_sets_real_focus.py`** — tapping any button, the difficulty
  select, or a board cell sets real `document.activeElement` focus, so
  Tab afterward continues from there. Freezes the invariant behind a fix
  for an iOS-Safari-only quirk (tapped buttons/selects don't get real
  focus by default there) that Chromium can't reproduce to show a
  before/after contrast.
- **`test_all_buttons_tab_reachable.py`** — every button has an explicit
  `tabindex`, so Tab reaches it on iOS even without Full Keyboard Access
  turned on (which otherwise makes Tab skip plain buttons entirely).
- **`test_hint_progresses_past_seen_hints.py`** — asking for another
  hint right after fully cycling one (without placing anything) moves
  on to a different technique instead of repeating the same one
  forever, when more than one technique is actually available.
- **`test_keyboard_shortcuts.py`** — every button has a working
  letter-key shortcut, modified presses (Ctrl/Cmd/Alt) are ignored
  rather than treated as a shortcut, and the difficulty select's own
  native type-ahead isn't double-triggered by the same key.
- **`test_hint_selects_target_cell.py`** — activating Hint (by keyboard,
  not a tap) moves real keyboard focus onto the hinted cell itself, not
  just a purple highlight on top of a cell that's still only visually
  marked while the Hint button silently keeps real focus. Also checks an
  arrow key immediately after Hint actually moves selection, proving
  focus is really on the board.
- **`test_board_shortcut.py`** — "B" jumps keyboard focus straight onto
  the board (the previously selected cell, or the roving tab-stop cell if
  none), from anywhere else on the page.
- **`test_destructive_shortcuts_confirm.py`** — the New Game, Restart, and
  Clear Pencil Marks keyboard shortcuts show a confirmation dialog before
  acting (and do nothing if it's cancelled), while the other five
  shortcuts never show one.
- **`test_digit_key_keeps_board_focus.py`** — typing a digit on the
  keyboard (right or wrong) shows the usual status message and leaves
  real keyboard focus on the board cell, instead of the iOS tap-focus
  workaround silently yanking it onto the number tile the keypress
  happens to relay through.
- **`test_correct_digit_clears_stale_status.py`** — placing a correct
  digit clears a leftover "X doesn't belong..." message from an earlier
  wrong attempt, instead of leaving it on screen looking like the
  correct keypress did nothing.
- **`test_pencil_toggle_keeps_selection_visible.py`** — tapping a number
  tile to toggle a pencil mark keeps the selected cell visibly marked
  `.selected` and keeps real keyboard focus on the board, so an arrow
  key right afterward still moves the selection instead of doing
  nothing.
- **`test_roving_tabindex_follows_click.py`** — clicking/selecting a cell
  moves the roving tabindex there too, not just arrow-key moves and
  Hint, so "B" and a bare Tab always land on the cell actually selected
  instead of a stale one from an earlier Hint.
- **`test_naked_single_wording_matches_reasoning.py`** — a Naked Single
  hint only claims digits are "already present" in the row/column/box
  when that's actually true; when the single remaining candidate depends
  on an earlier hint's own elimination instead, it says so rather than
  making a false claim the player can't verify by scanning for placed
  digits.
- **`test_hint_chains_eliminations.py`** — once an elimination-only hint
  (Naked Pair/Triple, Pointing/Claiming, X-Wing/Swordfish, the wings,
  Unique Rectangle) has been fully cycled, the *next* Hint press can find
  a genuinely different technique that only becomes visible after that
  elimination is actually applied — instead of recomputing identical raw
  candidates forever and repeating the same hint with no way to
  progress. Searches generated puzzles for a state exhibiting exactly
  this technique-chain dependency, since a puzzle's own difficulty
  rating already requires this kind of chaining to be solvable by pure
  logic at Hard/Expert.

## Adding a new one

When you fix a bug that the in-page `?test` suite couldn't have
caught (anything needing real rendering, real network conditions, or
a multi-step interaction), consider adding a script here rather than
just fixing it and moving on. Follow the existing pattern: use
`_helpers.serve_repo()` and `_helpers.launch_browser()`, collect
failures into a list, and exit 1 with specifics if any failed.
