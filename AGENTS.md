# Gray Go Arena Agent Guide

This file governs the repository rooted at `/Users/gcao/proj/graygo-arena`.

## Project Context

Read these files before planning or implementation work:

- `.planning/PROJECT.md` - product intent, core value, constraints, and key decisions.
- `.planning/REQUIREMENTS.md` - v1 requirements and phase traceability.
- `.planning/ROADMAP.md` - current phase sequence and success criteria.
- `.planning/STATE.md` - current project position and active concerns.
- `.planning/research/SUMMARY.md` - research synthesis and phase-ordering rationale.
- `docs/design.md` - original source design.

## Core Invariants

- The backend is the only authoritative owner of board state, legal moves, captures, forbidden points, pass state, scoring, and BoardKeys.
- Models are move selectors only. Never accept model-echoed boards, captures, or scores as authoritative state.
- Black and White must always have separate seat sessions, histories, provider state references, private transcripts, and retry state.
- Simultaneous turns must prompt both seats from the same immutable pre-turn board and BoardKey before either pending move becomes public or opponent-visible.
- Provider credentials stay on the backend. Browser code and API responses expose only configured aliases and safe metadata.
- Fake/scripted agents must prove the engine, orchestration, API, persistence, UI, and privacy boundaries before paid provider adapters are enabled.

## Planned Stack

- Backend: Python 3.14, uv, FastAPI, Pydantic, Pydantic Settings, SQLAlchemy 2.x, SQLite/aiosqlite, Alembic, SSE via `sse-starlette`.
- Provider adapters: fake random and scripted first, then direct OpenAI and Anthropic SDK adapters.
- Frontend: React 19, TypeScript 6, Vite 8, TanStack Query, generated OpenAPI types, `openapi-fetch`, Zod for event payload checks.
- Testing: pytest, pytest-asyncio, Hypothesis, Ruff, Pyright, Vitest, Testing Library, Playwright.

## Workflow

- Use the GSD artifacts as the execution source of truth.
- Next step after initialization is Phase 1 planning: `$gsd-discuss-phase 1` or `$gsd-plan-phase 1`.
- Keep diffs small and phase-scoped.
- Before implementing a phase, lock ambiguous Gray Go semantics into fixtures and tests.
- For commits, follow the Lore Commit Protocol described in the active workspace instructions.

## Phase Focus

Current focus: Phase 1, Deterministic Engine & Rule Fixtures.

Phase 1 must establish the pure deterministic engine and tests before any orchestration, API, UI, or provider work.

## IMPORTANT

Do not use codex_apps, Apps connectors, or app MCP tools unless explicitly requested. Prefer local filesystem, git CLI, and normal shell tools.
