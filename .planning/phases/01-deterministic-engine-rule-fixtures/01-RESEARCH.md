# Phase 1 Research: Deterministic Engine & Rule Fixtures

**Phase:** 01 - Deterministic Engine & Rule Fixtures
**Researched:** 2026-04-25
**Status:** Ready for planning
**Method:** Local project artifact review only. No app connectors or MCP app tools used.

## Research Goal

Plan Phase 1 well enough that execution can build a pure deterministic Gray Go engine without drifting into orchestration, API, persistence, UI, prompts, or provider adapters.

Phase 1 must satisfy requirements ENG-01 through ENG-08:

- Board representation, coordinates, symbols, BoardKey serialization, and turn metadata.
- Legal move validation for each color, including PASS.
- Simultaneous Black/White move resolution from one pre-turn board.
- Collision-to-gray behavior.
- Toroidal neighbor, group, and liberty logic.
- Two-stage capture and forbidden-point updates.
- Double-pass and scoring or score-estimate behavior.
- Automated coverage for every rule mechanic.

## Source Findings

### Locked Decisions From Context

- Engine is the only authority for board state, legal moves, captures, forbidden points, pass state, scoring, and BoardKeys.
- Phase 1 is pure deterministic engine plus fixtures only.
- `graygo-v1` is the only ruleset in scope.
- Board cells use `+`, `B`, `W`, and `G`.
- Coordinates use lowercase row letters plus 1-based columns, such as `d4`; pass is `PASS`.
- BoardKey is a human-readable slash-separated row string, for example `+++++++/+++++++/+++++++/+++++++/+++++++/+++++++/+++++++`.
- Ambiguous rules must become named fixtures/spec cases before implementation proceeds.

### Architecture Findings

The project research recommends a modular backend where the engine is isolated from all IO. For Phase 1, that means:

- No FastAPI imports.
- No Pydantic dependency inside core rule code.
- No SQLAlchemy or persistence models.
- No provider SDKs or prompt code.
- No UI DTOs.

The planner should keep the first backend module small and importable in tests. A good initial layout is:

```text
backend/
  pyproject.toml
  src/
    graygo_arena/
      __init__.py
      engine/
        __init__.py
        board.py
        coordinates.py
        moves.py
        rules.py
        resolution.py
        scoring.py
        fixtures.py
  tests/
    fixtures/
      engine_cases.json
    engine/
      test_board_key.py
      test_coordinates.py
      test_legal_moves.py
      test_toroidal_liberties.py
      test_resolution.py
      test_scoring.py
```

If the executor prefers a flatter layout during the first slice, that is acceptable as long as the engine remains IO-free and tests can import it directly.

## Recommended Data Model

### Core Types

The planner should specify small value types, likely with frozen dataclasses and enums:

```python
SeatColor = Literal["black", "white"]
Cell = Literal["+", "B", "W", "G"]
Move = Coordinate | PassMove
```

Recommended objects:

- `Coordinate(row: int, col: int)` with zero-based internal indexes.
- `Move` with either `kind="place"` and `coordinate`, or `kind="pass"`.
- `Board(size: int, cells: tuple[tuple[Cell, ...], ...])`.
- `ForbiddenState(black: frozenset[Coordinate], white: frozenset[Coordinate])`.
- `GameState(board, forbidden, double_pass_count, turn_index, ruleset="graygo-v1")`.
- `PlacementEvent`, `CaptureEvent`, `ForbiddenUpdate`, and `TurnResolution`.

Keep internal indexes zero-based for algorithms, but parse/render coordinates as row letters and 1-based columns at the boundary.

### BoardKey Contract

BoardKey should be a canonical string:

```text
row0/row1/row2/.../rowN
```

Each row has exactly `size` symbols from `+BWG`. Validation should reject:

- Wrong row count.
- Wrong row length.
- Unsupported symbols.
- Empty rows.
- Leading/trailing slash anomalies.

Round-trip invariant:

```text
Board.from_key(board.to_key()).to_key() == board.to_key()
```

## Rule Planning Notes

### Legal Move Validation

A legal move is either:

- `PASS`.
- A coordinate inside the board that is empty on the current resolved board and not forbidden for that color.

The planner should include tests for:

- Empty board legal moves include all cells plus PASS.
- Occupied black, white, and gray cells are illegal.
- Color-specific forbidden points are illegal only for the matching color.
- Coordinates outside board size are rejected.
- PASS remains syntactically legal.

### Toroidal Neighbors

Neighbors wrap in four orthogonal directions:

```text
up:    (row - 1) % size
down:  (row + 1) % size
left:  (col - 1) % size
right: (col + 1) % size
```

Key invariants:

- Every coordinate has exactly four orthogonal neighbors.
- For size greater than 2, neighbors are unique.
- Neighbor relation is symmetric.
- Corners and edges wrap.

For very small board sizes, duplicate neighbors can occur if not normalized. The planner should decide whether Phase 1 supports only practical sizes such as 3+ or validates all sizes explicitly. The design uses 7x7 default. If uncertain, plan a guard such as `board_size >= 3`.

### Groups and Liberties

Group detection should use toroidal neighbors and same-color cells. Gray stones should be their own cell type, not treated as black or white.

Fixture targets:

- Single stone on empty toroidal board has four liberties on 3x3+ boards.
- Edge/corner stones see wrapped neighbors.
- Connected groups through wrapped edges are one group.
- Gray cells block occupation but are not counted as same-color liberties.

### Simultaneous Resolution

Phase 1 should expose an engine function equivalent to:

```python
resolve_turn(state: GameState, black_move: Move, white_move: Move) -> TurnResolution
```

Resolution must use one immutable pre-turn snapshot. It should never mutate the input state in place.

Recommended high-level order:

