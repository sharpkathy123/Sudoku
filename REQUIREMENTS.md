# Requirements

This is the durable source of truth for what this Sudoku app is supposed to
do, separate from `README.md` (user-facing feature copy). `README.md`
previously listed several hint techniques and an offline-support claim that
didn't actually exist; both have since been implemented to match (see items
1–8 below) and the README corrected. Each item below has a verification
status. Where a requirement is enforced by an automated test, the test name
is given so a future change that breaks the requirement gets caught, not
just described.

Status legend: ✅ Met and verified · ⚠️ Met most of the time (bounded,
probabilistic) · ❌ Not currently met.

## 1. Offline play ("Airplane Mode") — ✅ Met (verified with real offline simulation)

**Requirement:** the game must be playable with no network connection,
including on a mobile device in Airplane Mode after being loaded once.

**Status:** met, via a real Service Worker — `sw.js`, a second file alongside
`index.html`. An earlier attempt registered a Service Worker from a `data:`
URL to keep everything in one file; browsers refuse to register a Service
Worker from anything other than an `http(s)` URL, so that registration
always failed silently and no offline caching ever actually happened. There
is no way to make a Service Worker work from a single inline file — this is
a platform restriction, not an implementation detail — so a second file is
the minimum deviation from "everything in one HTML file" needed to make this
requirement genuinely true rather than aspirational.

**How it works:** `sw.js` uses a network-first, cache-fallback strategy —
every successful online load refreshes a cache (`sudoku-cache-v1`) with the
current `index.html`; when a fetch fails (no connectivity), it serves the
last cached copy instead. Because the game itself makes zero runtime network
calls (no external CSS/JS/fonts/images — the touch icon is canvas-generated
and the manifest is an inline `data:` URI), caching the one HTML file is
sufficient; there's no separate app-shell asset list to keep in sync. No
manual versioning is needed for ordinary content updates — the network-first
strategy means the cache is refreshed on every online visit automatically;
`CACHE_NAME` only needs bumping if the caching *strategy itself* changes and
old cached entries should be discarded.

`index.html` registers it (`navigator.serviceWorker.register('./sw.js', {
scope: './' })`) guarded behind the same `http:`/`https:` protocol check as
before, so opening the file directly (`file://`) — where Service Workers
aren't supported at all — degrades harmlessly with no registration attempt.

