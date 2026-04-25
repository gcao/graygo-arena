# Stack Research

**Domain:** Local-first AI-vs-AI deterministic board game arena
**Project:** Gray Go Arena
**Researched:** 2026-04-25
**Confidence:** HIGH for framework/package choices and registry versions; MEDIUM for future provider/model details because provider APIs and model IDs change quickly.

## Recommendation

Use a split stack: a Python/FastAPI backend owns all rules, state, persistence, credentials, provider calls, transcripts, and event broadcasting; a React/TypeScript/Vite SPA handles only configuration, visualization, controls, and transcript inspection. Do not put provider credentials, move validation, board mutation, or seat-private transcript state in the browser.

The backend should stay deliberately boring: deterministic pure-Python game engine, FastAPI boundary models, SQLAlchemy 2.x persistence over SQLite, direct OpenAI/Anthropic SDK adapters, and SSE for live updates. Avoid agent frameworks in v1. This product's hard problems are simultaneity, deterministic rule resolution, auditability, and seat isolation, not generic multi-agent orchestration.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.14.4 | Backend runtime and deterministic engine | Python matches the existing design assumption, is strong for rule engines/tests, and current FastAPI requires Python `>=3.10`. Use Python 3.14 for a greenfield 2026 codebase; do not start new work on 3.11/3.12 unless deployment constraints force it. |
| uv | 0.11.7 | Python dependency, lockfile, and virtualenv manager | Fast, reproducible project/dependency management with a lockfile. Prefer `uv` over Poetry/Pipenv for a new local-first project because it keeps setup and CI commands short. |
| FastAPI | 0.136.1 | Backend REST API and WebSocket support | Best fit for typed Python APIs with automatic OpenAPI generation and Pydantic validation. It keeps the backend as the trusted arbiter while giving the frontend typed API contracts. |
| Pydantic | 2.13.3 | API schemas, provider move-output validation, config typing | Use Pydantic at trust boundaries: REST request/response DTOs, provider JSON move output, settings. Keep the engine itself as pure Python dataclasses/enums so rules remain deterministic and not coupled to API serialization. |
| Pydantic Settings | 2.14.0 | Backend-only configuration and secret aliases | Centralizes env-driven provider credentials while exposing only configured aliases through the API. This directly supports the design constraint that credentials never reach the SPA. |
| SQLAlchemy | 2.0.49 | Persistence mapping and transactions | Use SQLAlchemy 2.x ORM/Core instead of SQLModel. It gives explicit control over transactions, migrations, JSON columns, indexes, and future PostgreSQL migration without coupling persistence models to API schemas. |
| SQLite | Bundled engine via Python `sqlite3`; no app-level package pin | Local persistence | Use SQLite for v1 because this is local-first and single-operator. Enable WAL, foreign keys, and `busy_timeout`; design schema with PostgreSQL-compatible types where possible. |
| aiosqlite | 0.22.1 | Async SQLite driver for SQLAlchemy | Use `sqlite+aiosqlite` with SQLAlchemy async sessions because the app will already have async provider calls and SSE streams. Create one `AsyncSession` per request/turn; never share a session across concurrent seat tasks. |
| Alembic | 1.18.4 | Database migrations | Required even for local SQLite because games, transcripts, board snapshots, and provider calls will evolve quickly. |
| Uvicorn | 0.46.0 | ASGI dev/prod server | Standard FastAPI runtime. Use `uvicorn[standard]` for local serving and websocket dependencies. |
| React | 19.2.5 | SPA UI framework | Standard choice for an interactive board, controls, live event stream rendering, and transcript panes. React 19 is current and works with the Vite React TypeScript template. |
| TypeScript | 6.0.3 | Frontend type system | Strongly type API payloads, board state rendering, event payloads, and UI state. Generate API types from FastAPI OpenAPI rather than duplicating contracts by hand. |
| Vite | 8.0.10 | Frontend build/dev server | Fast local SPA development. Vite 8 officially requires Node `^20.19.0 || >=22.12.0`; Node 24 LTS satisfies this. |
| @vitejs/plugin-react | 6.0.1 | React integration for Vite | Use with Vite 8. The v6 plugin is the matching current generation and removes older Babel-default assumptions unless React Compiler support is explicitly opted in. |
| Node.js | 24.15.0 LTS | Frontend runtime/toolchain | Node 24 LTS is the conservative 2026 runtime choice. Avoid Node 25/26 current releases for this project unless a tool requires them. |
| npm | 11.x | Frontend package manager | Good default with Node 24; Node 24.15.0 bundles npm 11.12.1, while the npm registry latest queried was 11.13.0. Do not add pnpm/yarn unless the repo already standardizes on them. |

