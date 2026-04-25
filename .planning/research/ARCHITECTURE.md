# Architecture Research

**Project:** Gray Go Arena
**Domain:** Local-first AI-vs-AI simultaneous-turn board-game arena
**Researched:** 2026-04-25
**Confidence:** HIGH for project-specific architecture constraints, MEDIUM for provider-specific future adapter details

## Executive Recommendation

Build Gray Go Arena as a modular monolith with a FastAPI backend as the only authority for state, rule resolution, provider calls, persistence, and live events. The React/Vite frontend should be a client of backend state only: it configures games, sends lifecycle commands, renders boards, and inspects transcripts, but never stores provider secrets or computes authoritative board updates.

The most important architecture boundary is between the deterministic Gray Go engine and every IO concern. The engine should be a pure Python module that takes an immutable pre-turn game state plus two validated moves, then returns a deterministic resolution object. It must not know about FastAPI, SQLAlchemy, provider SDKs, prompts, or UI models. That makes rule correctness testable before paid model calls exist.

The second critical boundary is seat isolation. Black and White must be represented as separate seat sessions even when they use the same provider, model, and credential alias. Prompt building, provider session references, stored histories, private strategic summaries, raw model responses, retry state, and any future CLI working directories must be scoped by `seat_session_id`, never by provider/model alone.

Use repository and provider adapter interfaces early, even if the first implementations are in-memory and fake. The first working slice should run one simultaneous turn with fake/scripted agents, validate BoardKey and moves, resolve the turn through the engine, persist or record the result through a repository port, and emit typed events. Real OpenAI/Anthropic adapters should come only after that loop is deterministic and observable.

## Architecture Constraints

| Constraint | Architectural consequence |
|------------|---------------------------|
| Backend is the arbiter | Only backend engine can mutate board state, forbidden points, captures, pass counters, scores, and game status. |
| Simultaneous turns | Both seat prompts are built from the same pre-turn snapshot before either pending move is known to the other side. |
| Seat isolation | Black and White have distinct `seat_sessions`, prompt histories, private transcripts, provider session refs, retries, and optional CLI state. |
| Server-side credentials | Browser receives configured aliases and model descriptors only; provider tokens remain in backend config. |
| Deterministic rules | Engine must be pure and replayable from stored turn inputs. No provider output can become authoritative board state. |
| Auditable games | Store enough data to reconstruct pre-board, BoardKey, prompts, raw outputs, parsed moves, validation, resolution, captures, and post-board. |
| Local-first v1 | Single-process FastAPI plus SQLite is acceptable at first, but in-memory locks/events must not be mistaken for horizontal-scale primitives. |

## System Overview

```text
Operator Browser
  |
  | REST commands: create, start, step, pause, stop, inspect
  | SSE first: typed game events
  v
+----------------------------- FastAPI Backend -----------------------------+
|                                                                           |
|  api/                                                                     |
|    routers translate HTTP/SSE to application calls                         |
|    schemas expose safe public DTOs                                         |
|                                                                           |
|  application/                                                             |
|    game orchestrator owns use cases and game state transitions             |
|    prompt builder enforces privacy policy                                  |
|    autorun manager owns cancellable per-game loops                          |
|                                                                           |
|  domain/                                                                  |
|    Gray Go engine resolves legal moves, collisions, captures, scoring      |
|    domain models define Board, BoardKey, Move, GameState, TurnResult       |
|                                                                           |
|  ports/                                                                   |
|    ProviderAdapter, GameRepository, EventBus, Clock, IdGenerator           |
|                                                                           |
|  adapters/                                                                |
|    fake/scripted providers first                                           |
|    OpenAI and Anthropic direct providers later                             |
|    SQLAlchemy/SQLite persistence                                           |
|    in-memory event bus or SSE stream source                                |
|                                                                           |
+---------------------------------------------------------------------------+
  |
  | persisted audit records
  v
+-------------------------- SQLite in v1 -----------------------------------+
| games | seat_sessions | turns | agent_calls | board_snapshots | events     |
+---------------------------------------------------------------------------+
```

Recommended initial transport choice: REST for commands and queries, SSE for live updates. SSE is simpler than WebSocket for one-way event fanout from backend to UI, and the UI can still issue all control commands through REST. Add WebSocket only if the product later needs bidirectional realtime interactions beyond REST commands.

## Component Responsibilities