**Verified with actual offline simulation**, not just "should work in
theory": loaded the page online (letting the Service Worker install,
activate, and cache the page), then set the browser context genuinely
offline (Playwright's `context.set_offline(True)`, not just throttling) and
reloaded — the page still loaded, the board rendered, and clicking Hint
still worked, with no console errors. This mirrors exactly what you
described experiencing on your phone (a system "no connection" warning that
doesn't actually stop the page from loading), except now it happens because
of a Service Worker deliberately caching the app, not by accident of
whatever the browser's ordinary HTTP cache happened to still be holding.

**Known limitation, same as any Service-Worker-based offline strategy:** the
very first visit still needs a network connection so there's something to
cache. A device that has never loaded the page online has nothing to fall
back to.

## 2–5. Difficulty calibration — ✅ Met (see per-tier notes)

**Requirement:**
- Easy: solvable using only easy-tier hints.
- Medium: needs at least one medium-tier hint; solvable at medium-or-easier.
- Hard: needs at least one hard-tier hint; solvable at hard-or-easier.
- Expert: needs at least one fallback (direct-reveal) hint.

Before this was implemented, the generator only checked that a puzzle had a
**unique solution** — given-count (38/32/27) was the only thing standing in
for difficulty, with no check that a puzzle generated for "Hard" actually
*needed* a hard technique, or that an "Easy" puzzle didn't secretly need one.
Testing this for real turned out to require an actual difficulty rater, not
just a test file — see the Testing section below for what that took.

**Tier count changed from 5 to 4 (Hard/Expert/Master → Hard/Expert).** The
old middle "Hard" tier existed solely to require X-Wing and nothing more —
but as Medium's own technique roster grew (Naked Triple, Claiming, checking
every unit instead of just rows), there was less and less room left for
X-Wing alone to be the one thing distinguishing a puzzle from Medium, and it
became the single least reliable tier to calibrate (see the old status notes
below, kept as history). X-Wing was folded into Medium's own qualifying
technique set instead of kept as its own slot, old Expert was renamed to
Hard, and old Master was renamed to Expert. Nothing about *what a puzzle
needs* changed for the renamed tiers — only the old X-Wing-only slot was
removed, and its technique now also satisfies Medium.

### Every generated puzzle used to have the exact same solution — ✅ Fixed

**Bug (reported by a player: "I know what the cells are going to be for
every difficulty level"):** `solveSudoku()`, used to generate each puzzle's
full answer key by solving a blank grid, always tried digits 1-9 in a fixed
order and always scanned cells in the same order — so solving an empty grid
always found the exact same "first" solution, every single time, for every
difficulty (row 1 was always `1 2 3 4 5 6 7 8 9`, row 2 always
`4 5 6 7 8 9 1 2 3`, etc., matching exactly what the player described). Only
*which cells got removed* as givens was ever randomized; the underlying
solved grid never varied at all — meaning an experienced player really could
memorize it and "solve" any puzzle at any difficulty from memory.

**Fix:** `solveSudoku()` now shuffles the digit-try order at each cell
before attempting placements, so solving an empty grid produces a different
random valid solution on every call. Callers that only need a yes/no
validity check (the seed-puzzle tests) are unaffected — shuffling which
solution is found doesn't change whether one exists.

**Side effect discovered while verifying the fix:** real random solution
grids turned out to be *much* harder to calibrate for the old X-Wing-only
Hard tier than the one fixed canonical grid the generator had always
actually been testing against — "New Game" at that tier went from an
occasional multi-second wait to consistently exhausting its full 450-attempt
budget (~19-20 seconds) every time. This is what motivated folding X-Wing
into Medium rather than just re-tuning the old tier's numbers: the old tier
wasn't just unreliable, it was unreliable specifically because the bug it
was calibrated against no longer applied once puzzles were genuinely random.

**Verified:** generated 5 consecutive puzzles and confirmed all 5 solution
grids were different (previously always identical); confirmed reverting the
fix reproduces the exact reported pattern. See
`tests/test_solution_grid_randomness.py`.

### Tier → technique mapping

All techniques live in one ordered list, `HINT_CASCADE` — used both to drive
live hints (`showHint()`) and to rate puzzles (`rateSolveWithTierCascade()`),
so the two can never disagree about what a puzzle needs. Order within a tier
is easiest-to-spot first.

| Tier | Techniques | Rank |
|---|---|---|
| Easy | Full House, Hidden Single / Cross-Hatching (box, row, *and* column), Naked Single | 1 |
| Medium | Naked Pair, Pointing Pair/Triple, Claiming Pair/Triple (Box-Line Reduction), Naked Triple, X-Wing | 2 |
| Hard | XY-Wing, XYZ-Wing, Unique Rectangle (Type 1), Swordfish | 3 |
| Expert | Fallback direct-reveal (nothing above solves it) | 4 |

This is the full "widely known techniques, newbie to mastery" roster
`README.md` describes. What changed to get there:

- **Hidden Single now scans rows and columns, not just boxes.** It used to
  only check 3×3 boxes (`findHiddenSingleInBox`); a hidden single confined to
  a row or column without also being box-confined was missed. Generalized to
  `findHiddenSingle()` using a shared `ALL_UNITS` list (27 units: 9 rows, 9
  columns, 9 boxes) that most of the newer techniques below also use.
- **Naked Pair now checks all 27 units, not just rows.** Same fix as above,
  generalized into `findNakedSubsetOfSize(candGrid, solutionGrid, size, ...)`,
  which also powers the new **Naked Triple** (`size=3`).
- **Claiming Candidates (Box-Line Reduction) is new** — the mirror image of
  the existing Pointing technique: a digit confined to one box *within* a
  row/column eliminates that digit from the rest of the box (Pointing goes
  the other way: confined to one row/column *within* a box). `README.md`
  had listed "Claiming Lines" as a feature before it existed.
- **XY-Wing, XYZ-Wing, and Unique Rectangle (Type 1) are new.** Also
  previously listed in `README.md` without existing. XY-Wing/XYZ-Wing use a
  shared `cellsSeeEachOther()` geometry check; Unique Rectangle scans all
  2-box-spanning 4-cell rectangles for the classic "three corners share a
  pair, the fourth has extras" deadly pattern.
- **Swordfish** was added in the previous pass (X-Wing generalized from 2
  rows/columns to 3) so Hard would have a technique of its own instead of
  sharing X-Wing with Medium.

### How calibration actually works

`rateSolveWithTierCascade(puzzle, solution, maxTierRank)` re-solves a puzzle
using only techniques at or below a given tier — the same technique
functions used for live hints, run headless against a plain grid. It reports
whether the puzzle was fully solved and which tiers were actually *needed*
along the way (an elimination technique that never removes a real candidate
doesn't count as "needed" — see the `eliminate` list each technique now
returns). `meetsDifficultyBar(puzzle, solution, difficulty)` turns that into
a yes/no against `DIFFICULTY_REQUIREMENTS`.

The generator (`createNewPuzzleAsync`) digs to a difficulty's nominal
given-count as before, then checks the bar. If it isn't met, it keeps
digging the *same* puzzle further (removing cells generally makes a puzzle
harder, so this converges far faster than re-rolling a whole new grid) down
to a floor (`DIFFICULTY_GIVENS`). If that still doesn't clear the bar, it
re-rolls a fresh solution and repeats, up to a bounded number of attempts
(`CALIBRATION_ATTEMPTS_BY_DIFFICULTY`). If the whole budget is exhausted, it
serves the closest candidate found rather than searching forever or freezing
the "New Game" button, and logs a `console.warn` so this is visible rather
than silent — in practice, this essentially never happens any more (see
below).

**A puzzle that overshoots its tier can't come back by digging further** —
removing givens only ever makes a puzzle harder or leaves it the same, never
easier. So while extending a dig toward the floor, the moment
`evaluateDifficultyBar` reports `overshoot: true` (the puzzle is already
unsolvable using techniques up to the tier's own ceiling), that trajectory is
abandoned immediately in favor of a fresh attempt, rather than continuing to
dig toward the floor for a result that can only get further away.

**Status by tier — ✅ across the board, and fast, since folding X-Wing into
Medium and removing the old standalone slot:**
- Easy: converges on the first or second dig almost every time.
- Medium: converges reliably within its budget (60 attempts); X-Wing being
  an acceptable qualifying technique now (alongside Naked Pair/Triple,
  Pointing, Claiming) only ever makes this *easier* to satisfy, never harder.
- Hard: spot-checked at 10/10 puzzles meeting the bar, generating in well
  under a second each. This tier held the *exact* techniques the old,
  unreliable "Expert" tier used to require (XY-Wing/XYZ-Wing/Unique
  Rectangle/Swordfish) — nothing about the requirement changed, only its
  name and the removal of the old X-Wing-only tier below it.
- Expert: spot-checked at 10/10, also well under a second each — same
  situation, this tier is exactly the old "Master" requirement (not solvable
  through Hard techniques) under a new name.

Before the tier consolidation, the old middle "Hard" tier (X-Wing only,
nothing else could qualify it) was the genuinely unreliable one — empirically
converging only around half the time even at a 450-attempt budget, and after
the solution-randomization fix below, effectively never converging at all
within budget (~19-20 seconds, every single "New Game" at that tier). That
specific failure mode is what's gone now: X-Wing has always remained useful
as a *hint* — nothing about the technique itself changed, and it still
appears in the same cascade position — it just no longer has to be the
*sole* qualifying technique for an entire difficulty tier by itself.

**The two hardcoded seed puzzles are currently unused.** `HARD_SEED_PUZZLES`
and `EXPERT_SEED_PUZZLES` are filtered through this same bar at load time
(so a seed can't sneak in without meeting it), and as of writing none of the
hand-picked puzzles actually require a Swordfish or resist every technique
through Swordfish — they were evidently chosen by feel (few givens) rather
than verified technique requirements. Both pools end up empty, and the
generic calibrated digging loop is what actually delivers Hard and Expert
puzzles today. The seed machinery is left in place — if better-chosen seeds
are added later, they'll be used automatically provided they clear
`meetsDifficultyBar`.

## 7. Three-tier hint wording, on every technique — ✅ Met

**Requirement:** first press points at a cell and names the technique;
second press gives more help without revealing the number; third press
gives the exact, actionable detail. This must hold for every technique, not
just the simple ones — the goal is a hint system someone can ride from
absolute newbie all the way through mastering every widely-known technique.

Every entry in `HINT_CASCADE` (all 12 techniques, from Full House through
Swordfish) returns the same `{ tier1, tier2, tier3, tier, method }` shape.
`tier1` always names the technique and points at the cell or unit; `tier2`
explains the pattern without ever naming the actual digit; `tier3` is fully
actionable. For placement techniques (Full House, singles) tier 3 says
exactly which number to enter. For elimination-only techniques (Naked
Pair/Triple, Pointing/Claiming, X-Wing, XY-Wing, XYZ-Wing, Unique Rectangle,
Swordfish) tier 3 says exactly which pencil marks to erase and from where —
there usually isn't a number to *enter* yet, since the technique's job is
narrowing candidates, not placing a digit. That's intended, not a gap.

Verified by `testHintObjectsWellFormed`: solves several puzzles per
difficulty through the full cascade and checks every hint object produced
along the way (from whichever techniques actually fire) has non-empty
tier1/2/3 text, a valid tier, and a real target cell — so a future technique
added without full 3-tier text, or a typo that leaves one blank, fails the
suite instead of shipping quietly.

**Fixed bug:** Pointing Pair/Triple's tier 3 sometimes claimed an
elimination "leaves N in Row R, Column C" when it didn't. The check for
this (`makesSingle`) tested the wrong cell entirely — it looked at whether
the *box's own* candidate cell would have one candidate left if digit `n`
weren't a candidate there, which has nothing to do with the elimination
(Pointing only removes `n` from cells *outside* the box; it never touches
candidates inside the box). Reported from a real hint: Box 6 correctly had
digit 2 confined to Row 5, but the actual elimination only removed one
pencil mark elsewhere in Row 5, from a cell that still had another
candidate left — no single was created anywhere, yet the hint claimed one.
Fixed with `singleCellResolvedByElimination`, which checks the cells
actually being eliminated from, not the box's own cells. Now caught
permanently by `testHintObjectsWellFormed`: it parses any "This leaves N
in Row R, Column C" claim out of a hint's tier3 text and verifies that
cell's candidates, after applying the hint's own `eliminate` list, really
do resolve to exactly `[N]` — so this exact bug, or the same mistake in
any future technique, fails the suite instead of shipping.

## 8. Human-like hint ordering — ✅ Met

**Requirement:** hints should come in the order a person would actually try
them, prefer techniques that don't need pencil marks until they're actually
needed, and respect whatever pencil marks the player has already entered.

- `HINT_CASCADE` is one ordered list, easiest first: Full House → Hidden
  Single → Naked Single (no candidate-tracking needed at all) → Naked Pair →
  Pointing → Claiming → Naked Triple → X-Wing (medium) → XY-Wing →
  XYZ-Wing → Unique Rectangle → Swordfish (hard) → fallback reveal
  (expert). Both `showHint()` (live hints) and `rateSolveWithTierCascade()`
  (difficulty rating) walk this exact same list, so what a player is told
  and what the generator verified a puzzle needs can never drift apart.
- `getCandidatesGrid()` uses the player's own active pencil marks as the
  candidate set for a cell once they've entered *any* mark there, and falls
  back to full rule-based candidates (`isSafe`) otherwise. This means a hint
  reflects what the player has actually narrowed down, not a fresh
  from-scratch computation.
- **Tier 1 says "Look at pencil marks in..." for every technique that is
  literally impossible to spot without candidates written down** (Naked
  Pair/Triple, Pointing/Claiming, X-Wing, XY-Wing, XYZ-Wing, Unique
  Rectangle, Swordfish, and the pencil-mark variant of Hidden Single) —
  a newbie who hasn't turned on Pencil Mode or used Auto-Pencil yet has no
  way to even attempt these otherwise, and the hint didn't used to say so.
  Full House, Naked Single, and the Cross-Hatching variant of Hidden Single
  are correctly left unchanged: those are genuinely readable straight off
  the placed digits, no marks required, so saying "look at pencil marks"
  there would be actively wrong instruction. Sample of what each technique
  says now: `Naked Pair: Look at pencil marks in Row 6 (Row 6, Col 4 / Row
  6, Col 7). Try using "Naked Pair".` vs `Full House: Look at Row 1, Column
  4 in Box 2. Try using "Full House".`
- **Fixed bug: multi-cell hints only ever highlighted one cell, silently.**
  `showHint()` added the `highlight-least` class (the same one "Highlight
  Fullest" uses) to the primary cell, then immediately called
  `onCellClick(cell)` — which calls `clearNumberHighlights()` internally,
  stripping `highlight-least` off *every* cell, including the one it was
  just added to, before the browser ever painted it. So the class was being
  added and removed in the same synchronous tick; only the separate `glow`
  flash (untouched by that clear) was ever visible. This meant every
  multi-cell technique (Naked Pair/Triple, Pointing/Claiming, X-Wing,
  Swordfish, the wings, Unique Rectangle) visually pointed at only one of
  the several cells its own tier 1 text names — reported as "past
  functionality was lost somewhere along the way."
  Fixed by reordering (`onCellClick` first, then apply the highlight) and
  giving every multi-cell technique a `highlightCells` list of every cell
  its hint text refers to (the naked subset's cells, the box cells sharing
  a confined candidate, the fish pattern's corners, the wing's pivot and
  both pincers, the rectangle's four corners) — all styled the same way, so
  a Naked Pair now highlights both its cells the same way Highlight Fullest
  highlights a whole unit, not just the first one. (The exact class used for
  this styling changed since — see the next bug below.)
  Techniques with only one relevant cell (Full House, Naked Single, Hidden
  Single, the fallback reveal) are unaffected — they still highlight just
  that cell, correctly.
  Verified against the live game (not just unit-level function output):
  drove several puzzles to a state where a specific multi-cell technique
  was next, called the real `showHint()`, and confirmed the cells that
  actually got highlighted in the DOM exactly matched the technique's
  own `highlightCells` — checked for Naked Pair, Pointing Pair, and
  Claiming Pair. `testHintObjectsWellFormed` now also checks that whenever
  `highlightCells` is present, every cell in it is in-bounds and the list
  includes the hint's own primary target cell.
- **Fixed bug: the hint highlight vanished the instant anyone tried to act
  on it.** The fix above reused `highlight-least` — the same class Highlight
  Fullest uses — to mark a hint's cells. But `onCellClick()`'s
  `clearNumberHighlights()` strips that class from every cell, and clicking
  the hinted cell (the natural first step in acting on a hint) is exactly
  what calls `onCellClick()`. So the highlight was cleared the moment a
  player tried to use it — reported as only ever glimpsing "remnants" of a
  trace (a flash from the hint's blue `glow` pulse to amber
  `highlight-least`) before it disappeared, with no way to keep track of
  which cell a hint was about while figuring out how to act on it. The
  shared amber color was also a separate complaint on its own — the same
  color meaning two different things (a hint's target vs. Highlight
  Fullest's nearly-complete unit) didn't read cleanly against the rest of
  the palette.
  Fixed with a dedicated `hint-trace` class (a violet distinct from every
  other highlight color in use) and dedicated state (`hintTraceCells`,
  `hintTraceTarget`) that `clearNumberHighlights()` deliberately does not
  touch. The trace now survives ordinary clicking — selecting the hinted
  cell, selecting an unrelated cell, tapping outside the board — and clears
  only when a new hint is requested (superseding the old trace) or when the
  hint's own target cell is filled in with the correct value (the hint has
  been acted on). Verified with `tests/test_hint_trace_persistence.py`: the
  trace survives clicking the hinted cell and an unrelated cell, then
  clears on correct placement — confirmed to fail against the prior
  `highlight-least`-based approach and pass with the fix.
- **Known intentional edge case:** if a player's pencil marks for a cell are
  incomplete or wrong, the hint engine trusts them as the candidate universe
  for that cell anyway (garbage in, garbage out) — this matches how a real
  hint/checker built on your own notes should behave, rather than silently
  overriding what you wrote.
- **Fixed bug:** a cell can legitimately be a Hidden Single from more than
  one unit's perspective at once (e.g. the only open row-cell for a digit,
  and separately the only open box-cell for it). `findHiddenSingle` used to
  iterate all rows, then all columns, then all boxes (`ALL_UNITS`'s natural
  order), so it always reported the row/column framing in that case — even
  when the box framing was the more direct, obvious-to-a-human explanation
  (a compact 3x3 area blocked by as few as two other rows/columns reads far
  more clearly than the same fact traced row-by-row through a mix of column
  and box eliminations). Fixed by checking boxes first (`UNITS_BOX_FIRST`),
  matching how people actually cross-hatch. Caught from a real hint a player
  saw explained as "Row 4" when "Box 6" was the far more obvious framing of
  the exact same deduction — the math wasn't wrong, the explanation was
  needlessly confusing.

**When asked "does this affect other techniques too," these were checked
and found:**

- **Naked Pair / Naked Triple — same bug, fixed the same way.** Two (or
  three) cells can share both a row/column *and* a box at once. Verified
  empirically: in a sample of 63 naked-subset instances across generated
  puzzles, ~8% had this ambiguity, and `findNakedSubsetOfSize` (which also
  iterates `ALL_UNITS`) always picked the row/column framing for the same
  reason as Hidden Single. Fixed by switching it to `UNITS_BOX_FIRST` too;
  re-verified the same sample now always picks the box framing when both
  are valid.
- **Full House — same shape of bug in theory, not worth fixing.** Checked
  empirically (no occurrences found in a smaller sample) and reasoned about
  separately: unlike Hidden Single, a Full House explanation is equally
  simple regardless of which unit is named ("count 1-9 in this row" vs "in
  this box") — there's no more-confusing framing to accidentally prefer, so
  even if the same row-before-box tie-break occurs, it doesn't produce a
  worse hint the way it did for Hidden Single.
- **X-Wing / Swordfish — a different, and actually larger, bug.** Not a
  confusing-explanation issue: `findXWing`/`findSwordfish` only ever checked
  one orientation of the pattern (a digit confined to N columns across N
  rows), never its mirror image (confined to N rows across N columns).
  Verified empirically this isn't rare: about 1 in 8 solving steps sampled
  across Medium/Hard/Expert puzzles had a column-oriented X-Wing available
  that the row-only search would never find at all — meaning some puzzles
  got shown a harder technique than actually necessary, or were mis-rated
  as needing more than Medium when a column X-Wing would have sufficed
  (this was measured before the tier consolidation, when X-Wing still had
  its own dedicated middle tier — the underlying finding is unchanged, only
  which tier X-Wing counts toward has moved since).
  Fixed by generalizing both into one axis-parameterized search
  (`findFishAlongAxis`) tried in both directions. Re-verified against the
  same sample: 0 missed column patterns after the fix (was 317 of 2557
  checked steps). As a side effect, that tier's calibration hit rate also
  improved (roughly 50% → 65% in spot-checks) since there are now more
  valid X-Wing instances to find.
- **The wing/rectangle techniques (XY-Wing, XYZ-Wing, Unique Rectangle) —
  not exposed to this bug class.** Their explanations don't hinge on a
  choice between interchangeable unit framings the way row/column/box-based
  techniques do, so there's no equivalent tie-break to get wrong. They can
  still only report one instance when multiple exist on a board (whichever
  their scan order reaches first), but that's an arbitrary-choice-among-
  equals situation, not a systematically-worse-framing one.

## 9. Are the regression tests worth keeping?

Yes — keep them, but the honest answer is that they were narrower than they
looked, and today's work is a concrete example of exactly the gap you
suspected.

Before this change, the suite (`?test` in the URL) only verified the
**generator never produces a broken grid** — no duplicate digits, always a
unique solution. That's real, worthwhile coverage (randomized digging logic
is exactly the kind of thing that silently breaks in a refactor), but it
never touched difficulty calibration, hint correctness, or anything in the
UI layer. Two concrete illustrations from today:

- The previous `testDifficultyTierQuality` test asserted only that *some*
  hint technique applied to a generated puzzle, for any difficulty — which
  is true almost by construction and would pass even for a puzzle whose
  "hint strategy" was the same for Easy and Expert alike. It's been replaced
  by real per-tier calibration tests.
- While building this, a test wording bug surfaced live: an early version of
  `testSeedPoolsNotEmpty` was intended to catch exactly the situation this
  work uncovered (both seed pools ending up empty) — but the seed-validity
  tests it was meant to complement (`testExpertSeedPuzzlesValidity`, etc.)
  loop `for (i = 0; i < pool.length; i++)`, which trivially "passes" over an
  empty array with zero assertions ever running. A validity test that can't
  fail when there's nothing to validate is a real blind spot, and it's the
  same shape of bug the original test suite had at a larger scale.

Current test list (`?test`):
- `testIsSafeEngine` — core constraint-checking correctness.
- `testEasyPuzzlesGenerator` — generator produces a valid, uniquely-solvable grid.
- `testEasyPuzzleCalibration` — item 2.
- `testMediumPuzzleCalibration` — item 3.
- `testHardPuzzleCalibration` — item 4.
- `testExpertPuzzleCalibration` — item 5.
- `testHardSeedPuzzlesValidity` / `testExpertSeedPuzzlesValidity` — any
  seed that does make it into the pool is itself valid and cleared the bar.
- `testStatePersistence` — localStorage round-trip.
- `testHintObjectsWellFormed` — item 7, every technique returns valid 3-tier text.

The calibration tests sample several generated puzzles and tolerate some
misses rather than asserting every single generated puzzle hits the bar —
because that's a bounded probabilistic search by design, not a 100%
guarantee. A test that demanded zero misses would itself be flaky and would
erode trust in the suite the same way an untested claim does; the tolerance
on each test is set from what was actually observed running it repeatedly,
not guessed. (As of the tier consolidation and solution-randomization fix
above, Medium/Hard/Expert are now all spot-checked at or near 10/10 — the
tolerances remain in place as a safety margin, not because the search is
still known to be unreliable.)

**DOM/UI-layer gaps are now covered by a separate `tests/` directory**
(Playwright, driven from outside the page — see `tests/README.md`), added
after the in-page suite's structural limit became a real problem: it runs
as JavaScript *inside* the page, so it can't inspect rendered pixels,
control real network conditions, or drive a realistic multi-click sequence.
Each script there started as a one-off verification for a specific reported
bug and was kept as a standalone regression test:
- `test_app_icon.py` — the generated app icon's grid renders without a
  broken line.
- `test_offline_playability.py` — item 1, real offline simulation.
- `test_deselect_on_outside_tap.py` — tapping outside the board/controls
  clears the current selection.
- `test_corrupted_save_recovery.py` — a corrupted (all-zero) saved game is
  discarded rather than resumed forever.
- `test_resume_no_spurious_glow.py` — resuming doesn't re-glow units
  completed in a prior session.
- `test_tap_stops_glow.py` — a tap clears in-progress glow without erasing
  the very completion that just caused it.
- `test_solution_grid_randomness.py` — the solveSudoku() fix above; several
  generated puzzles must not all share the same solution grid.
- `test_hint_trace_persistence.py` — the hint-trace fix above; a hint's
  highlight survives ordinary clicking and clears once acted on.
- `test_status_height_stable.py` — item 10's #status reflow fix; the status
  box never overflows its fixed height and the Hint button never drifts.
- `test_build_stamp_persists.py` — item 10's build-stamp fix; the "App
  updated" stamp survives every kind of status message.
- `test_auto_pencil_preserves_notes.py` — item 10's Auto-Pencil fix; a
  hand-marked cell is left alone, and filled cells refuse pencil marks.
- `test_wrong_digit_status_message.py` — item 10's wrong-digit message; a
  legal-but-wrong digit gets a plain-language explanation instead of a
  400ms flash with no context, and still never lands on the board.

Cell clicks, Guard Pencil behavior, and win detection specifically are still
only exercised indirectly (through the tests above and manual verification
during development), not by a dedicated test of their own — a real gap if
either regresses silently, though the interaction pattern needed to close it
is now established by the tests already in that directory.

Item 1 (offline play) is a special case: it's genuinely verified — with real
offline simulation, not just "should work" — but not by the in-page `?test`
suite, because that suite runs as JavaScript *inside* the page and has no
way to control the browser's actual network state. It was verified
externally (headless browser automation, forcing the network fully offline,
reloading, and confirming the page and its interactions still work) during
development instead. If the Service Worker's caching logic changes in the
future, it should be re-verified the same way, not assumed from reading the
code.

## 10. Human-factors overhaul (2026-08) — in progress

**Origin:** four expert reviews were commissioned in parallel — interaction
design/UX, accessibility, visual/aesthetic design, and learning design for
newbie players — each instructed to actually play the live app with
Playwright (click through real flows, not just read the source) and produce
a prioritized report. Findings were synthesized into "real bugs, just fix
them" vs. "bigger themes that need product direction before implementing."
The agreed order, confirmed by the user, is: bugs → reversibility/safety →
color & layout overhaul → hint curriculum rewrite → accessibility → win-state
polish last.

### Done: real bugs (fixed, each with a regression test)

1. **`#status` reflow.** Two reviewers independently found the same
   critical bug: `#status` only had a `min-height`, so a long message (hint
   tier 2 especially) grew the box and pushed every control below it down
   the page — enough that the Hint button could drift between taps and a
   third press at the same screen coordinate landed on Guard Pencil instead,
   silently disabling it. Fixed with a fixed height (112px, tuned to zero
   overflow across 320–428px widths, all 4 difficulties, all 3 hint tiers)
   plus `overflow-y: auto` as a safety net. Test: `test_status_height_stable.py`.
2. **Auto-Pencil destroyed hand-written notes.** `autoFillAllPencils()`
   used to clear and refill every empty cell unconditionally. Now a cell
   with even one existing mark is left completely untouched; only
   zero-mark cells get auto-filled. Test: `test_auto_pencil_preserves_notes.py`.
3. **Build stamp destroyed by the first status message.** The "App
   updated" stamp was a DOM child of `#status`; `setStatusText()`'s
   `textContent = text` replaces all children, so it was permanently wiped
   the moment any hint/toggle/action message appeared. Moved to its own
   sibling element, `#buildInfo`. Test: `test_build_stamp_persists.py`.
4. **Pencil marks could be drawn on top of an already-filled cell**
   (with Guard Pencil off), producing an illegible overlap, and Guard
   Pencil gave a factually wrong "conflicts with row/column/box" message
   for what was actually an already-solved cell. Both fixed by refusing
   pencil input on filled cells before any conflict check runs. Covered by
   the second half of `test_auto_pencil_preserves_notes.py`.
5. **"Select a cell first." lingered for its full timeout** even after a
   cell was subsequently selected. Now clears immediately once a cell is
   selected.
6. **Board and number bar stayed clickable during async puzzle
   generation.** Added a `.generating` state (`pointer-events: none;
   opacity: 0.55;`) applied to `#board`/`#numberBar` while
   `createNewPuzzleAsync()` is running.
7. **A legal-but-wrong digit gave no explanation**, just a 400ms red
   flash — easy to miss and gave no clue why it was rejected. Fixed with a
   plain-language status message: `"6 doesn't belong in row 3, column 5.
   Try another number."` Test: `test_wrong_digit_status_message.py`.

### Product decision: no mistake counter, no Undo button

One reviewer's synthesis had proposed either louder wrong-digit messaging
*or* a mistake counter with an Undo button for recovery. The user explicitly
rejected both the counter and the escalated messaging: **"I purposely don't
want to make a big thing of mistakes because I fumble finger so much... I
also don't see any point in letting users make mistakes because they'd have
to start the game over anyway... I definitely don't want a mistake counter
to make me concentrate on mistakes."** Since a wrong digit is never actually
written to the board (the value check happens before anything touches the
DOM), there is nothing to undo in the first place — Undo was dropped
entirely, and the fix above (item 7) is deliberately just a short,
self-clearing status line naming the digit and cell location, no counter,
no persistent penalty, no button. Do not reintroduce a mistake counter or an
Undo button for this purpose without a fresh, explicit ask.

### Done: color & layout overhaul

User request, verbatim: *"I'd like a designer to do a nice overhaul of all
colors, highlighting, and animations for us. I'd like the board to use the
maximum space it can."*

- **Board sizing.** `--cell-size` was `clamp(32px, 9.2vw, 50px)`, which
  filled only ~86-94% of the width on phones and, worse, hit its 50px cap
  past ~600px wide and simply stopped growing — a 1024px-wide window showed
  the same 464px board (45% fill) as a 600px-wide one. Retuned empirically
  (measuring actual rendered board width and horizontal overflow across
  300-1280px) to `clamp(30px, 9.8vw, 74px)`, with `.panel-row`,
  `.top-bar`, and `.controls-gameplay` widened from `max-width: 480px` to
  `700px` to match. Result: ~90-96% fill on phones, growing all the way to
  a 680px board on tablets/desktops (vs. the old fixed 464px), zero
  horizontal overflow at any tested width. Number-tile size, cell-value
  font size, and pencil-mark font size were scaled up proportionally so
  text doesn't look small relative to the now-larger cells. Test:
  `test_board_uses_available_space.py`.
- **"Highlight Fullest" amber → teal.** The amber (`#fef3c7` bg /
  `#d97706` outline) clashed with the rest of the palette and read as too
  close in meaning to the warm hint-trace/wrong-digit tones — explicit
  feedback: *"I don't think the amber highlighting looks nice with the
  other colors we use."* Replaced with a teal (`--highlight-fullest-bg:
  #ccfbf1`, `--highlight-fullest-outline: #0d9488`), keeping the same
  "pastel fill + saturated outline" visual language as hint-trace (violet,
  unchanged) and the same-number highlight (soft yellow, unchanged) — three
  clearly distinct hues, one meaning each. Test:
  `test_visual_overhaul_colors_and_motion.py`.
- **Softened the near-black grid/text colors** slightly for a less harsh
  look: `--border-strong` `#222`→`#334155`, `--border-light`
  `#c9ced6`→`#cbd5e1`, `--text-dark` `#222`→`#1e293b`, `--text-soft`
  `#6b7280`→`#64748b`. All highlight/flash colors were also pulled into
  named CSS custom properties (`--highlight-fullest-*`, `--hint-trace-*`,
  `--wrong-bg`) instead of inline hex, so the palette has one place to
  tune further.
- **`prefers-reduced-motion` support**, added globally (`*, *::before,
  *::after { animation-duration: 0.001ms !important; ... }` under the
  media query) rather than scoped to one animation, so every current and
  future transition/animation respects it automatically. Test:
  `test_visual_overhaul_colors_and_motion.py`.

This was a deliberately scoped first pass (the specific amber complaint,
genuine max-space layout, and reduced-motion), not a full re-theme (no dark
mode, no gradient/background redesign, no button-chip recoloring like
Pencil Mode's amber toggle) — further refinement can follow if requested.

**Follow-up, reported live after playing the bigger board:** the hint/status
text sat at the very top of the page, right under the title — fine when the
board was small, but once it grew to use much more of the viewport, the two
no longer fit on one phone screen together: reading a hint meant scrolling
away from the board it was about. Fixed by moving `#status` down to sit
directly above the number bar and board, and moving the Hint button down
onto the same row as the Pencil Mode toggle — so asking for a hint and
reading it both happen right next to the board, no scrolling required. Test:
`test_hint_and_board_both_visible.py`.

**Second follow-up, reported live with iOS Reduce Motion on:** unit-completion
glow appeared to have vanished, and a hint's target cell was momentarily hard
to spot. Root cause: the `prefers-reduced-motion` fix above collapsed *every*
animation's duration to 0.001ms globally — which doesn't just remove the
pulsing motion, it makes the glow complete so fast nobody can ever actually
see it, silently deleting real state feedback (a just-completed unit, a
hint's target) rather than just removing the motion. "Reduced motion" should
mean no distracting pulsing, not no acknowledgment at all. Fixed with a
specific override: under reduced motion, `.glow` gets a plain, non-animated
`box-shadow` ring instead of the pulsing one, staying visible for the same
~2s window the JS-driven `.glow` class is present. Confirmed the underlying
animation itself is still suppressed (no actual motion) — only the
visibility of the feedback changed. Test:
`test_glow_visible_under_reduced_motion.py`.

### Done (partial): hint curriculum — the giveaway-wording and default-difficulty pieces

From the learning-design review, addressed so far:

- **Default difficulty was Medium, not Easy** — a first-time visitor with
  an empty `localStorage` got dropped straight into Medium (which already
  expects Naked Pair/Triple, Pointing, and Claiming) rather than Easy.
  Fixed at the one call site that set it (`init()`); anyone with a saved
  game keeps their own last-used difficulty as before.
- **Tier 1 gave away the answer cell for the "visual scanning" techniques**
  — Full House, Naked Single, and Hidden Single/Cross-Hatching all had
  tier 1 text like `"Look at Row 3, Column 5. Try using 'Naked Single'."`
  For these three techniques specifically, *finding* the cell is the actual
  skill (unlike, say, Pointing Pair, where knowing the cells still leaves
  real deductive work to do) — so naming it in tier 1 skipped past the
  point of asking for a hint at all. Naked Single's tier 2 had the same
  problem. Rewritten so tier 1 narrows to a unit (a row/column/box, or "one
  cell in the grid" for Naked Single, then "somewhere in Box N" at tier 2)
  without naming the exact cell; the full "Row R, Column C" reveal is now
  reserved for tier 3, which was already the full-answer tier and is
  unchanged.
- **XY-Wing and XYZ-Wing's tier 3 never named the eliminated digit** —
  text like `"eliminate it from every cell that can see both of them"`
  never says what "it" is. Both now name the digit explicitly in tier 2
  and tier 3 (e.g. `"Digit 8 must end up in Row 1, Col 5 or Row 8, Col 2 —
  eliminate pencil mark 8 from every other cell that can see both of
  them."`).

Test: `test_hint_curriculum_wording.py`, which walks the real hint cascade
across generated puzzles at every difficulty (mirroring how
`testHintObjectsWellFormed` already does this for structural checks) and
confirms these four techniques' tier1/tier2 text doesn't contain a
`Row R, Column C` coordinate pair, that XY-Wing/XYZ-Wing's tier3 names
their eliminated digit, and that a fresh (no-`localStorage`) load starts on
Easy.

### Still open: hint curriculum

- **Tier 2 is often generic/textbook** rather than board-specific for the
  multi-cell techniques (Naked Pair/Triple, Pointing/Claiming, X-Wing,
  Unique Rectangle) — this pass only touched tier1/tier2 wording for the
  three single-cell techniques above and tier2/tier3 for the two wings;
  the rest of the cascade's tier2 text is unchanged.
- **No onboarding/rules explainer for a true newbie** — nothing currently
  explains what Sudoku's rules are or what Pencil Mode/Guard Pencil/hints
  even do before a first-time player is dropped onto a board.
- **No technique glossary or progress tracking** — no way to look back at
  which techniques a player has seen or learn about one before it's needed.
- **Swordfish/XYZ-Wing almost never actually fire in practice** (rarely
  generated/detected) — unchanged; a real generation/detection-rate issue,
  not a wording one.

### Done (partial): accessibility — keyboard operability and core ARIA semantics

User confirmed: *"Yes, please, for accessibility."* From the accessibility
review, addressed so far:

- **The board and number pad had zero keyboard handlers** — not operable
  at all without a mouse or touch. Board cells now use a roving tabindex
  (only the focused cell is a Tab stop, so keyboard users don't tab through
  81 stops): arrow keys move focus between cells, moving focus also selects
  the cell (matching a tap), Enter/Space selects the focused cell, and
  digits 1-9 place/pencil-mark through the exact same number-tile logic a
  mouse/touch user triggers — no separate keyboard-only code path to keep
  in sync. Number tiles are now focusable with `role="button"` and an
  `aria-label`.
- **Cells had no accessible description at all.** Each cell now has an
  `aria-label` stating its row, column, box, and state ("empty" / "given
  N" / "you entered N"), kept live-updated after every placement. The
  board itself has `role="grid"` with a label.
- **`#status` wasn't an ARIA live region** — screen reader users got none
  of the hint/status feedback. Now `role="status" aria-live="polite"`.
- **Toggle buttons (Pencil Mode, Guard Pencil) lacked `aria-pressed`** —
  now present and kept in sync with each toggle's actual state.
- **The win overlay was present in the accessibility tree from page
  load** (screen readers could reach it) despite being visually hidden via
  opacity only. Now `aria-hidden="true"` by default, flipped to `"false"`
  only in `onWin()`.
- **Missing landmark/heading structure** — the page's only heading was an
  `<h2>` with no preceding `<h1>`. Now a proper `<h1>` inside a `<main>`
  landmark.
- `prefers-reduced-motion` support was already added as part of the color
  & layout overhaul above.

Test: `test_keyboard_accessibility.py`.

**Follow-up, reported live using an attached keyboard:** arrow-navigating
onto a filled cell lit up every other cell holding the same digit (pale
yellow), and the thin 2px selection outline got lost amid that highlight —
easy to lose track of where you were. Separately, this surfaced a real gap:
only the arrow-key handler explicitly kept `selectedCell` in sync with
focus; a plain Tab landing directly on the board's one tab-stop cell left
selection out of sync entirely, relying on the browser's own inconsistent
default focus ring instead of this app's own. Fixed both: the selection
outline is now thicker (3px), pulled inward (`outline-offset`), a darker
more saturated blue, and raised above every highlight layer (`z-index: 3`);
and a single `focusin` listener on the board now syncs selection however
focus arrives, not just via arrow keys (with the cell's own default focus
ring suppressed in favor of this always-in-sync one). Test:
`test_keyboard_focus_stays_visible.py`.

**Third follow-up, reported live using an attached keyboard on iOS:** Tab
always resumed from the same place no matter which button had just been
tapped with a finger. Root cause: a long-standing iOS Safari quirk — unlike
every other browser, Safari on iOS doesn't give a tapped `<button>` or
`<select>` real keyboard focus by default (it visually reacts without
`document.activeElement` ever actually changing), so Tab afterward
continues from wherever focus last *genuinely* was, not from what was just
tapped. Fixed with one delegated `click` listener that explicitly calls
`.focus({ preventScroll: true })` on whatever
`button`/`select`/`[tabindex]` element was tapped, covering every control
(and every board cell/number tile) at once rather than button by button.
Chromium already focuses on click by default, so
`test_tap_sets_real_focus.py` can't show a before/after contrast the way
most tests here do (the bug itself is iOS-only) — it freezes the
underlying invariant (tap sets real focus) that the fix relies on instead.

Separately reported: Tab/Shift+Tab don't escape the difficulty dropdown's
native picker once it's open on iOS with an external keyboard. This is
likely a platform-level interaction between iOS's native picker overlay
and external keyboards, not something controllable from page script —
worth confirming whether it persists now that the Tab-resets-elsewhere
issue is fixed, and whether Enter/Return (to confirm the highlighted
option) works as an alternative, before concluding whether it needs a
custom (non-native) dropdown to fully control.

**Fourth follow-up, reported live using an attached keyboard on iOS:**
after leaving the difficulty dropdown, Tab jumped straight to the first
number tile, skipping New Game, Restart, Clear Pencil Marks, Highlight
Fullest, Guard Pencil, Auto-Pencil, Pencil Mode, and Hint entirely — every
plain `<button>` in the app. Root cause: a well-documented iOS Safari
default — with an external keyboard, Tab only stops at form fields (like
the `<select>`) and elements with an *explicit* `tabindex` attribute,
skipping plain buttons entirely, unless the device has Settings >
Accessibility > Keyboards > Full Keyboard Access turned on. Only the
number tiles and board cells had ever been given an explicit `tabindex`
(for the roving-focus work), so they were the only things Tab could still
land on. Fixed by adding `tabindex="0"` to all 8 plain buttons — the
documented workaround that makes a button Tab-reachable on iOS regardless
of that device setting. Test: `test_all_buttons_tab_reachable.py` (freezes
the fix directly, since Chromium's own default already Tab-stops on plain
buttons and can't reproduce the skip itself).

**Fifth follow-up, requested live:** even with every button Tab-reachable,
tabbing all the way across the control rows to reach one was still slow.
Added a plain, unmodified letter-key shortcut per button — each one's own
first letter (New Game/N, Restart/R, Clear Pencil Marks/C, Guard Pencil/G,
Auto-Pencil/A, Pencil Mode/P, Hint/H), except Highlight Fullest, which
uses "F" (from "Fullest") since Hint already owns "H". Each button's
visible label and title spell out its own shortcut (e.g. "Hint (H)") for
discoverability. Guarded two ways: modified presses (Ctrl/Cmd/Alt) are
ignored, so this never fights a real browser/OS shortcut sharing the same
letter; and the difficulty `<select>`'s own native type-ahead (jumping to
"Hard" on "h", etc.) is left alone whenever that select is focused, rather
than being double-triggered by this handler too. Test:
`test_keyboard_shortcuts.py`.

Trade-off flagged to the user rather than decided unilaterally: three of
the shortcut targets (New Game, Restart, Clear Pencil Marks) are
destructive and already have no undo/confirmation on a deliberate tap — a
single stray keypress is easier to trigger by accident than a tap on a
physically separated button. Shipped as requested (shortcuts on all 8);
revisit if accidental triggers turn out to be a real problem in practice.

**Sixth follow-up, requested live:** three more issues surfaced while
actually testing the shortcuts above.

1. *Destructive-shortcut trade-off, resolved.* Asked directly whether to
   confirm or drop the New Game/Restart/Clear Pencil Marks shortcuts; the
   answer was to confirm. Those three now show a native `confirm()` dialog
   before acting, and do nothing if it's cancelled; the other five
   shortcuts are unaffected (no dialog). Test:
   `test_destructive_shortcuts_confirm.py`.

2. *Hint left real focus stranded on the Hint button.* Reported live:
   after Tab-reaching Hint (not tapping it) and activating it, the hinted
   cell lit up purple, but that cell wasn't actually selected/focused —
   the Hint button still was, so arrow keys and digit keys did nothing.
   Two compounding causes: `showHint()` only ran `onCellClick(cell)`,
   which adds the `.selected` CSS class but never moves real
   `document.activeElement` focus; and even fixing that alone wasn't
   enough, because the iOS tap-focus workaround (see
   `test_tap_sets_real_focus.py`) re-focuses whatever was actually
   clicked/activated on *every* click, including the synthetic click a
   keyboard Enter/Space produces on a focused button — so it was quietly
   stealing focus back onto the Hint button a tick later. Fixed with a new
   `moveSelectionAndFocusTo()` helper (updates the roving tabindex, runs
   `onCellClick`, and calls `cell.focus()`) plus a shared
   `intentionalFocusTarget` flag the iOS workaround now checks so it
   defers to a click handler's own deliberate focus move instead of
   overriding it. Test: `test_hint_selects_target_cell.py` (also confirms
   an arrow key immediately after Hint actually moves selection, proving
   focus is really on the board, not just visually implied).

3. *No way back to the board once you'd tabbed off it.* Requested
   live, alongside the destructive-shortcut question: add a shortcut onto
   the board if there wasn't one. Added "B", which moves focus onto the
   currently selected cell (or the roving tab-stop cell if nothing's
   selected) from anywhere else on the page. Test:
   `test_board_shortcut.py`.

**Seventh follow-up, reported live:** "When I type a wrong digit I don't
see our error message. I do when I use the old method to enter a digit
[tapping the number tile]." Both paths run the exact same code — the
board's digit-key handler calls `numberBar.children[n-1].click()`, the
same click a tap fires — so the status message was always being set;
what was missing was focus staying put to let the player see it. The iOS
tap-focus workaround (item 2 two follow-ups up, and see
`test_tap_sets_real_focus.py`) reacts to *any* click whose target isn't
the current activeElement, including a click our own code dispatches via
`.click()` — so typing a digit silently yanked real keyboard focus off
the cell and onto the number tile div it happens to relay through, which
on a real device can scroll that tile into view and push the status text
off-screen even though it's sitting right there in the DOM. The same
mechanism affects every letter-key shortcut too (each one relays through
`document.getElementById(id).click()`), not just digit entry. Fixed by
gating the workaround on `event.isTrusted`, which is false for a click
dispatched by `element.click()` and true only for a genuine tap/mouse
click — keyboard-driven input no longer moves focus off wherever
Tab/arrow-keys legitimately left it, while real taps on iOS still get
the original fix. Test: `test_digit_key_keeps_board_focus.py`, confirmed
to fail against the pre-fix code (focus landed on the number tile after
both a wrong and a correct keyboard digit entry) and pass against the
fix; full suite (29 Playwright tests + 10 in-page tests) still green.

**Eighth follow-up, reported live:** immediately after the fix above,
"...and then nothing happens when I type the correct digit." The digit
was actually being placed correctly the whole time — but the correct-
placement code path never touched `#status` at all, so the stale
"X doesn't belong in row Y, column Z" message from the earlier wrong
attempt just sat there. With no visible change to point to, the correct
keypress read as silently ignored. Fixed by clearing the status text as
part of a successful placement, the same way `onCellClick()` already
clears one specific stale nudge ("Select a cell first.") once it goes
stale. Test: `test_correct_digit_clears_stale_status.py`, confirmed to
fail against the pre-fix code and pass against the fix; full suite (30
Playwright tests + 10 in-page tests) still green.

**Ninth follow-up, reported live:** three symptoms from one report —
"I selected a cell, turned on pencil mode, typed the digits I wanted to
erase, and they erased, but I can't tell that the cell is selected now.
I tried hitting an arrow key to another cell, and couldn't tell it
worked; it did not cause the cell I expected to be highlighted. I then
hit B (for board) and one of the cells that had been selected by the
Hint was selected." Three separate, compounding bugs, all in code paths
the last two follow-ups' fixes didn't touch:

1. `highlightSameNumbers()` calls `clearNumberHighlights()`, which
   strips `.selected` from *every* cell, including whichever one is
   still actually selected — and nothing put it back. `onCellClick()`
   happens to re-add it as its own last step, which is why selecting a
   cell always looked right, but every number-tile branch that calls
   `highlightSameNumbers()` directly (wrong digit, correct digit, pencil
   toggle) has no such last step, so the outline silently disappeared
   the moment you acted on the cell you'd just selected. Fixed by having
   `highlightSameNumbers()` restore `.selected` on `selectedCell` itself,
   right after `clearNumberHighlights()`.

2. A number tile is a real, trusted tap — unlike the digit-key/letter-
   shortcut routing fixed two follow-ups up, this one isn't filtered out
   by the `event.isTrusted` guard — so the iOS tap-focus workaround moves
   real keyboard focus onto the tile, off the board entirely, exactly
   like it does for every other button. Arrow keys require focus to
   literally be on a `.cell` to do anything, so they went dead
   immediately after using the number bar for anything, not just pencil
   marks. Fixed with a new `keepFocusOnSelectedCell()` helper — a number
   tile never changes *which* cell is selected, only acts on it, so
   every branch of its click handler now explicitly refocuses
   `selectedCell` afterward, the same way `showHint()` already refocuses
   its own target cell.

3. `onCellClick()` (what a plain click/tap runs) never updated the
   roving tabindex — only arrow-key movement and Hint's own focus helper
   did. So the one cell marked `tabindex="0"` (what "B" and a bare Tab
   fall back to whenever `selectedCell` is momentarily null) could keep
   pointing at wherever Hint last put it long after the player had
   clicked somewhere else entirely. Fixed by having `onCellClick()` keep
   the roving tabindex in sync with whatever cell was just selected,
   the same inline bookkeeping arrow-key movement already did.

Tests: `test_pencil_toggle_keeps_selection_visible.py` (covers 1 and 2)
and `test_roving_tabindex_follows_click.py` (covers 3), both confirmed
to fail against the pre-fix code and pass against the fix. Worth noting
for next time: the first version of
`test_pencil_toggle_keeps_selection_visible.py` picked an arbitrary
digit to toggle, which happened to conflict with Guard Pencil for the
chosen cell in that run — landing on the *early-return* conflict branch
instead of the actual toggle-success branch the `.selected`-stripping
bug lives in, so it missed catching bug 1 entirely despite still
"passing" (a false negative on the un-fixed code, caught by rerunning
against the pre-fix code and noticing only 2 of the expected 3 failures
showed up). Fixed by having the test explicitly pick a digit confirmed
safe via `isSafe()` before tapping it. Full suite (32 Playwright tests +
10 in-page tests) still green.

### Still open: accessibility

- **Non-text contrast** on several borders/outlines, and **pencil-mark
  text contrast** against some highlight backgrounds — not audited or
  fixed in this pass.
- **Touch targets below the 44px minimum** — the board-space overhaul
  raised cell/tile sizes substantially, but the *minimum* end of their
  `clamp()` ranges (30px) is still below 44px on the narrowest supported
  widths. Needs to be weighed against the max-space layout work rather
  than changed in isolation.
- **ARIA grid structure is simplified**: `role="gridcell"` cells sit
  directly under `role="grid"` with no intervening `role="row"` (the
  board's CSS Grid layout relies on 81 flat `.cell` children in flow
  order; wrapping them in row containers would need a bigger layout
  change). Most screen readers still announce position and state
  correctly via each cell's `aria-label`, but this isn't a fully
  spec-compliant ARIA grid.

**Win-state polish** (lowest priority, by agreed order). From the UX
review: competing simultaneous visual signals on win (confetti + banner +
board glow + leftover cell highlights all at once), inert controls with no
visible disabled state, the banner covers exit/next-action controls, and
there's no clear "what's next" call to action after winning.

No implementation work has started on any of these four remaining chunks —
this section is the full carry-forward brief for resuming later.

## 11. Hints could tell a player to place a digit the game then rejected — ✅ Fixed

**Reported live:** a Unique Rectangle hint said *"eliminate pencil marks 7
and 9 from Row 1, Column 5 — whatever extra candidate remains there must be
the real answer,"* implying the answer was 8 (the cell's third candidate).
Placing 8 was rejected as wrong.

**Root cause:** `getCandidatesGrid()` — used only by the real `showHint()`,
never by the test harness — silently substituted the player's own
hand-written pencil marks for a cell's candidates whenever that cell had
*any* marks at all, falling back to a true constraint-derived computation
only for completely unmarked cells. A player is never obligated to have
hand-marked every valid candidate in a cell — that's normal, ordinary
pencil-mark use, not a mistake. But Naked Pair/Triple, Locked Candidates,
X-Wing/Swordfish, XY-Wing/XYZ-Wing, and Unique Rectangle are only logically
sound when "this cell has exactly these N candidates" is actually *true*.
Trusting incomplete marks let the engine treat a genuinely tri-valent cell
as bivalue and confidently produce an elimination that flatly contradicted
the real solution. Full House, Naked Single, and Hidden Single aren't
affected by this specific failure mode (they don't reason from *other*
cells' candidate sets the way these do), but every technique from Naked
Pair onward was exposed to it whenever the player had any pencil marks in
play — which is most real games past the opening few moves.

This also explains why the in-page `?test` suite never caught it: it always
calls the finder functions directly with `getCandidatesGridPure()` (the
correct, DOM-independent computation), so it never exercised the
DOM-marks-substitution path that only the real `showHint()` used.

**Fix:** `showHint()` now calls `getCandidatesGridPure()` — the same
function the test harness already trusted — instead of `getCandidatesGrid()`.
The old function (which had exactly one caller) was deleted entirely rather
than left as dead, reintroducible code.

**Verification:** confirmed directly rather than inferred — reconstructed
the reported board from a screenshot and ran it through an independent
backtracking solver, which showed the four Unique-Rectangle corner cells
really did form a genuine "deadly pair" ambiguity (two grids differing only
by swapping 7↔9 in the rectangle) alongside the one genuinely safe
completion, proving the *technique's logic* was sound and the bug had to
be in what fed it. Then reproduced the actual mechanism live: rigged an
empty cell's pencil marks to something clearly wrong (every digit marked
at once) and
confirmed `showHint()` ignored it and still reasoned correctly, whereas the
pre-fix code read the marks. Test: `test_hints_ignore_pencil_marks.py`,
confirmed to fail against the pre-fix code (both by detecting the deleted
function's continued existence and by proving `showHint()` never called
`getCandidatesGridPure()`) and pass against the fix. Full suite: 10/10
in-page tests, 16/16 Playwright tests.

**Follow-up, reported live — a different, non-conflicting problem:** a
player correctly applied a Pointing Pair hint's tier-3 instruction by
erasing the named pencil marks by hand, asked for another hint, and got
the *exact same* Pointing Pair hint again. Worth being explicit that this
is not the correctness bug above resurfacing — it's a separate gap that
only exists *because* the fix above is correct: elimination-only hints
(Naked Pair/Triple, Pointing/Claiming, X-Wing/Swordfish, the wings, Unique
Rectangle) don't themselves change the grid, and since hints deliberately
never read pencil marks, updating your own notes by hand doesn't register
as progress — asking for another hint recomputes the exact same
candidates from the exact same placed digits and finds the exact same
hint, forever. The fix for *this* has to stay entirely separate from
candidate correctness, which is why it's a different mechanism: a `Set`
of hints (by their primary cell) that have already had all 3 tiers shown
on the current grid state. The next `showHint()` call skips any technique
that resolves to an already-seen cell, falling back to repeating it only
if every fireable technique has already been fully shown. Cleared
whenever the grid actually changes (a real placement, or a new puzzle) —
never by anything that leaves placed digits untouched. Test:
`test_hint_progresses_past_seen_hints.py`, confirmed to fail against the
pre-fix code (the same cell repeated even with 5 distinct techniques
available) and pass against the fix.

Known limitation: this skips by *technique function*, not by individual
instance — if the same technique (say, Naked Single) has several
different valid cells available at once, cycling through the first one
moves on to a *different technique* next, not to the second Naked Single
instance the same finder function would otherwise have found. Doing that
would mean threading an "avoid these cells" set through every one of the
~12 finder functions individually — a much larger change than this fix,
and not what the live report actually needed (a different technique was
available in that case). Worth revisiting if a puzzle state ever
surfaces where this narrower limitation is the one actually in the way.

**Accepted limitation, reported live:** pressing Hint again on the *same*
cell still just advances tier 1→2→3 (see the `currentHintLevel` cycling
above), even when the player has already mentally acted on tier 1 or 2's
information in a way the engine has no way to detect (e.g. reasoning
through it in their head, or writing marks the engine — deliberately,
per the correctness fix above — doesn't read). There's no reliable signal
to tell "already addressed, give me something new" apart from "still
stuck, show me more of this one," short of re-opening the same
detect-what-the-player-really-meant problem that's already been revisited
several times in this section. Flagged directly to the user rather than
attempted: given how many previous fixes here have each solved one report
only to surface the next adjacent one, the user chose to accept current
behavior over risking another round of that cycle. Not fixed; left here
so a future session doesn't have to relitigate the same tradeoff from
scratch.

**Follow-up, reported live — this was more than cosmetic:** "This
'acceptable limitation' means that I can't finish this puzzle without
making a wild guess." Investigating properly (rather than repeating the
same accepted-limitation framing) found a real, fixable bug underneath
the cosmetic tier-cycling annoyance above, not just an extension of it.

The puzzle generator's own solver, `rateSolveWithTierCascade()` (used to
verify a puzzle is solvable by pure logic before it's ever shown to a
player), and separately the in-page test suite's
`testHintObjectsWellFormed`, both prove solvability by *chaining*
techniques: applying each one's `eliminate` list into a working
candidate grid, then re-running the cascade so the next technique in the
chain becomes visible. `showHint()` never did this — every call
recomputed `getCandidatesGridPure()` from placed digits only, with no
memory of eliminations already fully shown. So whenever the *next*
logical step genuinely depended on an earlier elimination being applied
first, Hint could never reach it: the same already-fully-shown
elimination-only hint would keep winning the cascade forever, since
nothing it looks at ever changes on its own. That's a real dead end, not
mere repetition — exactly what stranded the player.

Fixed with `confirmedCandGrid`: a working candidate grid that persists
across Hint presses (reset only when the real grid changes — a
placement or a new puzzle, the same two reset points as `seenHintKeys`)
and has each hint's own `eliminate` list folded into it once that hint
reaches tier 3, mirroring exactly what the two already-trusted solvers
above already do. `showHint()` now seeds this grid from
`getCandidatesGridPure()` only when it's empty, and reuses/narrows it
otherwise. This doesn't touch the narrower cosmetic annoyance in the
"Accepted limitation" note above (tier 1→2→3 cycling on a hint the
player has already mentally handled, when there's genuinely no other
technique available yet) — that's still an accepted, unfixed tradeoff.
What's fixed is the case where a *different* technique actually becomes
available and the engine simply wasn't looking for it correctly.

Test: `test_hint_chains_eliminations.py` — advances a generated puzzle
via placements only (recomputing candidates fresh each round, exactly
like `showHint()` does) until reaching a state where the first fireable
technique is elimination-only, is the *only* thing fireable on the raw
candidates, and its own elimination unlocks a different technique that
doesn't fire otherwise; then drives the real `showHint()` through that
hint's 3 tiers without ever placing a digit and confirms the next press
moves to the unlocked technique. Confirmed to fail against the pre-fix
code (repeats the same hint forever, exactly as reported) and pass
against the fix. Worth noting for next time: an earlier version of this
test searched for the dependency using an *accumulated* candidate grid
built by walking the solve forward with eliminations applied at every
step — which found "dependencies" that don't actually exist from a cold
start, since `showHint()` (both before and after this fix, on its very
first call for a given grid) always begins from a fresh
`getCandidatesGridPure()` with no accumulated history. That version
passed even against the pre-fix code, for an unrelated reason (an
entirely separate technique happened to already be independently
fireable on the true raw candidates). Fixed by only ever advancing the
simulated grid through placements, and identifying the dependency fresh
at each round — matching what the real engine can actually see — and by
requiring the target hint to be the *only* thing fireable on that raw
grid, ruling out the same false-pass mode. Full suite (33 Playwright
tests + 10 in-page tests) still green, including
`test_eliminations_never_contradict_solution.py`'s 60-puzzle audit and
the in-page `testHintObjectsWellFormed`.

## 12. Some "Hard" puzzles weren't actually uniquely solvable — ✅ Fixed

**Reported live, following up on item 11:** the exact same "place 8, get
rejected" scenario reappeared even after item 11 shipped. Worth noting how
this was surfaced at all — GitHub Pages serves both the live site and a
PR's preview build from the same origin (`sharpkathy123.github.io`, just
different paths), and `localStorage` is scoped per-origin, not per-path, so
both share the same saved game. The puzzle being resumed predated item
11's fix; item 11 only changes how *new* hints reason about candidates, not
a puzzle/solution pair already sitting in `localStorage` from before the
fix existed — so reproducing the old bug on an old save didn't mean the
fix failed, but it did mean the underlying puzzle needed direct
investigation rather than assuming it was the same root cause again.

**Root cause, found by auditing broadly instead of re-checking the one
report:** wrote a check that generates many fresh puzzles and confirms no
hint's elimination ever removes a cell's *actual* solution digit — a
stronger, technique-agnostic version of item 11's check. Run across 60
fresh puzzles, it failed 11 times, always on Hard difficulty, always
"Unique Rectangle." Diagnosed one failing case in full: four cells with
candidates `{1,6}, {1,6}, {1,3,5,6}, {1,6}` — a textbook Unique Rectangle
shape, correctly detected — but the recorded solution had `6` at the
"extra" cell, exactly one of the two digits Unique Rectangle said to
eliminate. Re-solving that same puzzle's original givens with a larger
search budget than the generator itself used turned up **at least 5**
solutions, not the 1 the generator's own uniqueness check had certified.

The generator's `countSolutions()` (used everywhere a candidate puzzle's
uniqueness gets verified) had a hard-coded `MAX_ITERATIONS = 5000` cap, and
scanned for the first empty cell in row-major order at every step rather
than the most-constrained one. A genuinely Hard puzzle — few forced cells,
which is exactly what makes it Hard — has a much larger, flatter search
tree under that naive ordering, and could exhaust the iteration cap having
only explored one branch, silently reporting "1 solution" (unique) for a
puzzle that actually had several. That false "unique" then broke every
technique whose correctness depends on real uniqueness — Unique Rectangle
chief among them, since eliminating a digit specifically because keeping
it would allow a second solution is meaningless once a second solution
already exists via a different cell entirely. This was never a hint-engine
bug; item 11's fix was real and necessary, but insufficient for puzzles
that were broken before any hint ran.

**Fix:** `countSolutions()` now branches on the empty cell with the fewest
remaining candidates first (the standard "most constrained variable"
heuristic) instead of scanning in row-major order — this is a well-known,
large reduction in search-tree size for Sudoku specifically, not a niche
optimization. It also now distinguishes "confirmed count" from "iteration
budget ran out before a definitive answer" (returning `-1` for the latter,
which every caller's `=== 1` / `!== 1` check already treats as "not
verified unique" and rejects) rather than ever returning a possibly-wrong
partial count as if it were final.

**Verification:** re-ran the 60-puzzle elimination audit three consecutive
times post-fix — zero contradictions every time (was 11 failures on one
run pre-fix). As a side effect of branching more intelligently rather than
brute-force scanning, Hard-tier generation also got dramatically faster in
the process (spot-checked at consistently under 1 second; a previous
session had documented it at ~19 seconds after an unrelated randomization
fix). Full suite: 10/10 in-page tests (which also run measurably faster
now), 19/19 Playwright tests, including the new
`test_eliminations_never_contradict_solution.py`.
