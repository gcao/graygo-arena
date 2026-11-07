# Plan 01-02 Summary: Rule Resolution

**Completed:** 2026-04-25
**Requirements:** ENG-03, ENG-04, ENG-05, ENG-06, ENG-07
**Status:** Complete

## Delivered

- Added toroidal neighbor, group, and liberty helpers.
- Implemented simultaneous `graygo-v1` turn resolution from one immutable pre-turn board.
- Implemented same-point collision-to-gray behavior, adjacent placements, capture removal, forbidden updates, double-pass completion, and deterministic stone-count scoring.
- Added focused tests for wrapping, groups/liberties, collisions, input immutability, occupied-move rejection, captures, forbidden points, pass handling, and scoring.

## Locked Semantics

- Corrected on 2026-11-06: capture groups containing no new stone first, recompute liberties, then remove all remaining zero-liberty groups simultaneously as suicides.
- Corrected on 2026-11-07: ordinary captures do not forbid their coordinates. Restrictions come from accumulated no-change placements and matching one of the last two pre-round boards. Matching history forbids each player's own recorded move, never PASS, without reverting the round.
- Gray collision bridges inherit liberties from their entire connected group, including across toroidal seams. A captured stone at the connecting point does not itself forbid a subsequent collision there.
- Full post-round restriction sets and two-round history now round-trip in resolution JSON; older turn records remain readable. Existing active-game restrictions can be repaired from public history without replaying or rewriting their boards.
- The initial implementation finished after one `PASS`/`PASS` round. Corrected on 2026-11-06 to require two consecutive `PASS`/`PASS` rounds; any placement resets `double_pass_count`.
- Corrected on 2026-11-06: final scoring uses Chinese area counting with all remaining stones alive, toroidal empty regions, and gray's stone/territory share split between both players. Finished responses, events, exports, and the UI expose the result. This replaces the initial black/white stone-count estimate.

## Verification

- `cd backend && uv run pytest tests/engine/test_toroidal_liberties.py tests/engine/test_resolution.py tests/engine/test_scoring.py` passed.
- `cd backend && uv run ruff check .` passed.
- `cd backend && uv run pyright` passed.
