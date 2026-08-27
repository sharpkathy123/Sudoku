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
