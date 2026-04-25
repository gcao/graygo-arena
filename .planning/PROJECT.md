# Gray Go Arena

## What This Is

Gray Go Arena is a local-first web application for running simultaneous-turn Gray Go matches between AI agents. The backend owns all game state and rule resolution, while the models only choose legal moves from an authoritative resolved board.

The product is for a human operator who wants to configure AI seats, run or step through matches, inspect public/private transcripts, and verify that same-model or cross-provider matches stay isolated and rule-correct.

## Core Value

The backend must be the trusted arbiter: it must preserve simultaneous move fairness, enforce Gray Go rules exactly, and prevent private seat context from leaking between agents.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] Build a deterministic Gray Go engine that owns board state, legal move validation, collision-to-gray resolution, toroidal liberties, two-stage captures, forbidden points, pass handling, and scoring.
- [ ] Build a game orchestrator that creates games, starts/stops/steps rounds, calls both seats from the same pre-move board, resolves moves simultaneously, persists the post-board, and broadcasts updates.
- [ ] Model Black and White as separate seat sessions, even when they use the same provider/model, so provider session state and private transcripts cannot cross-contaminate.
- [ ] Keep all provider credentials on the backend and expose only safe configured aliases to the UI.
- [ ] Provide provider adapters for fake/scripted agents first, then OpenAI and Anthropic direct APIs, with CLI adapters deferred until the direct integrations work.
- [ ] Require structured move output from agents, validate JSON and BoardKey server-side, retry malformed/illegal outputs once, and apply the configured invalid-move policy.
- [ ] Provide REST endpoints for provider discovery/testing, game lifecycle, single-step execution, autorun, current game state, turn history, and transcript views.
- [ ] Provide an SSE or WebSocket event stream for live game updates.
- [ ] Persist games, seat sessions, turns, boards, AI calls, public logs, and private seat transcripts without storing secret token values.
- [ ] Build a React/TypeScript SPA for New Game, Live Game, Game History, Provider Status, and Settings workflows.
- [ ] Build a board UI with coordinates, B/W/G/+ symbols, last-move highlights, collision/capture highlights, cell inspection, and toroidal-neighbor visualization.
- [ ] Let the operator inspect public transcript, seat-private strategic summaries, raw provider responses, and backend validation/resolution audit without feeding private opponent context back into prompts.
- [ ] Use fake random and deterministic scripted agents before paid model calls so the engine, orchestrator, API, and UI can be verified cheaply.

### Out of Scope

- Browser-side API tokens - credentials must never be entered into or exposed through the SPA.
- AI-authored board updates - models may echo boards for diagnostics, but the backend engine is the only authority.
- Shared provider conversations between seats - Black and White never share a response chain, conversation, local history, or CLI state.
- Production multi-user auth - v1 is an operator tool for local or trusted environments, not a hosted public service.
- Claude Code and Codex CLI adapters in the first milestone - direct provider APIs and fake agents come first because CLI adapters add operational fragility.
- PostgreSQL-first deployment - SQLite is the local development persistence target; PostgreSQL can follow once transcripts and durability matter.

## Context

The design document defines a FastAPI + Python backend and a React + TypeScript + Vite SPA. Python is preferred because existing Gray Go logic is assumed to be available or easy to port, and Pydantic is useful for validating model output. SQLite is the initial persistence target.

The core gameplay loop is:

1. Backend holds resolved board S.
2. Backend computes BoardKey(S).
3. Backend sends Black and White separate prompts based on the same S.
4. Neither prompt includes the opponent's pending move.
5. Backend validates both replies.
6. Backend resolves the two moves simultaneously.
7. Backend persists S' and broadcasts the result.
8. Repeat until game end, stop, invalid-provider failure, or max turns.

The UI should focus on configuration, visualization, controls, and transcript inspection. The backend should focus on rule correctness, provider isolation, persistence, and event delivery.

## Constraints

- **Security**: API tokens stay entirely on the backend - OpenAI, Anthropic, Claude Code, and Codex credentials must never appear in browser code or responses.
- **Privacy**: Black and White seat transcripts, strategic summaries, raw model outputs, response chains, and CLI state must be isolated by seat.
- **Correctness**: The engine, not the model, is authoritative for boards, legal moves, captures, forbidden points, and scoring.
- **Fairness**: Both seats must be prompted from the same pre-move board before either pending move is known to the other side.
- **Stack**: Backend is FastAPI/Python with Pydantic validation; frontend is React/TypeScript/Vite; local persistence is SQLite.
- **Cost control**: Fake and scripted agents come before paid provider adapters.
- **Observability**: Every turn should have enough stored audit data to reconstruct prompt input, model output, validation, resolution, captures, and post-board state.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Backend owns all game state | Prevents model rule mistakes and illegal board updates | Pending |
| Simultaneous turns resolve server-side | Preserves fairness and prevents peeking | Pending |
| Separate seat sessions for Black and White | Same provider/model matches must not leak private context | Pending |
| Structured JSON move responses | Lets the backend reject malformed or stale BoardKey outputs deterministically | Pending |
| Fake/scripted agents before real providers | Verifies rules, API, and UI before spending provider tokens | Pending |
| SQLite for v1 local persistence | Keeps local setup simple while preserving turn/transcript history | Pending |
| Direct OpenAI/Anthropic adapters before CLI adapters | Direct APIs are easier to validate and operate than subprocess-based auth/session paths | Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? Move to Out of Scope with reason.
2. Requirements validated? Move to Validated with phase reference.
3. New requirements emerged? Add to Active.
4. Decisions to log? Add to Key Decisions.
5. "What This Is" still accurate? Update if drifted.

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections.
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state.

---
*Last updated: 2026-04-24 after initialization from docs/design.md*
