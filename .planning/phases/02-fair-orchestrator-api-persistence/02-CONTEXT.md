# Phase 2: Fair Orchestrator, API & Persistence - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 turns the verified pure engine into a runnable backend slice. It delivers fake/scripted provider adapters, seat-isolated game orchestration, typed REST APIs, SQLite persistence, transcript/audit records, and an SSE event shell.

It does not deliver the React SPA, direct OpenAI/Anthropic calls, hosted auth, exports, replay bundles, or provider cost guardrails. Those belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Backend Authority

- **D-01:** The Phase 1 engine remains the only authority for BoardKeys, legal moves, resolution, captures, forbidden state, double-pass state, and scoring.
- **D-02:** The orchestrator validates model/provider output and calls `resolve_turn`; providers return candidate moves only.
- **D-03:** Prompt construction must use one pre-turn snapshot and must not include either pending move in the other seat's request.

### Seat Isolation

- **D-04:** Every game creates one Black seat session and one White seat session, even when both seats use the same provider/model/credential alias.
- **D-05:** Seat histories, raw provider responses, strategic summaries, parsed moves, provider references, and retry outcomes are scoped by `seat_session_id`.
- **D-06:** Transcript views are filtered from persisted records; UI/API filtering is not a substitute for isolated persisted seat records.

### Providers

- **D-07:** Phase 2 supports fake random and deterministic scripted adapters only. Direct OpenAI/Anthropic adapters are deferred to Phase 4.
- **D-08:** Provider aliases are safe metadata and never expose token values. Fake/scripted provider test endpoints must not call the network.
- **D-09:** Invalid provider output is retried once, then handled by deterministic policy. Phase 2 defaults to force `PASS`.

### API and Persistence

- **D-10:** REST endpoints expose create/get/lifecycle/step/autorun/turns/transcripts/provider discovery/provider test.
- **D-11:** SSE events are notifications derived from persisted state; the database remains the source of truth.
- **D-12:** SQLite persistence stores games, seats, turns, agent calls, events, public logs, and private seat transcripts with credential refs only.
- **D-13:** Use stdlib SQLite for Phase 2 to keep the local backend small; defer SQLAlchemy/Alembic until schema complexity demands it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and Requirements

- `.planning/PROJECT.md` - Core value and backend-authority constraints.
- `.planning/REQUIREMENTS.md` - Phase 2 requirements ORCH-01 through ORCH-07, PROV-01 through PROV-03, PROV-06, and API-01 through API-05.
- `.planning/ROADMAP.md` - Phase 2 goal, plan stubs, dependencies, and success criteria.
- `.planning/STATE.md` - Current focus and Phase 1 completion state.

### Phase 1 Engine

- `.planning/phases/01-deterministic-engine-rule-fixtures/01-01-SUMMARY.md`
- `.planning/phases/01-deterministic-engine-rule-fixtures/01-02-SUMMARY.md`
- `.planning/phases/01-deterministic-engine-rule-fixtures/01-03-SUMMARY.md`
- `backend/src/graygo_arena/engine/` - Pure deterministic engine APIs.
- `backend/tests/fixtures/engine_cases.json` - Golden rule fixtures.

### Design and Research

- `docs/design.md` - API endpoints, persistence shape, prompt/privacy policy, and turn orchestration pseudocode.
- `.planning/research/ARCHITECTURE.md` - Modular-monolith boundary guidance.
- `.planning/research/FEATURES.md` - MVP feature dependencies and anti-features.
- `.planning/research/STACK.md` - Backend stack guidance.

</canonical_refs>

<specifics>
## Specific Ideas

- Keep initial provider aliases to `fake_random`, `scripted_center`, and `scripted_pass`.
- Store BoardKeys and JSON payloads as text columns in SQLite.
- Keep autorun bounded by `max_turns`; a simple synchronous loop is acceptable in Phase 2.
- The SSE shell can replay persisted events and keep a lightweight in-memory subscription queue for live listeners.

</specifics>

<deferred>
## Deferred Ideas

- React UI, generated API client, and board visualization - Phase 3.
- Direct OpenAI and Anthropic provider SDK calls - Phase 4.
- Redacted exports, leakage audit, retention, budget checks, and replay bundles - Phase 5.

</deferred>

---

*Phase: 02-fair-orchestrator-api-persistence*
*Context gathered: 2026-04-25*
