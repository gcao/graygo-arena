# Requirements: Gray Go Arena

**Defined:** 2026-04-24
**Core Value:** The backend must be the trusted arbiter: it must preserve simultaneous move fairness, enforce Gray Go rules exactly, and prevent private seat context from leaking between agents.

## v1 Requirements

### Engine

- [ ] **ENG-01**: System can represent a configurable square Gray Go board with coordinates, symbols, BoardKey serialization, and current turn metadata.
- [ ] **ENG-02**: System can validate legal moves for each color from the current resolved board, including PASS.
- [ ] **ENG-03**: System resolves simultaneous Black and White moves from the same pre-turn board without exposing either pending move to the other seat.
- [ ] **ENG-04**: System converts same-point simultaneous placements into gray collision points according to the Gray Go ruleset.
- [ ] **ENG-05**: System computes toroidal neighbors, groups, and liberties consistently for all board positions.
- [ ] **ENG-06**: System applies two-stage captures and forbidden-point updates deterministically.
- [ ] **ENG-07**: System tracks double-pass state and computes a final score or score estimate when a game ends.
- [ ] **ENG-08**: Automated tests cover legal move validation, toroidal liberties, collision-to-gray behavior, captures, forbidden points, pass handling, and scoring.

### Orchestration

- [ ] **ORCH-01**: User can create a game with board size, ruleset, Black seat config, White seat config, max turns, invalid move policy, visibility options, and run mode.
- [ ] **ORCH-02**: System creates separate Black and White seat sessions for every game, including same-provider and same-model games.
- [ ] **ORCH-03**: User can start, pause, resume, stop, autorun, and step exactly one simultaneous turn.
- [ ] **ORCH-04**: System prompts both seats from the same authoritative pre-turn board and BoardKey before resolving either move.
- [ ] **ORCH-05**: System validates each agent reply against expected BoardKey, JSON schema, legal moves, and configured retry policy.
- [ ] **ORCH-06**: System persists each turn before and after resolution with enough audit data to reconstruct the decision and rule outcome.
- [ ] **ORCH-07**: System publishes live events for agent call start/finish, turn resolution, game finish, and errors.

### Providers

- [ ] **PROV-01**: User can list configured provider aliases and models without exposing secret values.
- [ ] **PROV-02**: User can test a configured provider alias/model from the backend.
- [ ] **PROV-03**: System includes fake random and deterministic scripted provider adapters for zero-cost development and verification.
- [ ] **PROV-04**: System includes an OpenAI direct API adapter that uses backend-only credentials and structured output validation where supported.
- [ ] **PROV-05**: System includes an Anthropic direct API adapter that uses backend-only credentials and server-side JSON validation.
- [ ] **PROV-06**: System stores provider session references, local message history, and previous response identifiers per seat without sharing them across seats.
- [ ] **PROV-07**: System never stores raw API key or OAuth token values in persistent game, turn, or agent-call records.

### API and Persistence

- [ ] **API-01**: Backend exposes REST endpoints for provider listing, provider testing, game creation, game retrieval, lifecycle controls, single-step execution, autorun, turns, and transcripts.
- [ ] **API-02**: Backend exposes an SSE or WebSocket endpoint that streams game events to the UI.
- [ ] **API-03**: Backend validates request and response bodies with typed schemas.
- [ ] **API-04**: Backend persists games, seat sessions, turns, agent calls, boards, captures, forbidden updates, public logs, and private seat transcripts in SQLite for local development.
- [ ] **API-05**: Backend can return public transcript, Black-private transcript, White-private transcript, and debug transcript views with access separation enforced server-side.
- [ ] **API-06**: Backend can export or retrieve enough turn history for UI replay and debugging.

### User Interface

