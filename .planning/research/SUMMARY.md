# Project Research Summary

**Project:** Gray Go Arena
**Domain:** Local-first AI-vs-AI simultaneous-turn Gray Go arena
**Researched:** 2026-04-25
**Confidence:** HIGH for v1 roadmap direction; MEDIUM for provider/API details that can change quickly

## Executive Summary

Gray Go Arena is a local operator console for running simultaneous-turn Gray Go matches between isolated AI seats. Experts should build this kind of product as a backend-authoritative system: the backend owns all game state, rule resolution, provider calls, credentials, persistence, transcript boundaries, and event publication; the frontend only configures games, renders authoritative state, and inspects audit evidence.

The recommended approach is a modular FastAPI/Python backend with a pure deterministic Gray Go engine, SQLAlchemy/SQLite persistence, backend-only provider aliases, fake/scripted agents first, direct OpenAI/Anthropic adapters second, and a React/TypeScript/Vite SPA using REST plus SSE. Avoid agent frameworks, browser provider calls, shared seat sessions, and AI-authored board updates in v1.

The major risks are rule ambiguity, simultaneity leaks, same-model privacy cross-contamination, weak validation of model output, provider failures corrupting state, and UI/backend drift. The roadmap should mitigate these by proving engine fixtures and fake-agent orchestration before paid providers, enforcing seat-scoped data models and prompt queries before transcript UI, making every turn replayable, and treating events as update hints rather than source of truth.

## Key Findings

### Recommended Stack

Use a split stack: Python/FastAPI backend as the trusted arbiter and React/TypeScript/Vite frontend as an inspection/control client. Keep the engine as pure Python domain code, use Pydantic only at trust boundaries, use SQLAlchemy 2.x over SQLite for auditable local persistence, and use SSE before WebSocket because live updates are mostly one-way.

**Core technologies:**
- Python 3.14 + uv 0.11.7: backend runtime and reproducible dependency management.
- FastAPI 0.136.1 + Pydantic 2.13.3 + Pydantic Settings 2.14.0: typed API schemas, provider move-output validation, backend-only configuration.
- SQLAlchemy 2.0.49 + SQLite + aiosqlite 0.22.1 + Alembic 1.18.4: local persistence, explicit transactions, future PostgreSQL path.
- sse-starlette 3.3.4: live game updates through browser `EventSource`.
- OpenAI SDK 2.32.0 and Anthropic SDK 0.97.0: direct backend provider adapters after fake/scripted agents are proven.
- React 19.2.5 + TypeScript 6.0.3 + Vite 8.0.10: SPA runtime for board visualization and operator workflows.
- TanStack Query, openapi-typescript/openapi-fetch, and Zod: typed REST access, generated contracts, and SSE payload validation.
- pytest, pytest-asyncio, Hypothesis, Ruff, Pyright, Vitest, Testing Library, and Playwright: engine, orchestration, API, UI, and E2E verification.

### Expected Features

**Must have (table stakes):**
- Deterministic Gray Go engine for legal moves, collision-to-gray, toroidal liberties, two-stage captures, forbidden points, pass handling, scoring, and BoardKey stability.
- Simultaneous-turn orchestrator that builds both prompts from the same pre-board snapshot and resolves both moves together.
- Isolated Black and White seat sessions, including separate private histories, raw responses, provider state references, and transcript storage.
- Backend-only credential aliases and provider discovery/test endpoints that never expose token values.
- Fake random and deterministic scripted agents for zero-cost verification before paid providers.
- Structured move output contract with server-side JSON, BoardKey, legal-move validation, one retry, and explicit invalid-output policy.
- SQLite persistence for games, turns, boards, seat sessions, provider calls, public events, and private transcripts.
- REST lifecycle API plus SSE stream for create/start/pause/stop/step/autorun/current state/turn history/transcripts.
- React UI for New Game, Live Game, History, Provider Status, Settings, board inspection, turn audit, and transcript views.