| Component | Owns | Must not own | Communicates with |
|-----------|------|--------------|-------------------|
| `graygo.engine` | Board representation, BoardKey, legal moves, simultaneous resolution, collision-to-gray, toroidal liberties, two-stage captures, forbidden points, pass/scoring rules | Provider calls, prompts, persistence, HTTP, UI DTOs | Orchestrator only |
| `domain.models` | Stable domain types and enums such as `SeatColor`, `Move`, `Board`, `GameStatus`, `TurnResolution` | ORM concerns or HTTP response shapes | Engine, orchestrator, repositories |
| `application.game_orchestrator` | Use cases: create game, step turn, start/pause/resume/stop, autorun loop decisions, invalid-move policy | Provider-specific SDK code, SQLAlchemy models in route handlers, UI state | Engine, repositories, providers, event bus |
| `application.prompt_builder` | Prompt composition and privacy policy, legal move list insertion, BoardKey insertion, public vs private history selection | Provider transport, board mutation, opponent private data | Orchestrator, repositories |
| `ports.providers` | Adapter protocol and normalized provider response types | Concrete provider credentials or engine logic | Orchestrator and concrete adapters |
| `providers.fake` and `providers.scripted` | Cheap deterministic test agents | Network calls or hidden state that affects reproducibility | Orchestrator |
| `providers.openai` and `providers.anthropic` | Server-side provider calls, timeout handling, raw response capture, provider metadata | Board resolution, opponent transcript access, browser exposure of tokens | Orchestrator, credential config |
| `persistence.repositories` | Loading/saving games, seats, turns, agent calls, transcripts, event/outbox records | Business decisions or provider calls | Orchestrator |
| `persistence.uow` | Transaction boundary and commit/rollback behavior | Long-running provider waits | Orchestrator, repositories |
| `events.bus` | Typed event publication and subscription for UI streams | Source-of-truth state | Orchestrator, API event endpoints |
| `api.routers` | HTTP routes, dependency injection, auth placeholder, request/response validation | Game rules, provider-specific branching, direct DB mutation | Application services |
| `frontend.api` | Typed REST/SSE client, error normalization | Secrets, rules authority, local board mutation as truth | FastAPI |
| `frontend.features.game` | New Game, Live Game, History, transcript and audit inspection | Provider credentials, authoritative state transitions | API client and event stream |

## Recommended Project Structure

```text
backend/
  app/
    main.py
    core/
      config.py
      logging.py
      ids.py
      time.py
    api/
      deps.py
      schemas/
        games.py
        providers.py
        events.py
        transcripts.py
      routers/
        games.py
        providers.py
        transcripts.py
        events.py
    domain/
      models.py
      errors.py
      board.py
      moves.py
    graygo/
      engine.py
      rules.py
      scoring.py
      board_key.py
      tests/
        test_resolution.py
        test_toroidal_liberties.py
        test_captures.py
        test_forbidden_points.py
        test_scoring.py
    application/
      orchestrator.py
      prompt_builder.py
      privacy_policy.py
      invalid_move_policy.py
      autorun.py
      locks.py
    ports/
      providers.py
      repositories.py
      events.py
      runtime.py
    providers/
      fake.py
      scripted.py
      openai_adapter.py
      anthropic_adapter.py
    persistence/
      database.py
      orm.py
      repositories.py
      uow.py
      migrations/
    events/
      schemas.py
      bus.py
      sse.py
    tests/
      application/
      api/
      persistence/

frontend/
  src/
    main.tsx
    app/
      App.tsx
      routes.tsx
    api/
      client.ts
      events.ts
      types.ts
    features/
      new-game/
      live-game/
      history/
      providers/
      settings/
    components/
      board/
        BoardGrid.tsx
        CellInspector.tsx
        ToroidalNeighbors.tsx
      transcript/
      controls/
    state/
      gameStore.ts
    styles/

docs/
  design.md
```

### Structure Rationale