- [ ] **UI-01**: User can configure a new game from the SPA, including board size, ruleset, provider/model/credential alias per seat, temperature, max output tokens, run mode, max turns, and visibility toggles.
- [ ] **UI-02**: User sees a clear notice when the same provider/model is selected for both seats and that isolated seat sessions will be created.
- [ ] **UI-03**: User can view the live board with coordinates, B/W/G/+ symbols, current status, turn number, and backend BoardKey.
- [ ] **UI-04**: User can step, run, pause, stop, and export from the live game view.
- [ ] **UI-05**: User can inspect the latest turn resolution, including Black move, White move, collisions, captures, forbidden updates, and pre/post BoardKeys.
- [ ] **UI-06**: User can inspect Black and White panels with provider/model, thinking state, current move, strategic summary, errors, and optional raw JSON.
- [ ] **UI-07**: User can browse game history and expand each turn for public log, private seat summaries, raw provider responses, and backend validation audit when enabled.
- [ ] **UI-08**: User can inspect a board cell for coordinate, contents, neighbors, group, and liberties.
- [ ] **UI-09**: User can toggle visualization for toroidal neighbors, last Black move, last White move, collisions, and captured stones.
- [ ] **UI-10**: User can view provider status and settings without entering or exposing actual secret tokens in the browser.

## v2 Requirements

### Provider Expansion

- **PROV2-01**: System can run Claude Code CLI/OAuth-backed seats with isolated working/config directories per color.
- **PROV2-02**: System can run Codex CLI/API-key-backed seats with separate CODEX_HOME directories per color.
- **PROV2-03**: System can run local model adapters.

### Persistence and Deployment

- **DATA2-01**: System can use PostgreSQL when transcripts and multi-game durability need production-grade persistence.
- **DATA2-02**: System supports multi-operator access control for hosted use.
- **DATA2-03**: System supports retention policies for raw provider responses and private transcripts.

### Analysis

- **ANALYZE2-01**: User can compare strategy quality across providers/models over multiple games.
- **ANALYZE2-02**: User can replay games turn-by-turn from persisted history.
- **ANALYZE2-03**: User can export datasets for external analysis.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Browser-entered provider secrets | Violates the backend-only credential model and risks token exposure. |
| Model-authored board state | The model is a move selector only; backend engine authority is the core correctness guarantee. |
| Shared conversations between Black and White | Breaks privacy and fairness, especially when both seats use the same model. |
| Public hosted multi-tenant service in v1 | Requires authentication, authorization, rate limiting, billing, and stronger secret management beyond MVP scope. |
| CLI-backed Claude Code/Codex adapters in v1 | Operationally fragile compared with direct provider APIs; defer until direct adapters work. |
| PostgreSQL in the first implementation pass | SQLite is sufficient for local development and simpler to verify early. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENG-01 | Phase 1 | Pending |
| ENG-02 | Phase 1 | Pending |
| ENG-03 | Phase 1 | Pending |
| ENG-04 | Phase 1 | Pending |
| ENG-05 | Phase 1 | Pending |
| ENG-06 | Phase 1 | Pending |
| ENG-07 | Phase 1 | Pending |
| ENG-08 | Phase 1 | Pending |
| ORCH-01 | Phase 2 | Pending |
| ORCH-02 | Phase 2 | Pending |
| ORCH-03 | Phase 2 | Pending |
| ORCH-04 | Phase 2 | Pending |
| ORCH-05 | Phase 2 | Pending |
| ORCH-06 | Phase 2 | Pending |
| ORCH-07 | Phase 2 | Pending |
| PROV-01 | Phase 2 | Pending |
| PROV-02 | Phase 2 | Pending |
| PROV-03 | Phase 2 | Pending |
| PROV-04 | Phase 4 | Pending |
| PROV-05 | Phase 4 | Pending |
| PROV-06 | Phase 2 | Pending |
| PROV-07 | Phase 5 | Pending |
| API-01 | Phase 2 | Pending |
| API-02 | Phase 2 | Pending |
| API-03 | Phase 2 | Pending |
| API-04 | Phase 2 | Pending |
| API-05 | Phase 2 | Pending |
| API-06 | Phase 5 | Pending |
| UI-01 | Phase 3 | Pending |
| UI-02 | Phase 3 | Pending |
| UI-03 | Phase 3 | Pending |
| UI-04 | Phase 3 | Pending |
| UI-05 | Phase 3 | Pending |
| UI-06 | Phase 3 | Pending |
| UI-07 | Phase 3 | Pending |
| UI-08 | Phase 3 | Pending |
| UI-09 | Phase 3 | Pending |
| UI-10 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after initialization from docs/design.md*
