# Phase 1: Deterministic Engine & Rule Fixtures - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the pure deterministic Gray Go rule core only. It establishes board representation, coordinates, canonical BoardKey serialization, legal move validation, simultaneous move resolution, collision-to-gray behavior, toroidal liberties, two-stage captures, forbidden-point updates, pass handling, scoring, and regression fixtures.

It does not deliver orchestration, HTTP APIs, persistence, UI, provider adapters, prompts, transcripts, or model calls. Those belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Engine Authority

- **D-01:** The engine is the only authority for board state, legal moves, captures, forbidden points, pass state, scoring, and BoardKeys.
- **D-02:** Models and provider adapters are out of scope for this phase. Later model output may choose only a move; it must never provide authoritative board updates.
- **D-03:** The engine must be usable without FastAPI, Pydantic, SQLAlchemy, provider SDKs, or frontend code.

### Rule Semantics

- **D-04:** `graygo-v1` is the only ruleset in scope for Phase 1. Do not add a ruleset plugin system or variants.
- **D-05:** Resolution order is locked as: validate both moves from the same pre-turn board, apply simultaneous placements, convert same-point collisions to gray, apply Gray Go capture/forbidden updates, update pass/end state, then compute post-board and score/score estimate.
- **D-06:** Toroidal topology is mandatory. Neighbor/group/liberty logic must wrap around board edges rather than using ordinary Go boundaries.
- **D-07:** Any rule ambiguity discovered while planning or coding must be converted into a named fixture/spec case before implementation proceeds.

### Board and Move Shape

- **D-08:** Board cells use the design-document symbols: `+` for empty, `B` for Black, `W` for White, and `G` for gray.
- **D-09:** Coordinates use lowercase row letters with 1-based column numbers, matching examples such as `d4`; pass is represented as `PASS`.
- **D-10:** The canonical BoardKey is the human-readable slash-separated row string used in `docs/design.md`, for example `+++++++/+++++++/+++++++/+++++++/+++++++/+++++++/+++++++`.
- **D-11:** BoardKey generation must be deterministic and round-trip tested from board state to key and back.

### Testing Strategy

- **D-12:** Phase 1 should be test-first for rules: write golden fixtures before or alongside each rule implementation.
- **D-13:** Required fixture coverage includes legal moves, coordinate parsing, BoardKey round trips, toroidal neighbors, groups/liberties, same-point collision-to-gray, adjacent simultaneous placements, two-stage captures, forbidden-point updates, double pass, scoring, and deterministic replay.
- **D-14:** Use property tests where they strengthen invariants, especially BoardKey stability, coordinate round trips, toroidal neighbor symmetry, and deterministic resolution.

### the agent's Discretion

- The planner may choose exact Python module names and helper boundaries within the stack and architecture constraints.
- The planner may choose the fixture file format if it is readable, deterministic, and easy to extend.
- If the design document does not define exact scoring or forbidden-update semantics, the planner should create a small explicit spec/fixture task before implementation rather than guessing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and Requirements

- `.planning/PROJECT.md` - Core value, constraints, and backend-authority decisions.
- `.planning/REQUIREMENTS.md` - Phase 1 requirements ENG-01 through ENG-08.
- `.planning/ROADMAP.md` - Phase 1 goal, plan stubs, and success criteria.
- `.planning/STATE.md` - Current project focus and active Phase 1 rule-semantics concern.

### Source Design and Research

- `docs/design.md` - Original Gray Go backend-arbiter design, BoardKey examples, prompt shape, and implementation order.
- `.planning/research/SUMMARY.md` - Roadmap implications and Phase 1 research flags.
- `.planning/research/ARCHITECTURE.md` - Pure engine boundary and recommended project structure.
- `.planning/research/PITFALLS.md` - Gray Go edge-case, model-authority, and fake-first pitfalls relevant to Phase 1.
- `.planning/research/STACK.md` - Python backend/tooling recommendations for the deterministic engine and tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- No application source code exists yet. Phase 1 starts from a greenfield repository.

### Established Patterns

- GSD planning artifacts are established and committed.
- The repository now has a root `AGENTS.md` with project invariants and planned stack.

### Integration Points

- Future backend code should align with `.planning/research/ARCHITECTURE.md`, especially a pure engine separated from application orchestration, persistence, provider adapters, and API schemas.

</code_context>

<specifics>
## Specific Ideas

- The design document's BoardKey example should remain recognizable to operators and downstream prompt builders.
- Phase 1 should make fake/scripted-agent Phase 2 cheap by exposing a deterministic engine API over explicit inputs and outputs.
- Phase 1 should not optimize for real providers, UI rendering, or persistence yet.

</specifics>

<deferred>
## Deferred Ideas

- Fake random and deterministic scripted agents - Phase 2.
- REST/SSE API and SQLite persistence - Phase 2.
- React board visualization and cell inspection - Phase 3.
- Direct OpenAI and Anthropic adapters - Phase 4.
- Replay/export/leakage/budget guardrails - Phase 5.

</deferred>

---

*Phase: 01-deterministic-engine-rule-fixtures*
*Context gathered: 2026-04-25*