1. Validate both moves independently against the pre-turn state.
2. Handle passes and placements.
3. If both seats place on the same coordinate, create a gray collision at that coordinate.
4. Otherwise place Black and White stones simultaneously.
5. Apply the Gray Go capture/forbidden rules.
6. Update double-pass count and terminal/scoring state.
7. Return pre-board key, post-board key, moves, placement events, captures, forbidden updates, pass/end state, and score/score estimate.

### Collision-to-Gray

Fixtures should include:

- Black and White both choose the same empty coordinate -> post-board has `G`.
- Same-point collision does not create a black or white stone first.
- Same-point collision is auditable as a placement event.
- Same-point collision on occupied/forbidden coordinate is invalid before resolution.

### Two-Stage Captures and Forbidden Points

The design document names two-stage captures and forbidden points but does not fully define every edge case. The planner should include an early spec/fixture task that locks:

- Which stones or groups can be captured after simultaneous placement.
- Whether gray collision points can be captured.
- How forbidden points are derived from captures.
- Whether forbidden points are color-specific, turn-scoped, or persistent.
- How simultaneous captures interact with forbidden updates.

Do not let the executor guess these details silently. The plan should require named fixtures that encode the chosen behavior before implementation.

### Pass and Scoring

The design references `double_pass_count` and scoring. The planner should include:

- PASS/PASS increments double-pass count and can end the game when threshold is reached.
- One pass plus one placement resets or updates pass state according to the chosen rule fixture.
- Scoring is deterministic from final board.
- If exact Gray Go scoring is underdefined, Phase 1 may implement a documented score estimate with fixtures and leave richer scoring changes as explicit follow-up only if roadmap scope allows.

## Testing Strategy

Use pytest for example-based tests and Hypothesis for invariants.

Recommended commands:

```bash
cd backend
uv run pytest
uv run ruff check .
uv run pyright
```

If the backend scaffold is created in Phase 1, also include:

```bash
uv run ruff format --check .
```

### Golden Fixture Format

A JSON fixture file is sufficient and easy to audit:

```json
{
  "name": "same_point_collision_becomes_gray",
  "size": 7,
  "pre_board_key": "+++++++/+++++++/+++++++/+++++++/+++++++/+++++++/+++++++",
  "forbidden": {"black": [], "white": []},
  "double_pass_count": 0,
  "black_move": "d4",
  "white_move": "d4",
  "post_board_key": "+++++++/+++++++/+++++++/+++G+++/+++++++/+++++++/+++++++",
  "events": [{"type": "collision", "coordinate": "d4"}]
}
```

The planner should require at least these fixture classes:

- BoardKey round trip.
- Coordinate parsing and rendering.
- Legal move validation.
- Occupied and forbidden move rejection.
- Toroidal neighbor wrapping.
- Wrapped group/liberty detection.
- Same-point collision.
- Adjacent simultaneous placements.
- Capture scenario.
- Forbidden update scenario.
- PASS/PASS terminal scenario.
- Deterministic replay of a short scripted game.

### Property Tests

Good property-test candidates:

- BoardKey round trip for generated boards.
- Coordinate parse/render round trip for valid board sizes.
- Neighbor symmetry: if B is neighbor of A, A is neighbor of B.
- Resolution determinism: same state and moves produce identical resolution.
- Input immutability: resolving a turn does not mutate the pre-turn state.

## Planning Implications

The roadmap has three plan stubs. Keep that split:

1. **Board model, coordinates, symbols, BoardKey, turn metadata, and legal move validation**
   - Establish package scaffolding, type choices, board parsing/rendering, coordinate parsing, BoardKey validation, move validation, and initial tests.

2. **Simultaneous resolution, collision-to-gray, toroidal liberties, captures, forbidden points, pass state, and scoring**
   - Build rule algorithms and resolution output using fixtures from plan 1 plus newly added capture/pass fixtures.

3. **Golden fixtures, property checks, and regression coverage for engine rules**
   - Consolidate fixture runner, add property tests, add deterministic replay coverage, and run static/lint/test verification.

The planner may choose waves:

- Plan 01-01 must be wave 1.
- Plan 01-02 depends on 01-01.
- Plan 01-03 depends on 01-01 and 01-02.

Parallel execution is not appropriate within Phase 1 because the rule engine is a tight dependency chain.

## Risk Register

| Risk | Planning Response |
|------|-------------------|
| Gray Go details are underdefined | Add a fixture/spec-lock task before implementation of captures, forbidden points, pass, and scoring. |
| Ordinary Go assumptions leak in | Require toroidal edge/corner fixtures and wrapped group tests. |
| Engine couples to backend framework | Make pure engine import checks and no FastAPI/Pydantic/SQLAlchemy imports part of acceptance criteria. |
| Model output becomes authority later | Name engine return fields clearly and keep model/provider concepts out of Phase 1. |
| BoardKey drifts from design doc | Add exact BoardKey example tests from `docs/design.md`. |
| Fixtures become unreadable | Use named fixture cases with pre/post BoardKeys and explicit expected events. |

## Recommended Planner Constraints

- Every task must list exact files to create or modify.
- Every task must include `read_first` for `01-CONTEXT.md`, `docs/design.md`, and any file it will modify.
- Every plan must include requirements in frontmatter and map all ENG-01 through ENG-08 exactly once across the phase.
- Acceptance criteria should include concrete command outputs: `uv run pytest`, `uv run ruff check .`, and `uv run pyright` once the backend scaffold exists.
- If a command cannot run because scaffolding is not present yet, the task must create that scaffolding before using the command.

## Research Complete

Phase 1 can be planned without external documentation. The key is not external API knowledge; it is preserving the local design contracts, locking underdefined Gray Go edge cases into fixtures, and keeping the engine pure.

---
*Research completed: 2026-04-25*