### Backend Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sse-starlette | 3.3.4 | Server-Sent Events from FastAPI/Starlette | Use for live game updates first. REST controls game actions, so SSE is simpler than WebSocket for one-way board/turn/event streaming and supports browser reconnection via `EventSource`. |
| websockets | 16.0 | WebSocket runtime support, usually through `uvicorn[standard]` | Keep available for future bidirectional live controls, but do not make WebSocket the default v1 event path. |
| httpx | 0.28.1 | Async HTTP client | Use for provider health checks or adapters that need direct HTTP calls. The official OpenAI/Anthropic SDKs can remain the primary provider clients. |
| openai | 2.32.0 | OpenAI direct API adapter | Use direct SDK calls from backend-only seat sessions. Prefer Responses API with structured outputs where available. Persist provider request/response metadata per seat; never share `previous_response_id` or conversation state between Black and White. |
| anthropic | 0.97.0 | Anthropic direct API adapter | Use direct Messages API calls from backend-only seat sessions. Persist separate `messages` histories per seat; validate returned move JSON server-side and retry once on malformed/illegal output. |
| orjson | 3.11.8 | Fast JSON serialization | Use only if profiling or large transcript/turn-history responses justify it. Pydantic/FastAPI work without it, so keep it as a pragmatic optimization rather than a core design dependency. |
| python-dotenv | 1.2.2 | Local env loading | Use only for local developer convenience. Production-like secret handling should still read backend environment variables and expose only aliases to the UI. |

### Frontend Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-dom | 19.2.5 | React browser renderer | Required with React. Keep `react` and `react-dom` versions identical. |
| react-router | 7.14.2 | SPA routing | Use for New Game, Live Game, Game History, Provider Status, and Settings routes. |
| @tanstack/react-query | 5.100.1 | Server-state cache and request lifecycle | Use for REST reads/mutations, provider tests, game history, and transcript fetching. It prevents hand-rolled loading/error/cache state across the SPA. |
| openapi-typescript | 7.13.0 | Generate TypeScript types from FastAPI OpenAPI | Use in CI/dev scripts so frontend API types track backend contracts. |
| openapi-fetch | 0.17.0 | Typed fetch client over generated OpenAPI paths | Use for REST calls. Keep live event parsing separate because SSE event streams are not ordinary request/response endpoints. |
| zod | 4.3.6 | Runtime validation in the browser | Use for SSE event payload parsing and defensive UI boundary checks. Do not use it as the primary backend validation source; backend Pydantic schemas remain authoritative. |

### Testing and Quality Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| pytest | 9.0.3 | Backend test runner | Main backend test surface. |
| pytest-asyncio | 1.3.0 | Async backend tests | Use for FastAPI endpoints, orchestrator turns, provider adapter fakes, and SSE behavior. |
| hypothesis | 6.152.2 | Property-based engine tests | Critical for toroidal neighbors, liberties, simultaneous collision resolution, captures, forbidden points, pass handling, scoring invariants, and BoardKey stability. |
| respx | 0.23.1 | Mock HTTPX provider calls | Use for adapter tests when direct HTTP mocking is needed. For official SDKs, wrap provider clients behind a narrow project interface and test against fake adapters first. |
| ruff | 0.15.12 | Python lint and format | Use `ruff check` and `ruff format`; avoid adding Black/isort/flake8 separately. |
| pyright | 1.1.409 | Python static type checking | Recommended over mypy for this project because it is fast, strict enough, and pairs well with dataclass-heavy engine code. |
| Vitest | 4.1.5 | Frontend unit/component tests | Use for board rendering, API client helpers, event reducers, and route-level behavior. |
| @testing-library/react | 16.3.2 | React component testing | Use for user-observable UI tests rather than component internals. |
| @testing-library/user-event | 14.6.1 | Browser-like user interactions in tests | Use for controls, settings forms, transcript filters, board cell inspection. |
| jsdom | 29.0.2 | DOM environment for Vitest | Standard test environment for React components. |
| Playwright | 1.59.1 | End-to-end browser tests | Use for New Game -> step game -> live board update -> transcript inspection workflows. |
| ESLint | 10.2.1 | Frontend linting | Use with TypeScript ESLint. |
| typescript-eslint | 8.59.0 | TypeScript lint integration | Keep rules focused; avoid noisy stylistic rules covered by Prettier. |
| Prettier | 3.8.3 | Frontend formatting | Use for TS/TSX/CSS/JSON/Markdown. Let Ruff own Python formatting. |

