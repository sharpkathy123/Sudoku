# Requirements

This is the durable source of truth for what this Sudoku app is supposed to
do, separate from `README.md` (which is user-facing feature copy and, as of
this writing, overstates a couple of things — noted inline below). Each item
below has a verification status. Where a requirement is enforced by an
automated test, the test name is given so a future change that breaks the
requirement gets caught, not just described.

Status legend: ✅ Met and verified · ⚠️ Met most of the time (bounded,
probabilistic) · ❌ Not currently met.

## 1. Offline play ("Airplane Mode") — ❌ Not currently met

**Requirement:** the game must be playable with no network connection,
including on a mobile device in Airplane Mode after being loaded once.

**Status:** not met. An earlier version registered a Service Worker from a
`data:` URL for "single-file" offline caching; browsers refuse to register a
Service Worker from anything other than an `http(s)` URL, so that
registration always failed silently and no offline caching ever actually
happened. It's been removed rather than left in place pretending to work.

`README.md` currently claims *"🌐 100% Offline Support: Embedded Service
Worker automatically caches the app locally... (even in Airplane Mode)"* —
that claim is false today and should be corrected or the feature rebuilt.

**What it would take to actually fix this:** a Service Worker script served
from a real `http(s)` URL — i.e. a second file (`sw.js`) alongside
`index.html`, registered with a relative path. That's a small deviation from
"everything in one HTML file," which is a call for whoever owns that
tradeoff, not something to do silently. Once such a file exists, the
manifest and PWA meta tags already in `index.html` need no changes.

## 2–6. Difficulty calibration — ✅ / ⚠️ (see per-tier notes)

**Requirement:**
- Easy: solvable using only easy-tier hints.
- Medium: needs at least one medium-tier hint; solvable at medium-or-easier.
- Hard: needs at least one hard-tier hint; solvable at hard-or-easier.
- Expert: needs at least one expert-tier hint; solvable at expert-or-easier.
- Master: needs at least one fallback (direct-reveal) hint.

Before this was implemented, the generator only checked that a puzzle had a
**unique solution** — given-count (38/32/27) was the only thing standing in
for difficulty, with no check that a puzzle generated for "Hard" actually
*needed* a hard technique, or that an "Easy" puzzle didn't secretly need one.
Testing this for real turned out to require an actual difficulty rater, not
just a test file — see the Testing section below for what that took.

### Tier → technique mapping

| Tier | Techniques | Rank |
|---|---|---|
| Easy | Full House, Hidden Single / Cross-Hatching, Naked Single | 1 |
| Medium | Locked Candidates (Pointing Pair/Triple), Naked Pair | 2 |
| Hard | X-Wing | 3 |
| Expert | Swordfish | 4 |
| Master | Fallback direct-reveal (nothing above solves it) | 5 |

**Swordfish is new** — it didn't exist before this work. Without it, Expert
had no technique of its own; it and Hard would have been rated identically
(nothing beyond X-Wing existed), which made item 5 impossible to satisfy
honestly. It's `findSwordfish()`, the same pattern as X-Wing generalized
from 2 rows/columns to 3, and it slots into the hint cascade between X-Wing
and the fallback reveal.

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
(`CALIBRATION_ATTEMPTS_BY_DIFFICULTY` — Easy/Medium hit the bar almost
immediately; Hard needs more tries; Expert needs the most, since a genuine
Swordfish requirement is rare even at very few givens). If the whole budget
is exhausted, it serves the closest candidate found rather than searching
forever or freezing the "New Game" button, and logs a `console.warn` so this
is visible rather than silent.

**Status by tier:**
- Easy, Medium: ✅ — converge on the first or second dig almost every time.
- Hard: ⚠️ — usually converges within its budget; rarely (observed roughly
  1 in 10–15 generations in testing) falls back to a non-qualifying puzzle.
- Expert: ⚠️ — same idea, larger budget, still occasionally falls back;
  generation can take several seconds in the worst case (see below).
