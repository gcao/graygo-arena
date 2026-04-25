# Phase 5 Research: Trust Hardening

**Researched:** 2026-04-25

## Scope

Implement the smallest useful v1 trust layer:

- backend redacted export endpoint with enough game/turn/transcript/event/call data for replay/debugging
- backend guardrail endpoint that checks persisted records for secret-looking values and transcript separation
- provider settings endpoint/UI that exposes configured status without secret entry or token display
- UI uses backend export endpoint instead of local-only JSON

## Checks

Guardrail checks should return named statuses:

- `secret_values_absent`
- `credential_refs_only`
- `transcript_views_separated`
- `provider_settings_safe`

All checks are deterministic and local.

## Verification

Run:

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run pyright
cd frontend && npm run typecheck && npm run build
```

---

*Research completed: 2026-04-25*