- `backend/app/graygo/` stays importable without FastAPI or SQLAlchemy. This keeps the rule engine cheap to test and suitable for deterministic replay.
- `backend/app/application/` owns orchestration use cases. This is where simultaneous-turn fairness, game locks, invalid-output retry, and lifecycle state transitions belong.
- `backend/app/ports/` defines interfaces owned by the application layer. Concrete adapters implement those interfaces.
- `backend/app/providers/` contains concrete model-provider adapters. Provider differences are normalized before the orchestrator sees them.
- `backend/app/persistence/` owns database details behind repositories and a unit-of-work boundary. Route handlers should not import ORM models directly.
- `backend/app/events/` separates event schemas and transport from authoritative state. Events are notifications, not the source of truth.
- `frontend/src/features/` groups UI by workflow rather than by generic component type. Live match inspection, new game setup, and provider status will evolve independently.
- Do not create a shared runtime package between Python and TypeScript initially. Use OpenAPI-generated or hand-maintained client types after API schemas stabilize.

## Architectural Patterns

### Pattern 1: Pure Domain Engine

**What:** The engine is a deterministic function over explicit inputs.

```python
resolution = engine.resolve_turn(
    state=pre_turn_state,
    black_move=black_move,
    white_move=white_move,
)
```

**When to use:** Every rule operation, test fixture, replay, scoring calculation, and backend turn resolution.

**Trade-offs:** This forces more explicit data modeling up front, but prevents provider responses, route handlers, and UI state from becoming hidden rule dependencies.

### Pattern 2: Application Service Orchestration

**What:** Route handlers call a service method; the service coordinates repositories, engine, providers, and events.

```python
@router.post("/{game_id}/step")
async def step_game(
    game_id: str,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> GameView:
    return await orchestrator.step(game_id)
```

**When to use:** All game lifecycle commands. The API layer validates transport input and maps exceptions, but does not implement turn logic.

**Trade-offs:** Slightly more files than a script-style FastAPI app, but it keeps the core loop testable without an HTTP server.

### Pattern 3: Ports and Adapters for Providers

**What:** The orchestrator depends on a provider protocol, not on OpenAI, Anthropic, or CLI-specific code.

```python
class ProviderAdapter(Protocol):
    async def complete_move(self, request: MoveRequest) -> MoveResponse:
        ...
```

**When to use:** Fake agents, scripted agents, OpenAI direct API, Anthropic direct API, and future CLI adapters.

**Trade-offs:** The adapter boundary requires normalized response objects, but it makes fake-first development and same-model seat isolation practical.

### Pattern 4: Unit of Work for Turn Persistence

**What:** Database writes for a completed turn are committed atomically, while long provider waits happen outside the write transaction.

```text
short transaction:
  create turn as agent_thinking
  commit

provider calls:
  call Black and White concurrently
  parse and validate
  resolve through engine

short transaction:
  save agent calls
  save resolution
  update game current state if pre BoardKey still matches
  commit
```

**When to use:** Every turn, retry, failure transition, and game lifecycle state change.

**Trade-offs:** The orchestrator needs explicit status transitions, but this avoids holding SQLite write locks while waiting for slow providers.

### Pattern 5: Typed Event Notifications

**What:** Events describe changes that have happened or provider activity that is in progress.

```text
agent_call_started
agent_call_finished
turn_validation_failed
turn_resolved
game_status_changed
game_finished
```

**When to use:** Live Game UI updates, provider call spinners, transcript refresh, and history panes.

**Trade-offs:** The UI must tolerate missed events by refetching the current game state. That is acceptable and desirable because events are not authoritative storage.

## Key Data Flow: One Simultaneous Turn

This flow is the central architecture contract. Keep it stable.

```text
1. UI sends POST /api/games/{game_id}/step
2. API calls GameOrchestrator.step(game_id)
3. Orchestrator acquires a per-game step lock
4. Repository loads current game and both seat sessions
5. Orchestrator snapshots:
     pre_board
     pre_board_key
     current_turn
     forbidden points
     double_pass_count
     public resolved history
6. Engine computes legal moves for Black from the snapshot
7. Engine computes legal moves for White from the same snapshot
8. Repository creates a turn row with status agent_thinking and commits
9. Prompt builder creates Black prompt:
     rules
     same pre_board
     same pre_board_key
     Black legal moves
     public history
     Black private history only
10. Prompt builder creates White prompt:
     rules
     same pre_board
     same pre_board_key
     White legal moves
     public history
     White private history only
11. Orchestrator publishes agent_call_started for both seats
12. Provider calls run concurrently:
     black_task = call(black_session, black_prompt)
     white_task = call(white_session, white_prompt)
13. Adapter returns raw response and provider metadata for each seat
14. Pydantic validates structured JSON for each response
15. Server validates:
     returned board_key equals pre_board_key
     move is syntactically valid
     move is legal for that seat
     PASS is allowed only according to rules
16. If invalid, retry that seat once with:
     same pre_board
     same pre_board_key
     same legal moves
     validation error summary
17. If still invalid, apply configured invalid_move_policy
18. Engine resolves both final moves simultaneously from the original snapshot
19. Repository opens a short transaction
20. Repository verifies game still matches expected current_turn and pre_board_key
21. Repository saves agent_calls, parsed moves, validation audit, resolution, post_board, post_board_key, captures, forbidden updates
22. Repository updates games.current_board and lifecycle status
23. Transaction commits
24. Event bus publishes turn_resolved or game_finished
25. API returns fresh GameView
26. UI updates from response and/or SSE event; on disconnect it refetches GET /api/games/{game_id}
```