- Master: ⚠️ — same mechanism, requiring the *opposite* condition (not
  solvable through Expert techniques).

**Performance tradeoff:** hitting Expert/Master's bar reliably needs a large
attempt budget (up to 400 tries), which can take several seconds in the
worst case. `createNewPuzzleAsync` now yields to the browser every 5
attempts (`await new Promise(resolve => setTimeout(resolve, 0))`) so a long
search doesn't freeze the UI the way puzzle generation previously could —
but a multi-second wait for "New Game" at Expert is still the honest
worst case, not hidden.

**The three hardcoded seed puzzles are currently unused.** `EXPERT_SEED_PUZZLES`
and `MASTER_SEED_PUZZLES` are filtered through this same bar at load time
(so a seed can't sneak in without meeting it), and as of writing none of the
three hand-picked puzzles actually require a Swordfish or resist every
technique through Swordfish — they were evidently chosen by feel (few
givens) rather than verified technique requirements. Both pools end up
empty, and the generic calibrated digging loop is what actually delivers
Expert and Master puzzles today. The seed machinery is left in place —
if better-chosen seeds are added later, they'll be used automatically
provided they clear `meetsDifficultyBar`.

## 7. Three-tier hint wording — ✅ Met

**Requirement:** first press points at a cell and names the technique;
second press gives more help without revealing the number; third press
gives the exact, actionable detail.

This already matches the existing `tier1`/`tier2`/`tier3` text on every hint
technique — `tier1` always names the technique and cell/unit, `tier2` never
mentions the actual digit, `tier3` is fully actionable. For placement
techniques (Full House, singles) tier 3 says exactly which number to enter.
For elimination-only techniques (Locked Candidates, Naked Pair, X-Wing,
Swordfish) tier 3 says exactly which pencil marks to erase and from where —
there usually isn't a number to *enter* yet, since the technique's job is
narrowing candidates, not placing a digit. That's the intended behavior, not
a gap.

## 8. Human-like hint ordering — ✅ Met

**Requirement:** hints should come in the order a person would actually try
them, prefer techniques that don't need pencil marks until they're actually
needed, and respect whatever pencil marks the player has already entered.

- The cascade (`showHint()`) already tries Full House → Hidden Single →
  Naked Single before anything that depends on candidates being tracked at
  all, then only reaches Locked Candidates → Naked Pair → X-Wing → Swordfish
  → fallback once the board has no more plain singles.
- `getCandidatesGrid()` uses the player's own active pencil marks as the
  candidate set for a cell once they've entered *any* mark there, and falls
  back to full rule-based candidates (`isSafe`) otherwise. This means a hint
  reflects what the player has actually narrowed down, not a fresh
  from-scratch computation.
- **Known intentional edge case:** if a player's pencil marks for a cell are
  incomplete or wrong, the hint engine trusts them as the candidate universe
  for that cell anyway (garbage in, garbage out) — this matches how a real
  hint/checker built on your own notes should behave, rather than silently
  overriding what you wrote.

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
  "hint strategy" was the same for Easy and Master alike. It's been replaced
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
- `testMasterPuzzleCalibration` — item 6.
- `testExpertSeedPuzzlesValidity` / `testMasterSeedPuzzlesValidity` — any
  seed that does make it into the pool is itself valid and cleared the bar.
- `testStatePersistence` — localStorage round-trip.

The four calibration tests (medium/hard/expert/master) sample several
generated puzzles and tolerate at most one miss, rather than asserting every
single generated puzzle hits the bar — because, as above, that's a bounded
probabilistic search by design, not a 100% guarantee. A test that demanded
zero misses would itself be flaky and would erode trust in the suite the
same way an untested claim does.

**Still not covered** (real gaps, not addressed by this pass): anything in
the DOM/UI layer — cell clicks, Guard Pencil behavior, win detection — and
the PWA/offline plumbing (item 1). Those would need lightweight interaction
tests, not just solver-engine tests, to be caught the same way.
