# Plan 04-02 Summary: Anthropic Direct Adapter

**Completed:** 2026-04-25
**Requirements:** PROV-05
**Status:** Complete

## Delivered

- Added backend settings for `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`.
- Added direct HTTP Anthropic Messages adapter using forced `choose_graygo_move` tool use.
- Registered `anthropic_default` provider alias with configured status based on backend environment.
- Added mocked tests for `x-api-key`, `anthropic-version`, tool-choice payload shape, tool-use parsing, metadata capture, and safe missing-key behavior.

## Verification

- `cd backend && uv run pytest` passed with 76 tests.
- `cd backend && uv run ruff check .` passed.
- `cd backend && uv run ruff format --check .` passed.
- `cd backend && uv run pyright` passed.