### Why This Preserves Fairness

```text
pre_board S
  |
  +--> Black prompt: S + Black private context + public history
  |
  +--> White prompt: S + White private context + public history

Black pending move and White pending move do not enter either prompt.

validated Black move + validated White move
  |
  v
engine.resolve_turn(S, black_move, white_move)
  |
  v
post_board S'
```

The prompt builder must not read the opponent's private transcript for the current seat. The orchestrator must not sequentially call Black, append Black's pending move to public history, then call White. Public history advances only after the simultaneous resolution commits.

## Persistence Flow

Use two styles of persistence records:

1. Current-state records for fast UI loading: `games`, `seat_sessions`.
2. Append-style audit records for replay and inspection: `turns`, `agent_calls`, optional `events` or `outbox`.

Recommended transaction boundaries:

```text
create game:
  insert game
  insert black seat_session
  insert white seat_session
  commit

begin step:
  insert turn(status=agent_thinking, pre_board, pre_board_key)
  commit

complete step:
  insert/update agent_calls
  update turn(status=resolved or failed)
  update game(current_board, current_turn, status)
  optionally insert event/outbox rows
  commit

publish events:
  after commit, publish from committed state
```

Do not hold a database transaction open while waiting on provider APIs. SQLite permits a simple local-first implementation, but long write transactions will quickly cause lock contention and make the UI feel unreliable.

## Event Flow

```text
Orchestrator
  |
  | publish typed event after meaningful state transition
  v
EventBus
  |
  +--> in-memory subscriber queues for connected SSE clients
  |
  +--> optional persisted outbox row for replay/debug later
  |
  v
GET /api/games/{game_id}/events
  |
  v
Browser EventSource
```

Recommended v1 event payloads:

| Event | Timing | Payload should include |
|-------|--------|------------------------|
| `game_created` | After game commit | `game_id`, initial board, seat summaries |
| `game_status_changed` | After lifecycle commit | `game_id`, previous status, next status |
| `agent_call_started` | Before provider call | `game_id`, `turn_index`, `color`, provider alias/model |
| `agent_call_finished` | After provider call result is stored or staged | `game_id`, `turn_index`, `color`, success/failure metadata |
| `turn_validation_failed` | After malformed or illegal output | `game_id`, `turn_index`, `color`, retryable flag, public-safe error |
| `turn_resolved` | After turn commit | `game_id`, `turn_index`, moves, post BoardKey, highlights |
| `game_finished` | After terminal commit | `game_id`, result, score |

For v1, the frontend should treat any event as a hint to update local state and should be able to recover by fetching `GET /api/games/{game_id}` and `GET /api/games/{game_id}/turns`.

## API Boundary

Recommended API surface:

| Route | Responsibility | Notes |
|-------|----------------|-------|
| `GET /api/providers` | Return configured provider aliases and model descriptors | Never expose token values. |
| `POST /api/providers/test` | Test a configured alias/model with a tiny backend call | Store test result only if useful for diagnostics. |
| `POST /api/games` | Create game and two isolated seat sessions | Same provider/model for both seats is valid. |
| `GET /api/games/{game_id}` | Return current authoritative game view | Used for reconnect recovery. |
| `POST /api/games/{game_id}/step` | Run exactly one simultaneous turn | Idempotency guard should prevent overlapping steps. |
| `POST /api/games/{game_id}/start` | Mark game running or start autorun depending request | Do not run hidden turns without visible status. |
| `POST /api/games/{game_id}/pause` | Stop autorun after current safe boundary | Do not interrupt engine resolution mid-commit. |
| `POST /api/games/{game_id}/stop` | Terminal operator stop | Store final status. |
| `POST /api/games/{game_id}/autorun` | Start managed per-game loop | Return immediately with status. |
| `GET /api/games/{game_id}/events` | SSE stream | One-way backend events. |
| `GET /api/games/{game_id}/turns` | Turn list | Public audit by default. |
| `GET /api/games/{game_id}/turns/{turn_index}` | Turn details | Include optional debug/private sections only for trusted local operator. |
| `GET /api/games/{game_id}/transcript?view=...` | Public, seat-private, or debug transcript | Backend controls view filtering. |