**Should have (post-validation differentiators):**
- Fairness proof per turn with prompt hashes, same pre-BoardKey, call timing, and resolution inputs.
- Seat isolation proof/debug view with per-seat session IDs and prompt-context manifests.
- Gray Go-specific visualization for collisions, captures, forbidden points, and toroidal neighbors.
- Replayable redacted game bundles and deterministic replay viewer.
- Provider comparison metrics, batch match runner, leakage audit mode, retention/redaction controls, and budget guardrails.

**Defer (v2+):**
- CLI adapters for Codex/Claude Code and local models until per-seat filesystem/config/auth sandboxing is designed.
- Tournament ladders, hosted/collaborative mode, public gallery, rule variants, plugins, and multi-user auth until local fairness/privacy are proven.
- PostgreSQL-first deployment and cloud sync/telemetry by default.

### Architecture Approach

Build a modular monolith. The `graygo` engine is pure and deterministic; application services coordinate orchestration, prompts, validation, repositories, providers, and events; adapters handle fake/scripted providers, direct provider SDKs, SQLite persistence, and SSE transport. Route handlers stay thin, the browser never sees secrets, and the UI derives board state only from backend `GameView`/`TurnView` payloads.

**Major components:**
1. `graygo.engine` and domain models: authoritative board representation, BoardKey, legal moves, simultaneous resolution, capture/forbidden/scoring rules.
2. `application.game_orchestrator`: create/step/start/pause/stop/autorun use cases, per-game locking, same-snapshot prompt flow, retries, invalid-output policy, lifecycle transitions.
3. `application.prompt_builder` and privacy policy: public history plus own-seat private memory only; never opponent private/debug data.
4. Provider ports/adapters: normalized `ProviderAdapter` interface, fake/scripted first, OpenAI/Anthropic direct later.
5. Persistence repositories/unit of work: SQLite schema, turn transactions, replayable audit records, credential refs only.
6. Event bus/SSE: typed notifications after meaningful state transitions; events are hints, not source of truth.
7. Frontend features: New Game, Live Game, History, Providers, Settings, board components, transcript/audit panels, typed REST/SSE clients.

### Critical Pitfalls

1. **Model output becomes board authority** — accept only candidate moves; compute all board changes, captures, scoring, and BoardKeys in the engine.
2. **Simultaneity leaks through sequential orchestration** — build both prompts from one immutable pre-turn snapshot and hide pending moves until both are validated and resolved.
3. **Seat privacy cross-contaminates same-model games** — key all state by `(game_id, color)`/`seat_session_id`; enforce transcript views server-side.
4. **Malformed, stale, or illegal model output is normalized away** — require structured JSON, exact BoardKey match, legal move membership, retry-once from the original snapshot, and explicit failure policy.
5. **Provider credentials escape the backend** — expose aliases only, sanitize logs/errors/exports, scan API responses, SPA build output, SQLite, and exported bundles.
6. **Persistence cannot reconstruct a turn** — persist pre-board, prompts/metadata, raw and parsed outputs, validation, resolution, post-board, captures, forbidden updates, status, and BoardKeys.
7. **UI displays a different game than the backend** — render backend board state only, sequence events, and refetch current game/turns on reconnect.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Deterministic Engine & Rule Fixtures
**Rationale:** Every later phase depends on rule correctness; Gray Go edge cases are not ordinary Go.
**Delivers:** Domain types, canonical board encoding, BoardKey, legal moves, simultaneous placement, collision-to-gray, toroidal liberties, two-stage capture, forbidden points, pass/scoring, golden fixtures, Hypothesis/property tests.
**Addresses:** Deterministic engine, regression scenarios, backend board authority.
**Avoids:** Model-authored board updates, Gray Go rule drift, weak BoardKey canonicalization.