## Installation

Recommended repository layout:

```text
backend/
  pyproject.toml
  src/graygo_arena/
frontend/
  package.json
  src/
```

Backend:

```bash
cd backend
uv init --package --python 3.14
uv add fastapi==0.136.1 "uvicorn[standard]==0.46.0" pydantic==2.13.3 pydantic-settings==2.14.0 SQLAlchemy==2.0.49 alembic==1.18.4 aiosqlite==0.22.1 sse-starlette==3.3.4 httpx==0.28.1 openai==2.32.0 anthropic==0.97.0
uv add --optional perf orjson==3.11.8
uv add --dev pytest==9.0.3 pytest-asyncio==1.3.0 hypothesis==6.152.2 respx==0.23.1 ruff==0.15.12 pyright==1.1.409
```

Frontend:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react@19.2.5 react-dom@19.2.5 react-router@7.14.2 @tanstack/react-query@5.100.1 openapi-fetch@0.17.0 zod@4.3.6
npm install -D typescript@6.0.3 vite@8.0.10 @vitejs/plugin-react@6.0.1 @types/react@19.2.14 @types/react-dom@19.2.3 @types/node@24.12.2 vitest@4.1.5 @testing-library/react@16.3.2 @testing-library/user-event@14.6.1 jsdom@29.0.2 playwright@1.59.1 eslint@10.2.1 typescript-eslint@8.59.0 prettier@3.8.3 openapi-typescript@7.13.0
```

## Backend Architecture Notes

### Deterministic Engine

Use stdlib-first Python:

| Concern | Recommendation |
|---------|----------------|
| Board/cell types | `enum.StrEnum`, frozen dataclasses, tuples, and small value objects |
| BoardKey | `hashlib.blake2s` or `hashlib.sha256` over a canonical byte/string representation |
| Random fake agents | `random.Random(seed)` injected per fake/scripted seat |
| Time | Store UTC timestamps at persistence/API boundaries; do not let engine logic depend on wall-clock time |
| Serialization | Convert through explicit DTOs; do not let ORM models become game-engine objects |

Do not use a game-engine framework for Gray Go. The rules are domain-specific, deterministic, and small enough that introducing a generic engine would make rule audit harder.

### Persistence

Use SQLAlchemy async with `sqlite+aiosqlite:///...`.

Prescriptive SQLite settings:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
```

Data model direction:

| Table | Purpose |
|-------|---------|
| `games` | Board size, ruleset, lifecycle state, configured seats, max turns |
| `seat_sessions` | One row per game seat; provider alias/model/session metadata, no secret values |
| `turns` | Turn number, pre-board key, submitted moves, validation outcome, resolution summary |
| `boards` | Canonical board snapshots or compact encoded state after each turn |
| `ai_calls` | Provider request/response metadata, latency, token counts, retry status |
| `seat_transcripts` | Private per-seat prompt/response/history records |
| `public_events` | Sanitized audit/event stream visible to the operator |

One turn should be one durable transaction: validate both moves, resolve, persist board/turn/transcripts/audit, then broadcast. Do not broadcast a state update that is not durably persisted.

### Live Updates

Use SSE first:

```text
REST command -> orchestrator step transaction -> event bus append -> SSE broadcast
```

SSE event types:

| Event | Purpose |
|-------|---------|
| `game.created` | New game available |
| `game.status_changed` | started, paused, stopped, completed |
| `turn.started` | Both seats are being called from the same pre-board |
| `turn.resolved` | Moves, captures, collisions, post-board, BoardKey |
| `turn.invalid` | Malformed/illegal move and policy result |
| `provider.call_started` | Safe provider alias/model metadata only |
| `provider.call_finished` | Latency, token usage, status, no secret values |

Use WebSocket later only if the UI needs low-latency bidirectional controls beyond REST.

### Provider Adapters

Define a narrow project-owned interface:

```python
class ProviderSeatAdapter(Protocol):
    async def request_move(self, request: MoveRequest) -> MoveResponse:
        ...
