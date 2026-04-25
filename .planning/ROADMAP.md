# Roadmap: Gray Go Arena

## Overview

Gray Go Arena v1 moves from a deterministic, fixture-proven rule engine to an auditable fake-agent backend, then adds the React operator console, direct OpenAI and Anthropic providers, and final trust hardening for replay, export, leakage checks, and guardrails. The dependency order preserves the core value: the backend remains the trusted arbiter for simultaneous move fairness, Gray Go correctness, and seat-private context isolation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Deterministic Engine & Rule Fixtures** - Prove authoritative Gray Go board state, rule resolution, BoardKeys, and regression fixtures.
- [x] **Phase 2: Fair Orchestrator, API & Persistence** - Run auditable fake/scripted games through fair orchestration, REST contracts, SQLite persistence, privacy boundaries, and an SSE shell.
- [x] **Phase 3: React Operator UI & Live Inspection** - Operate and inspect fake/scripted games end-to-end from the SPA.
- [x] **Phase 4: Direct OpenAI & Anthropic Providers** - Add real direct-provider seats behind backend-only credentials and existing validation.
- [ ] **Phase 5: Trust Hardening, Replay & Guardrails** - Harden exports, replay, leakage audit, secret handling, retention, and budget guardrails.

## Phase Details

### Phase 1: Deterministic Engine & Rule Fixtures
**Goal**: Users can rely on the backend as the authoritative Gray Go rule arbiter with deterministic board state, legal moves, resolution, and scoring.
**Depends on**: Nothing (first phase)
**Requirements**: ENG-01, ENG-02, ENG-03, ENG-04, ENG-05, ENG-06, ENG-07, ENG-08
**Success Criteria** (what must be TRUE):
  1. User can represent any configured square Gray Go board with coordinates, B/W/G/+ symbols, stable BoardKey serialization, and current turn metadata.
  2. User can validate legal placements and PASS from the current resolved board for either color.
  3. User can resolve simultaneous Black and White moves from one pre-turn board, including gray collisions, toroidal liberties, two-stage captures, and forbidden-point updates.
  4. User can finish a game through double-pass state and receive a deterministic score or score estimate.
  5. Automated fixtures cover legal moves, toroidal liberties, collisions, captures, forbidden points, pass handling, and scoring.
**Plans**: 3 plans

Plans:
- [x] 01-01: Board model, coordinates, symbols, BoardKey, turn metadata, and legal move validation
- [x] 01-02: Simultaneous resolution, collision-to-gray, toroidal liberties, captures, forbidden points, pass state, and scoring
- [x] 01-03: Golden fixtures, property checks, and regression test coverage for engine rules

### Phase 2: Fair Orchestrator, API & Persistence
**Goal**: Users can run auditable fake/scripted games through backend APIs with fair seat isolation, typed contracts, SQLite persistence, and live event delivery.
**Depends on**: Phase 1
**Requirements**: ORCH-01, ORCH-02, ORCH-03, ORCH-04, ORCH-05, ORCH-06, ORCH-07, PROV-01, PROV-02, PROV-03, PROV-06, API-01, API-02, API-03, API-04, API-05
**Success Criteria** (what must be TRUE):
  1. User can create, start, pause, resume, stop, autorun, and step games with board size, ruleset, seat configs, max turns, invalid move policy, visibility options, and run mode.
  2. System prompts Black and White from the same authoritative pre-turn BoardKey, validates structured replies, retries malformed or illegal output per policy, and resolves only after both seats respond.
  3. Fake random and deterministic scripted agents can play full games at zero provider cost with separate Black and White seat sessions, histories, and response references.
  4. User can call typed REST endpoints for provider discovery/testing, game lifecycle, current state, turns, and separated public/private/debug transcripts.
  5. SQLite records and live SSE events preserve games, seat sessions, turns, boards, agent calls, public logs, private transcripts, lifecycle changes, and errors without sharing seat state.
**Plans**: 4 plans

Plans:
- [x] 02-01: Orchestrator lifecycle, per-game locking, same-snapshot prompt flow, validation, retry, and invalid-move policy
- [x] 02-02: Fake random/scripted adapters, provider aliases, provider tests, and seat-scoped session state
- [x] 02-03: REST schemas, lifecycle endpoints, transcript endpoints, and SSE event shell
- [x] 02-04: SQLite persistence, repositories/unit of work, audit records, privacy boundaries, and integration tests