## Frontend State Flow

```text
New Game form
  |
  | POST /api/games
  v
Live Game route
  |
  +--> GET /api/games/{id}
  +--> GET /api/games/{id}/turns
  +--> EventSource /api/games/{id}/events
  |
  v
Local UI state
  |
  +--> board grid from backend board only
  +--> highlights from last turn resolution
  +--> panels from safe seat summaries
  +--> transcript/debug panes from explicit backend views
```

Frontend state should distinguish:

- `authoritativeGame`: last full game view fetched from backend.
- `liveEvents`: transient event feed for spinners and recent updates.
- `draftNewGameConfig`: form state not yet submitted.
- `selectedTurnIndex`: inspection cursor.
- `visibilitySettings`: operator UI preferences for raw JSON, summaries, and audits.

Do not model local board mutation as a reducer that applies game rules in the browser. The UI may derive visual highlights, but board contents come from backend state.

## Integration Points

### External Services

| Service | Integration pattern | Architecture notes |
|---------|---------------------|--------------------|
| OpenAI direct API | `ProviderAdapter.complete_move` with server-side credential alias | Use structured output when available, store raw response and parsed JSON by seat. Do not share response chain between seats. |
| Anthropic direct API | `ProviderAdapter.complete_move` with server-side credential alias | Maintain separate message/history arrays by seat. Validate JSON server-side. |
| Fake random agent | Provider adapter with random legal move selection | Use for cheap smoke tests, but seed randomness for reproducibility where needed. |
| Scripted agent | Provider adapter that consumes a configured move list | Use for deterministic engine/orchestrator tests and UI demos. |
| SQLite | SQLAlchemy repository implementation | Suitable for local-first v1; avoid long write transactions around provider calls. |
| SSE | FastAPI streaming endpoint over event bus | Good first live-update transport because UI commands remain REST. |
| WebSocket | Optional later event/control channel | Add only if REST plus SSE becomes awkward. |

### Internal Boundaries

| Boundary | Communication | Contract |
|----------|---------------|----------|
| API to application | Method calls with Pydantic request/response DTOs | API maps HTTP to use cases; no rule logic in routes. |
| Application to engine | Pure function calls with domain objects | Engine returns resolution, never persists. |
| Application to providers | Adapter protocol | Providers return normalized `MoveResponse` with raw response metadata. |
| Application to persistence | Repository plus unit of work | Application owns transaction timing, repository owns SQL/ORM details. |
| Application to events | Typed publish calls | Events emitted after state transition or provider activity. |
| Frontend to backend | REST plus SSE | Browser never receives secrets or private opponent data unless using explicit trusted transcript views. |

## Build Order Implications

The roadmap should follow dependency order, not UI order.

### Phase 1: Deterministic Rule Core

Build:

- Domain types for board, coordinate, move, seat color, BoardKey, game state.
- Pure engine for legal moves, simultaneous placement, gray collision, toroidal liberties, two-stage capture, forbidden points, pass handling, scoring.
- Dense unit tests and replay fixtures.

Why first:

- Every later phase depends on engine correctness.
- Fake agents and UI are only useful if backend resolution is trusted.
- Rule bugs are cheaper to fix before persistence and transcripts depend on their shape.

### Phase 2: Contracts and In-Memory Turn Orchestrator

Build:

- `ProviderAdapter`, `GameRepository`, `EventBus`, and `UnitOfWork` protocols.
- Fake and scripted providers.
- In-memory repository.
- `GameOrchestrator.step()` with per-game lock, same-snapshot prompt construction, concurrent provider calls, validation, retry-once policy, engine resolution, and typed event publication.

Why second:

- This proves simultaneous-turn fairness before database or frontend complexity.
- It establishes seat isolation as a runtime invariant, not a later patch.

### Phase 3: FastAPI API Shell

Build:

- Provider discovery endpoint returning aliases only.
- Game create/get/step/lifecycle endpoints.
- Pydantic schemas for public game views, turns, provider descriptors, and errors.
- Basic SSE endpoint over in-memory event bus.

Why third:

- Gives the frontend a stable backend contract.
- Keeps route handlers thin while orchestrator behavior is still easy to test directly.

### Phase 4: React/Vite Manual Game UI

Build:

- New Game screen for fake/scripted providers.
- Live Game board rendering from backend state.
- Manual Step/Run/Pause controls wired to REST.
- SSE event connection for spinners and turn updates.
- Basic turn history and cell inspection.

Why fourth:

- Provides end-to-end feedback without paid providers.
- Reveals whether API response shapes support real inspection workflows.

### Phase 5: SQLite Persistence and Replay

Build:

- SQLAlchemy models/repositories for games, seat sessions, turns, agent calls, transcripts.
- Transaction boundaries around begin-step and complete-step.
- Replay/debug queries from persisted turns.
- Migration setup.

Why before real providers:

- Real provider failures and malformed outputs need durable audit records.
- Paid calls should not be spent before prompts, responses, validation, and outcomes are inspectable.

### Phase 6: Real Direct Provider Adapters

Build:

- OpenAI direct adapter.
- Anthropic direct adapter.
- Provider test endpoint against real configured aliases.
- Strict output validation, timeout handling, retry-once behavior, token/latency metadata.

Why after persistence:

- Direct providers introduce cost, latency, malformed outputs, and operational failures.
- Durable `agent_calls` records become essential at this point.

### Phase 7: Autorun, Transcripts, and Inspection Hardening

Build:

- Managed per-game autorun task registry with cancellation.
- Transcript views: public, Black private, White private, debug.
- Raw response toggles and backend validation audit.
- Export/replay helpers.

Why after single-step is stable:

- Autorun multiplies the blast radius of turn bugs.
- Transcript privacy rules are easier to validate after seat-scoped storage exists.

### Phase 8: Scaling and Optional Adapters

Build only when needed:

- PostgreSQL repository.
- Durable outbox and Redis/pubsub or queue-based event fanout.
- WebSocket transport if bidirectional realtime becomes necessary.
- CLI adapters for Claude Code/Codex with per-seat working/config directories.

Why last:

- CLI adapters and horizontal scaling add operational complexity unrelated to proving the core product.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Model-Authored Board Updates

**What people do:** Ask models to return the next board or capture result.

**Why it is wrong:** Models will eventually make illegal or inconsistent rule updates, and those mistakes will contaminate persistence and UI state.

**Do this instead:** Models return only structured move proposals. The backend validates and resolves all board changes.

### Anti-Pattern 2: Shared Seat Context

**What people do:** Use one provider conversation, message array, response chain, or CLI home directory for both Black and White because they share provider/model settings.

**Why it is wrong:** Same-model matches can leak private strategy, raw output, or cached session state across seats.

**Do this instead:** Create separate `seat_sessions` and provider session references per color for every game.

### Anti-Pattern 3: Sequential Prompt Contamination

**What people do:** Call Black first, store Black's pending move in public history, then call White for the same turn.

**Why it is wrong:** White can see information Black did not have, breaking simultaneous-turn fairness.

**Do this instead:** Build both prompts from the same pre-turn snapshot and dispatch calls concurrently or from prebuilt prompts.

### Anti-Pattern 4: Long DB Transaction Around Provider Calls

**What people do:** Open a transaction, call both providers, then commit after network calls return.

**Why it is wrong:** Provider latency can hold SQLite write locks and make concurrent UI/API operations unreliable.

**Do this instead:** Commit an `agent_thinking` turn record, call providers outside the write transaction, then commit resolution in a short transaction with a BoardKey/current_turn guard.

### Anti-Pattern 5: Events as Source of Truth

**What people do:** Let the frontend reconstruct game state only from an event stream.

**Why it is wrong:** Browser reconnects, missed events, and future multi-process deployments will create inconsistent views.

**Do this instead:** Persist authoritative state and use events as invalidation/update hints. The UI can always refetch current game and turns.