```

Adapters to build in order:

1. `fake_random` and deterministic scripted adapters.
2. OpenAI direct SDK adapter.
3. Anthropic direct SDK adapter.
4. CLI/OAuth adapters only after direct APIs are stable.

Adapter rules:

| Rule | Reason |
|------|--------|
| Backend-only credentials | Browser must never receive provider tokens. |
| One seat session per color | Same provider/model matches must not leak state between Black and White. |
| Persist provider alias, not secret value | Enables audit without credential exposure. |
| Validate JSON move output with Pydantic | Provider text is untrusted input. |
| Retry malformed/illegal output once | Gives models a chance to self-correct without making rule enforcement probabilistic. |
| Store raw response privately per seat | Enables audit while preventing opponent prompt contamination. |

## Frontend Architecture Notes

Use the SPA as a typed client of backend-owned truth:

| Concern | Recommendation |
|---------|----------------|
| Routes | React Router for New Game, Live Game, History, Provider Status, Settings |
| REST data | TanStack Query + openapi-fetch |
| Types | Generate from FastAPI OpenAPI with openapi-typescript |
| Live events | Native `EventSource`; validate event payloads with Zod |
| Board rendering | CSS grid or SVG, not canvas by default; add canvas only if board sizes/perf demand it |
| UI state | Local React state/reducers for transient controls; no Redux in v1 |

The frontend should never synthesize authoritative state. It may optimistically show "step requested" or "provider call running", but the board changes only after backend events or REST fetches return persisted state.

## Alternatives Considered

| Recommended | Alternative | Why Not / When to Use Alternative |
|-------------|-------------|-----------------------------------|
| FastAPI | Django | Django is stronger for admin/auth-heavy products. This is a local-first operator tool with typed APIs, live events, and deterministic services; FastAPI has less framework weight. |
| FastAPI | Flask | Flask is fine for small APIs, but FastAPI's Pydantic integration and OpenAPI generation are central to keeping the React client typed. |
| SQLAlchemy 2.x | SQLModel | SQLModel is convenient but blurs API schema and persistence shape. Gray Go needs explicit domain objects, audit tables, and future PostgreSQL migration. |
| SQLite first | PostgreSQL first | PostgreSQL is the right later production path. For v1, SQLite keeps local setup simple and matches the project constraint. Design schema so migration remains feasible. |
| SSE first | WebSocket first | WebSocket is useful for bidirectional realtime. This app's live updates are mostly server-to-browser; REST commands plus SSE is simpler, easier to reconnect, and easier to test. |
| Direct OpenAI/Anthropic SDKs | LangChain/LlamaIndex | Agent frameworks add abstraction and hidden state exactly where this product needs strict seat isolation and auditable prompts/responses. Use direct SDKs until there is a proven repeated abstraction need. |
| React SPA | Next.js/Remix | Server-rendering frameworks are unnecessary because the backend is FastAPI and the app is an operator console. Vite SPA is simpler and keeps credentials on the backend. |
| TanStack Query | Redux Toolkit Query | RTK Query is good when Redux is already part of the app. This project does not need a global Redux store for v1. |
| CSS/SVG board | Pixi/Konva/D3 | Those help for complex graphics. Gray Go boards and highlights should be inspectable, accessible, and testable with simple DOM/SVG first. |
| uv | Poetry/Pipenv | Poetry is viable but heavier. `uv` gives faster installs and simpler lockfile-driven workflows for a new Python service. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Browser-side OpenAI/Anthropic calls | Exposes credentials and breaks the backend-owned state/security model. | Backend provider adapters with safe provider aliases exposed to the UI. |
| Shared provider conversation/session for both seats | Same-model matches can leak private reasoning or prior responses across Black/White. | Separate `seat_sessions`, histories, response chains, and transcript rows per seat. |
| AI-authored board updates | Models will eventually make rule/state mistakes and can violate simultaneity. | AI returns only a candidate move; backend validates and resolves. |
| LangChain/LlamaIndex in v1 | Adds hidden state, complex abstractions, and adapter behavior that is hard to audit. | Small direct SDK adapters behind a project-owned protocol. |
| SQLModel as the core data layer | Conflates API DTOs and persistence, which makes audit/history schema changes harder. | SQLAlchemy 2.x models plus explicit Pydantic DTOs. |
| WebSocket-only live updates | More lifecycle complexity for one-way updates. | SSE first, WebSocket later only for true bidirectional needs. |
| Redux/global store for server truth | Risks duplicating backend state and stale board copies. | TanStack Query for server state and local React reducers for UI-only state. |
| Hardcoded current AI model IDs in source | Model availability changes quickly and differs by account/provider. | Backend-configured model aliases from env/config, surfaced safely through `/api/providers`. |
| Docker-first local workflow | Adds setup weight before the product needs deployment reproducibility. | Native `uv` + npm local workflow; add Docker when packaging matters. |

## Stack Patterns by Variant

**If running pure local development:**
- Use SQLite file storage under `.runtime/graygo.db`.
- Use fake/scripted agents by default.
- Load provider credentials from backend `.env`, not frontend `.env`.
- Run `uv run uvicorn graygo_arena.api.app:app --reload` and Vite separately.

**If adding paid provider adapters:**
- Keep provider clients behind the same `ProviderSeatAdapter` protocol.
- Add provider aliases in backend settings.
- Persist raw provider responses privately per seat.
- Add adapter contract tests using fake provider clients before making real paid calls.

**If transcript volume grows:**
- Keep SQLite for v1, but separate large raw payloads from hot game-state reads.
- Add indexes on `game_id`, `seat_session_id`, `turn_number`, and `created_at`.
- Revisit PostgreSQL when concurrent operators, remote hosting, or large transcript search becomes a real requirement.

**If live control gets more interactive:**
- Keep SSE for broadcast.
- Add one WebSocket endpoint only for bidirectional controls that cannot be modeled as REST commands.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastAPI 0.136.1 | Python `>=3.10`, Pydantic 2.x | PyPI metadata reports `Requires-Python >=3.10`; FastAPI docs use Pydantic models for request validation. |
| Pydantic 2.13.3 | Python `>=3.9` | Use v2 APIs only. Do not introduce Pydantic v1 compatibility shims. |
| SQLAlchemy 2.0.49 | aiosqlite 0.22.1 | SQLAlchemy docs show `create_async_engine("sqlite+aiosqlite:///filename")`; one `AsyncSession` is not safe for concurrent tasks. |
| Uvicorn 0.46.0 | FastAPI/Starlette ASGI | Use `uvicorn[standard]` so local WebSocket/SSE dependencies are present. |
| OpenAI SDK 2.32.0 | Python `>=3.9` | Use from backend only. Prefer structured output paths where available; keep model IDs config-driven. |
| Anthropic SDK 0.97.0 | Python `>=3.9` | Use from backend only. Store per-seat messages manually. |
| Vite 8.0.10 | Node `^20.19.0 || >=22.12.0` | Node 24 LTS satisfies this. |
| @vitejs/plugin-react 6.0.1 | Vite `^8.0.0` | Plugin peer dependencies require Vite 8. |
| React 19.2.5 | react-dom 19.2.5, @types/react 19.2.14 | Keep React packages on the same major/minor family. |
| @tanstack/react-query 5.100.1 | React `^18 || ^19` | Works with React 19. |
| @types/node 24.12.2 | Node 24.x LTS | Do not use latest `@types/node` 25.x with a Node 24 runtime. |
| Vitest 4.1.5 | Vite 6/7/8, Node 20/22/24 | Registry peer metadata includes Vite `^8.0.0`. |

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Backend framework stack | HIGH | FastAPI/Pydantic/SQLAlchemy versions verified from PyPI and docs; architecture matches project constraints. |
| SQLite approach | HIGH | SQLite is explicitly required for v1; WAL/foreign key/busy timeout settings are standard official SQLite features. |
| Frontend stack | HIGH | React/Vite/TypeScript versions verified from npm; Vite/React setup checked against docs. |
| OpenAI/Anthropic SDK versions | HIGH for package versions, MEDIUM for model/API behavior | Versions verified from PyPI and official docs consulted; provider model IDs and API defaults change frequently, so keep aliases configurable. |
| Testing stack | HIGH | Current versions verified from registries; Hypothesis is specifically valuable for deterministic game-rule invariants. |

## Sources

- Project context: `/Users/gcao/proj/graygo-arena/.planning/PROJECT.md` and `/Users/gcao/proj/graygo-arena/docs/design.md`.
- PyPI registry, queried 2026-04-25: `fastapi 0.136.1`, `pydantic 2.13.3`, `pydantic-settings 2.14.0`, `SQLAlchemy 2.0.49`, `aiosqlite 0.22.1`, `alembic 1.18.4`, `uvicorn 0.46.0`, `sse-starlette 3.3.4`, `websockets 16.0`, `httpx 0.28.1`, `openai 2.32.0`, `anthropic 0.97.0`, `orjson 3.11.8`, `pytest 9.0.3`, `pytest-asyncio 1.3.0`, `hypothesis 6.152.2`, `respx 0.23.1`, `ruff 0.15.12`, `pyright 1.1.409`, `uv 0.11.7`.
- npm registry, queried 2026-04-25: `react 19.2.5`, `react-dom 19.2.5`, `vite 8.0.10`, `@vitejs/plugin-react 6.0.1`, `typescript 6.0.3`, `react-router 7.14.2`, `@tanstack/react-query 5.100.1`, `zod 4.3.6`, `openapi-typescript 7.13.0`, `openapi-fetch 0.17.0`, `vitest 4.1.5`, `@testing-library/react 16.3.2`, `@testing-library/user-event 14.6.1`, `jsdom 29.0.2`, `playwright 1.59.1`, `eslint 10.2.1`, `typescript-eslint 8.59.0`, `prettier 3.8.3`, `@types/react 19.2.14`, `@types/react-dom 19.2.3`, `@types/node 24.12.2`, `npm 11.13.0`.
- FastAPI docs via Context7 `/fastapi/fastapi`: Pydantic request-body validation, dependency injection, and WebSocket validation.
- SQLAlchemy 2.0 docs via Context7 `/websites/sqlalchemy_en_20`: asyncio extension, `sqlite+aiosqlite`, and `AsyncSession` concurrency caveat.
- Vite docs via Context7 `/vitejs/vite`: Vite scaffolding, Node compatibility, Vite 8 and `@vitejs/plugin-react` v6 notes.
- React docs via Context7 `/reactjs/react.dev`: React 19 TypeScript setup and Vite React TypeScript project guidance.
- SQLite official docs: WAL mode and PRAGMA behavior, https://www.sqlite.org/wal.html and https://www.sqlite.org/pragma.html.
- OpenAI official docs, restricted to OpenAI domains for API guidance: structured outputs and API authentication, https://developers.openai.com/api/docs/guides/structured-outputs and https://developers.openai.com/api/reference/overview#authentication.
- Anthropic official docs: Messages API and authentication headers, https://platform.claude.com/docs/en/api/messages and https://platform.claude.com/docs/en/api/overview.
- Node.js official release schedule and releases: Node 24 LTS line and current release metadata, https://github.com/nodejs/Release and https://nodejs.org/en/download/archive/v24.15.0.
- Python official release schedule/release pages: Python 3.14 stable line, https://peps.python.org/pep-0745/ and https://www.python.org/downloads/.

---
*Stack research for: Gray Go Arena*
*Researched: 2026-04-25*
