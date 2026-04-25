# Phase 2 Research: Fair Orchestrator, API & Persistence

**Researched:** 2026-04-25
**Confidence:** High for fake/scripted orchestration and local SQLite, medium for future provider details.

## Scope

Phase 2 should build a backend loop that proves fairness and auditability without paid model calls:

1. Create games with isolated Black/White seat sessions.
2. Prompt both seats from the same authoritative pre-turn BoardKey.
3. Use fake/scripted adapters to return candidate moves.
4. Validate BoardKey and moves server-side.
5. Resolve through the pure engine only.
6. Persist game, turn, agent-call, transcript, and event records in SQLite.
7. Expose typed REST endpoints and an SSE event shell.

## Implementation Shape

Use the existing `graygo_arena` package and add IO code outside `graygo_arena.engine`:

```text
src/graygo_arena/
  api/
    schemas.py
    routes.py
  application/
    orchestrator.py
    prompt_builder.py
  events/
    bus.py
  persistence/
    database.py
    repositories.py
  providers/
    base.py
    fake.py
  main.py
```

The engine import-boundary guard already protects `graygo_arena.engine`; Phase 2 can import FastAPI/Pydantic in API modules.

## SQLite Strategy

Use a small stdlib SQLite repository for Phase 2:

- One local database path from settings, defaulting to `.runtime/graygo.db`.
- Tables: `games`, `seat_sessions`, `turns`, `agent_calls`, `events`, and `seat_transcripts`.
- Store board keys, move labels, JSON request/response payloads, and transcript text as text/JSON strings.
- Store credential refs only, never secret values.
- Use a repository lock around writes; later phases can replace this with SQLAlchemy if needed.

## Orchestrator Strategy

Use one process-local lock per game for Phase 2 fairness. The lock prevents overlapping `step` calls in a single-process local server. Future hosted/horizontal deployments will need database advisory locks or queueing, but that is outside v1 local-first scope.

Turn flow:

1. Load game and seats.
2. Refuse step unless status is `created` or `running`.
3. Capture one pre-board snapshot and BoardKey.
4. Build Black and White move requests from the same snapshot.
5. Call each provider adapter without opponent pending move context.
6. Validate provider BoardKey echo and parsed move against legal moves.
7. Retry invalid output once.
8. Apply invalid policy. Phase 2 default: force `PASS`.
9. Resolve with `resolve_turn`.
10. Persist turn, agent calls, transcripts, events, and updated game.

## API Surface

Minimum REST endpoints:

- `GET /api/providers`
- `POST /api/providers/test`
- `POST /api/games`
- `GET /api/games/{game_id}`
- `POST /api/games/{game_id}/start`
- `POST /api/games/{game_id}/pause`
- `POST /api/games/{game_id}/resume`
- `POST /api/games/{game_id}/stop`
- `POST /api/games/{game_id}/step`
- `POST /api/games/{game_id}/autorun`
- `GET /api/games/{game_id}/turns`
- `GET /api/games/{game_id}/turns/{turn_index}`
- `GET /api/games/{game_id}/transcript?view=public|black_private|white_private|debug`
- `GET /api/games/{game_id}/events`

## Risks

| Risk | Response |
|------|----------|
| Orchestrator accidentally mutates board without engine | Keep all board updates behind `resolve_turn`; test with scripted collisions/captures. |
| Same model/provider seats share state | Persist one seat row per color and assert distinct IDs in tests. |
| SQLite records are too thin for later UI | Store pre/post BoardKeys, moves, resolution events, calls, public logs, private transcripts. |
| SSE becomes source of truth | Persist events first; SSE only streams persisted event records. |
| Future real providers change APIs | Keep fake provider interface project-owned and narrow; Phase 4 can adapt SDK details behind it. |

## Verification

Phase 2 should pass:

```bash
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Add tests for:

- same-snapshot prompt requests for both seats
- distinct seat session IDs for same-provider games
- scripted step resolution
- invalid retry then forced `PASS`
- provider discovery/test metadata without secrets
- SQLite persistence of game/turn/agent-call/transcript/event records
- REST create/step/get/turn/transcript endpoints

---

*Research completed: 2026-04-25*