### Phase 2: Fair Orchestrator With Fake/Scripted Agents
**Rationale:** Simultaneity and seat isolation must be runtime invariants before API, UI, persistence, or paid providers add noise.
**Delivers:** Provider/repository/event ports, fake random and scripted adapters, in-memory repository, `step()` orchestration, per-game lock, same-snapshot prompts, structured move validation, retry-once policy, fake delay/spy tests.
**Addresses:** Simultaneous-turn orchestrator, isolated seat sessions, fake/scripted agents, invalid-output policy.
**Avoids:** Sequential prompt contamination, shared provider state, lifecycle races, provider-first debugging.

### Phase 3: API, SQLite Persistence & Privacy Boundaries
**Rationale:** The frontend and real providers need durable, auditable backend contracts; privacy must be enforced server-side before transcript screens exist.
**Delivers:** FastAPI routes, Pydantic DTOs, provider alias discovery/test shell, SQLAlchemy/Alembic schema, repositories/unit of work, turn audit records, transcript visibility model, SSE endpoint, secret-free storage.
**Addresses:** REST lifecycle API, local persistence, provider aliases, turn history, transcript endpoints.
**Avoids:** Thin audit schema, browser-visible secrets, UI-only privacy, long SQLite transactions around provider calls.

### Phase 4: Operator UI & Live Inspection
**Rationale:** The operator needs an end-to-end fake-agent console before real provider costs and failures are introduced.
**Delivers:** React/Vite SPA, generated API types, New Game, Live Game, board inspector, manual step/run/pause controls, turn audit, history, provider status/settings, SSE reconnect/refetch behavior.
**Addresses:** Board visualization, lifecycle controls, event stream, history, public/private transcript inspection shell.
**Avoids:** Frontend rule authority, event stream as source of truth, stale UI state, mislabeled private transcript views.

### Phase 5: Direct OpenAI & Anthropic Provider Adapters
**Rationale:** Real model play is valuable only after fake-agent E2E, persistence, validation, and inspection prove the core loop.
**Delivers:** Backend-only OpenAI/Anthropic adapters, configured model aliases, provider health tests, structured output handling, timeouts, retries, provider error classes, token/latency/request metadata, sanitized raw response capture.
**Addresses:** Real AI-vs-AI matches, provider discovery/test, structured output contract, provider call records.
**Avoids:** Paid-provider flakiness corrupting state, stale late responses, credential leaks, uncontrolled cost/rate-limit failures.

### Phase 6: Trust Hardening, Replay & Export
**Rationale:** Once real matches run, the product needs stronger proof, recovery, and portable artifacts without expanding scope into tournaments yet.
**Delivers:** Replay verification, redacted export/import, leakage audit mode, prompt-context manifests, budget guardrails, retention/redaction controls, crash recovery tests, local traces.
**Addresses:** Fairness proof, seat isolation proof, replayable bundles, privacy/leakage audit, cost controls.
**Avoids:** Irreconstructable games, private transcript export leaks, unbounded prompt history, silent cost growth.

### Phase 7: Scale & Extension
**Rationale:** Batch comparisons, tournaments, CLI/local adapters, PostgreSQL, and hosted mode require the v1 trust model to be stable first.
**Delivers:** Batch runner, provider comparison dashboard, tournament ladder, optional PostgreSQL/outbox/pubsub, WebSocket if needed, CLI/local-model adapters with per-seat sandboxes, hosted auth/tenancy research.
**Addresses:** v1.x/v2 differentiators after validation.
**Avoids:** Premature horizontal scaling, shared CLI auth/session caches, hosted secret/tenant risks.

### Phase Ordering Rationale

- Engine first because all API, UI, persistence, replay, and provider behavior depends on deterministic rule resolution.
- Orchestrator second because fairness and seat isolation are core product promises and cannot be patched in as UI filters.
- Persistence/privacy before paid providers because real API failures and malformed responses must be auditable and recoverable.
- UI before real providers because fake-agent E2E should validate board rendering, lifecycle controls, events, and transcript boundaries without cost.
- Provider adapters after fake E2E because provider variability should test the arena, not obscure unfinished invariants.
- Replay/export/hardening after real-provider validation because actual transcripts and failure modes will reveal which controls matter.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Clarify exact Gray Go edge-case semantics for two-stage capture, forbidden updates, pass/scoring, and toroidal topology before coding fixtures.
- **Phase 5:** Re-check current OpenAI/Anthropic structured-output APIs, model aliases, errors, timeout behavior, and SDK usage immediately before implementation.
- **Phase 6:** Research redaction/export policy, retention defaults, and prompt-leakage audit heuristics against actual stored transcript shapes.
- **Phase 7:** Research CLI sandboxing, local-model structured output limits, PostgreSQL/job/outbox choices, and hosted auth/secret management if promoted.

