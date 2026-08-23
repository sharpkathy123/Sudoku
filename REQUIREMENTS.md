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

All techniques live in one ordered list, `HINT_CASCADE` — used both to drive
live hints (`showHint()`) and to rate puzzles (`rateSolveWithTierCascade()`),
so the two can never disagree about what a puzzle needs. Order within a tier
is easiest-to-spot first.

| Tier | Techniques | Rank |
|---|---|---|
| Easy | Full House, Hidden Single / Cross-Hatching (box, row, *and* column), Naked Single | 1 |
| Medium | Naked Pair, Pointing Pair/Triple, Claiming Pair/Triple (Box-Line Reduction), Naked Triple | 2 |
| Hard | X-Wing | 3 |
| Expert | XY-Wing, XYZ-Wing, Unique Rectangle (Type 1), Swordfish | 4 |
| Master | Fallback direct-reveal (nothing above solves it) | 5 |

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
  rows/columns to 3) so Expert would have a technique of its own instead of
  sharing X-Wing with Hard.

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

**A puzzle that overshoots its tier can't come back by digging further** —
removing givens only ever makes a puzzle harder or leaves it the same, never
easier. So while extending a dig toward the floor, the moment
`evaluateDifficultyBar` reports `overshoot: true` (the puzzle is already
unsolvable using techniques up to the tier's own ceiling), that trajectory is
abandoned immediately in favor of a fresh attempt, rather than continuing to
dig toward the floor for a result that can only get further away.

**Status by tier:**
- Easy: ✅ — converges on the first or second dig almost every time.
- Medium: ✅ — converges reliably within its budget (60 attempts); needed a
  higher budget than Easy once Hidden Single started covering rows/columns
  too, since that alone resolves more puzzles that used to need a medium
  technique.
- Hard: ⚠️ — genuinely the hardest tier to calibrate, and got harder once
  Medium's technique roster grew (Naked Triple, Claiming, pair-in-any-unit):
  there's simply less left in between for Hard (X-Wing alone) to be the sole
  missing piece for. Empirically converges only around half the time even at
  a 450-attempt budget; the rest fall back to the closest candidate found.
- Expert: ⚠️ — same idea; a genuine Expert-tier requirement (XY-Wing/XYZ-Wing/
  Unique Rectangle/Swordfish, and nothing harder) is uncommon, but the tier
  now has four techniques' worth of ways to qualify instead of one
  (Swordfish alone previously), which noticeably improved its hit rate.
- Master: ⚠️ — same mechanism, requiring the *opposite* condition (not
  solvable through Expert techniques).

**Performance tradeoff:** Hard and Expert's attempt budgets (450 and 400)
can take several seconds in the worst case — observed up to roughly 10–15
seconds for Hard, 5–10 for Expert. `createNewPuzzleAsync` yields to the
browser every 5 attempts (`await new Promise(resolve => setTimeout(resolve,
0))`) so a long search doesn't freeze the UI the way puzzle generation
previously could, but a multi-second wait for "New Game" at these tiers is
the honest worst case, not hidden. A puzzle that falls back to the closest
non-qualifying candidate is still a perfectly valid, appropriately-sparse
puzzle at that difficulty's given-count — just not provably needing that
exact tier's signature technique.

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

## 8. Human-like hint ordering — ✅ Met

**Requirement:** hints should come in the order a person would actually try
them, prefer techniques that don't need pencil marks until they're actually
needed, and respect whatever pencil marks the player has already entered.

- `HINT_CASCADE` is one ordered list, easiest first: Full House → Hidden
  Single → Naked Single (no candidate-tracking needed at all) → Naked Pair →
  Pointing → Claiming → Naked Triple (medium) → X-Wing (hard) → XY-Wing →
  XYZ-Wing → Unique Rectangle → Swordfish (expert) → fallback reveal
  (master). Both `showHint()` (live hints) and `rateSolveWithTierCascade()`
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
  across Hard/Expert/Master puzzles had a column-oriented X-Wing available
  that the row-only search would never find at all — meaning some puzzles
  got shown a harder technique than actually necessary, or were mis-rated
  as needing more than Hard when a column X-Wing would have sufficed.
  Fixed by generalizing both into one axis-parameterized search
  (`findFishAlongAxis`) tried in both directions. Re-verified against the
  same sample: 0 missed column patterns after the fix (was 317 of 2557
  checked steps). As a side effect, Hard's calibration hit rate also
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
- `testHintObjectsWellFormed` — item 7, every technique returns valid 3-tier text.

The four calibration tests (medium/hard/expert/master) sample several
generated puzzles and tolerate some misses rather than asserting every
single generated puzzle hits the bar — because, as above, that's a bounded
probabilistic search by design, not a 100% guarantee, and (as of this
technique expansion) Hard in particular converges only around half the
time. A test that demanded zero misses would itself be flaky and would
erode trust in the suite the same way an untested claim does; the tolerance
on each test is set from what was actually observed running it repeatedly,
not guessed.

**Still not covered** (real gaps, not addressed by this pass): anything in
the DOM/UI layer — cell clicks, Guard Pencil behavior, win detection. Those
would need lightweight interaction tests, not just solver-engine tests, to
be caught the same way.

Item 1 (offline play) is a special case: it's genuinely verified — with real
offline simulation, not just "should work" — but not by the in-page `?test`
suite, because that suite runs as JavaScript *inside* the page and has no
way to control the browser's actual network state. It was verified
externally (headless browser automation, forcing the network fully offline,
reloading, and confirming the page and its interactions still work) during
development instead. If the Service Worker's caching logic changes in the
future, it should be re-verified the same way, not assumed from reading the
code.