### Phase 3: React Operator UI & Live Inspection
**Goal**: Users can operate fake/scripted games end-to-end in a React SPA with authoritative board visualization, lifecycle controls, history, and transcript/audit inspection.
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09
**Success Criteria** (what must be TRUE):
  1. User can configure a new fake/scripted game in the SPA, including board size, ruleset, provider/model/credential alias per seat, temperature, max output tokens, run mode, max turns, and visibility toggles.
  2. User sees a clear same-provider/model notice and can then view the live board with coordinates, B/W/G/+ symbols, current status, turn number, and backend BoardKey.
  3. User can step, run, pause, stop, and export from the live game view while SSE updates and refetches stay aligned with backend state.
  4. User can inspect the latest turn and game history for moves, collisions, captures, forbidden updates, pre/post BoardKeys, public logs, private summaries, raw responses, and validation audit when enabled.
  5. User can inspect board cells and toggle toroidal neighbors, last Black move, last White move, collisions, and captured-stone visualizations.
**Plans**: 4 plans
**UI hint**: yes

Plans:
- [x] 03-01: React/Vite app shell, generated API client, routing, New Game form, and same-provider/model notice
- [x] 03-02: Live board, coordinates, cell inspector, visualization toggles, status, turn number, and BoardKey display
- [x] 03-03: Step/run/pause/stop/export controls, SSE client behavior, reconnect/refetch handling, and fake-game verification
- [x] 03-04: Turn audit, seat panels, transcript/history browsing, raw JSON display, and validation audit screens

### Phase 4: Direct OpenAI & Anthropic Providers
**Goal**: Users can run real direct-provider seats through backend-only OpenAI and Anthropic adapters under the same validation, persistence, and seat-isolation rules.
**Depends on**: Phase 3
**Requirements**: PROV-04, PROV-05
**Success Criteria** (what must be TRUE):
  1. User can select a configured OpenAI alias/model and the backend submits structured move requests using backend-only credentials.
  2. User can select a configured Anthropic alias/model and the backend validates server-side JSON move outputs before resolution.
  3. Provider timeouts, errors, malformed outputs, and stale BoardKeys are surfaced as auditable provider outcomes without corrupting game state.
  4. OpenAI and Anthropic raw responses and metadata are captured only through sanitized, per-seat audit paths.
**Plans**: 2 plans

Plans:
- [x] 04-01: OpenAI direct adapter, structured output handling, health test path, error mapping, and audit metadata
- [x] 04-02: Anthropic direct adapter, server-side JSON validation, health test path, error mapping, and fake-to-real provider regression tests

### Phase 5: Trust Hardening, Replay & Guardrails
**Goal**: Users can trust and carry away completed real-model games through replay/export, leakage audit, and local guardrails for secrets, retention, and budget exposure.
**Depends on**: Phase 4
**Requirements**: PROV-07, API-06, UI-10
**Success Criteria** (what must be TRUE):
  1. User can retrieve or export enough turn history to replay and debug a game without relying on provider-side state.
  2. User can audit stored game, turn, and agent-call records and confirm raw API keys or OAuth tokens are never persisted.
  3. User can view provider status and settings guardrails in the SPA without entering or exposing actual secret token values in the browser.
  4. User can run leakage, retention, and budget guardrail checks that flag private transcript exposure, over-retention, or unexpected provider spend before longer matches.
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [ ] 05-01: Replay retrieval, redacted export bundles, and debug history completeness checks
- [ ] 05-02: Secret-storage audit, leakage checks, transcript/export redaction, and public/private boundary verification
- [ ] 05-03: Provider settings guardrail UI, retention controls, budget metadata checks, and long-run readiness tests

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Deterministic Engine & Rule Fixtures | 3/3 | Complete | 2026-04-25 |
| 2. Fair Orchestrator, API & Persistence | 4/4 | Complete | 2026-04-25 |
| 3. React Operator UI & Live Inspection | 4/4 | Complete | 2026-04-25 |
| 4. Direct OpenAI & Anthropic Providers | 2/2 | Complete | 2026-04-25 |
| 5. Trust Hardening, Replay & Guardrails | 0/3 | Not started | - |