### Anti-Pattern 6: Provider Logic in Route Handlers

**What people do:** Put OpenAI/Anthropic branching, prompt construction, retries, and validation directly in FastAPI endpoints.

**Why it is wrong:** It couples transport to game behavior and makes fairness/privacy hard to test without HTTP.

**Do this instead:** Routes call application services. Application services call provider adapters.

### Anti-Pattern 7: Browser-Visible Secrets

**What people do:** Put API tokens in Vite env vars or ask the user to paste provider keys into the SPA.

**Why it is wrong:** Vite exposes client-prefixed env vars to browser code, and browser code cannot protect provider secrets.

**Do this instead:** Store credentials in backend config and expose only safe aliases and configured status.

### Anti-Pattern 8: Fire-and-Forget Autorun

**What people do:** Start background turns without a tracked task, cancellation path, or persisted status.

**Why it is wrong:** The operator cannot reliably pause/stop, and failures become invisible.

**Do this instead:** Use an autorun manager with a per-game task registry, cancellation tokens, status updates, and a safe boundary after each committed turn.

## Scaling Considerations

| Scale | Recommended architecture | What breaks first |
|-------|--------------------------|-------------------|
| Local single operator, one or few games | Single FastAPI process, SQLite, in-memory event bus, fake/scripted plus direct providers | Provider latency and rule bugs, not infrastructure. |
| Dozens of concurrent games on one machine | Keep modular monolith, add provider concurrency limits, timeouts, better task registry, SQLite tuning or PostgreSQL | SQLite write contention, provider rate limits, event queue memory. |
| Multiple backend workers or remote users | PostgreSQL, durable locks or job queue, durable outbox, shared pub/sub for events, auth | In-memory locks and event bus no longer work across workers. |
| Hosted multi-user product | Split auth/tenant concerns, stronger secret management, audit retention policy, provider quota controls | Privacy/security boundaries, cost controls, multi-tenant data isolation. |

### Practical v1 Scaling Rules

- Run one backend worker while using in-memory per-game locks and in-memory SSE subscriptions.
- Add provider call timeouts and per-provider concurrency limits before adding more providers.
- Move from SQLite to PostgreSQL before supporting many concurrent autoruns or multiple backend processes.
- Add a durable outbox before relying on events for anything beyond live UI hints.
- Keep the engine pure even if the rest of the backend later splits into workers.

## Completion Checklist for Architecture Review

- Engine can be imported and tested without FastAPI, SQLAlchemy, provider SDKs, or frontend code.
- `GameOrchestrator.step()` can be tested with fake providers and in-memory repositories.
- Prompt builder has tests proving opponent private data is excluded.
- Same-provider same-model Black/White configuration creates two distinct seat sessions.
- A simultaneous turn has one pre BoardKey and two prompts derived from that same snapshot.
- Invalid output handling stores raw output, validation error, retry result, and final policy action.
- UI board rendering uses backend board state only.
- SSE disconnect recovery works by refetching current game and turn history.

## Sources

- `/Users/gcao/proj/graygo-arena/.planning/PROJECT.md` - project requirements and constraints. Confidence: HIGH.
- `/Users/gcao/proj/graygo-arena/docs/design.md` - original product architecture, API sketch, data model, prompt policy, and build order. Confidence: HIGH.
- `/Users/gcao/.codex/get-shit-done/templates/research-project/ARCHITECTURE.md` - required research artifact structure. Confidence: HIGH.
- FastAPI bigger applications and APIRouter documentation: https://fastapi.tiangolo.com/tutorial/bigger-applications/ and Context7 `/websites/fastapi_tiangolo`. Confidence: HIGH.
- FastAPI WebSocket and streaming response documentation: https://fastapi.tiangolo.com/advanced/websockets/ and https://fastapi.tiangolo.com/advanced/custom-response/. Confidence: HIGH.
- FastAPI background task documentation: https://fastapi.tiangolo.com/tutorial/background-tasks/. Confidence: HIGH.
- SQLAlchemy 2.0 session transaction documentation: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html. Confidence: HIGH.
- Pydantic validation documentation: https://docs.pydantic.dev/latest/concepts/models/ and Context7 `/pydantic/pydantic`. Confidence: HIGH.
- Vite environment variable documentation: https://vite.dev/guide/env-and-mode. Confidence: HIGH.

---
*Architecture research for Gray Go Arena.*