Phases with standard patterns (skip research-phase unless requirements change):
- **Phase 2:** Ports/adapters, in-memory fakes, per-game locks, and spy/delay tests are well-understood once Phase 1 rules are fixed.
- **Phase 3:** FastAPI route structure, SQLAlchemy repositories, Alembic migrations, SQLite WAL/foreign keys, and SSE are established patterns.
- **Phase 4:** React/Vite/TanStack Query/OpenAPI typed client workflows are standard; focus planning on UX flows and contract tests.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Package versions and compatibility were checked against registries and official docs; provider model/API behavior remains MEDIUM because providers change quickly. |
| Features | HIGH for v1, MEDIUM for v1.x/v2 | v1 scope follows project constraints and core trust requirements; later metrics, tournaments, and adapters should follow validation data. |
| Architecture | HIGH | Boundaries are strongly implied by backend authority, simultaneity, seat isolation, local-first persistence, and auditability constraints. |
| Pitfalls | HIGH | Risks are directly derived from product invariants and known failure modes for LLM/provider integrations, realtime UI, SQLite, and secret handling. |

**Overall confidence:** HIGH for v1 phase ordering and first implementation slices; MEDIUM for later provider, export, CLI, and hosted expansion details.

### Gaps to Address

- **Exact Gray Go rules:** Convert any unresolved rule ambiguity into golden fixtures before Phase 1 implementation.
- **Prompt schema details:** Lock the structured move response shape, BoardKey field, diagnostic board echo naming, and strategic summary limits before provider work.
- **Invalid/failure policy defaults:** Decide early whether v1 defaults to manual intervention, retry-then-pass, or retry-then-forfeit for invalid output and provider errors.
- **Transcript retention/export defaults:** Define which raw/private/debug records are kept, displayed, exported, and redacted before Phase 6.
- **Provider aliases/models:** Keep model IDs config-driven and revalidate OpenAI/Anthropic SDK/API details during Phase 5 planning.
- **SQLite durability expectations:** Decide recovery behavior for `agent_thinking`, `awaiting_retry`, cancelled, failed, and manual-intervention states.
- **UI information design:** Validate how much audit/transcript detail the operator can scan without confusing model diagnostics for backend truth.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — project definition, active requirements, constraints, key decisions.
- `.planning/research/STACK.md` — recommended technologies, package versions, alternatives, compatibility.
- `.planning/research/FEATURES.md` — table stakes, differentiators, anti-features, MVP and v1.x/v2 scope.
- `.planning/research/ARCHITECTURE.md` — modular monolith approach, component boundaries, data flow, build order.
- `.planning/research/PITFALLS.md` — critical pitfalls, detection checks, phase warnings, recovery strategies.
- `docs/design.md` — original product architecture, API sketch, data model, prompt/privacy policy, and implementation order referenced by research agents.

### Official documentation and registries cited by research
- FastAPI, Pydantic, SQLAlchemy, SQLite, Vite, React, OpenAI, Anthropic, Node.js, and Python official docs.
- PyPI and npm registry package/version checks from 2026-04-25.
- OWASP Secrets Management Cheat Sheet, OpenTelemetry overview, Ink & Switch local-first software paper.

### Secondary (MEDIUM confidence)
- Provider model/API behavior, structured-output details, rate-limit/error behavior, and future CLI/local-model adapter designs; re-check official docs during the relevant phases.

---
*Research completed: 2026-04-25*
*Ready for roadmap: yes*
