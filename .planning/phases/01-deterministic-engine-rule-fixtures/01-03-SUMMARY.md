# Plan 01-03 Summary: Fixtures and Regression Guards

**Completed:** 2026-04-25
**Requirements:** ENG-08
**Status:** Complete

## Delivered

- Added named golden fixtures for core engine mechanics in `backend/tests/fixtures/engine_cases.json`.
- Added a fixture loader that converts fixture dictionaries into `GameState` and parsed moves.
- Added parametrized fixture tests covering BoardKey round trips, collision-to-gray, adjacent placements, toroidal capture, forbidden updates, double pass, and pass-plus-placement.
- Added Hypothesis property tests for BoardKey stability, coordinate round trips, toroidal neighbor symmetry, deterministic resolution, and pre-state immutability.
- Added an import-boundary guard that fails if pure engine modules import framework, persistence, provider, UI, HTTP, or app connector namespaces, including `codex_apps`.

## Verification

- `cd backend && uv run pytest` passed with 54 tests.
- `cd backend && uv run ruff check .` passed.
- `cd backend && uv run ruff format --check .` passed.
- `cd backend && uv run pyright` passed.

## Coverage

- ENG-01 through ENG-08 are covered by Phase 1 implementation and tests.
- Phase 1 remains pure Python engine code with no network, persistence, browser, provider, or connector surface.
