# Phase 4: Direct OpenAI & Anthropic Providers - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 adds backend-only direct OpenAI and Anthropic provider adapters behind the existing Phase 2 provider boundary. The adapters request one structured move from each seat, parse the move JSON/tool payload, preserve raw response metadata for audit, and keep credential values server-side.

It does not add CLI/OAuth providers, local models, budget dashboards, leakage audit UI, or hosted secret management. Those remain deferred.
</domain>

<decisions>
## Implementation Decisions

- **D-01:** Use backend-only environment variables for provider keys. Browser/UI sees aliases and configured status only.
- **D-02:** Use direct HTTPS via `httpx` instead of provider SDK wrappers to keep the adapter surface small and easy to test with `MockTransport`.
- **D-03:** OpenAI uses the Responses API with JSON Schema structured output.
- **D-04:** Anthropic uses the Messages API with a forced `choose_graygo_move` client tool and JSON Schema input.
- **D-05:** Both adapters return the existing `ProviderMoveResponse` shape and let the orchestrator validate BoardKey and legal move.
- **D-06:** Missing API keys make real provider aliases visible but unconfigured; provider tests return a safe failure without making a network call.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` - PROV-04 and PROV-05.
- `.planning/ROADMAP.md` - Phase 4 scope and dependency on Phase 3.
- `.planning/phases/02-fair-orchestrator-api-persistence/02-02-SUMMARY.md` - Provider boundary.
- `backend/src/graygo_arena/providers/registry.py` - Existing provider catalog.
- `backend/src/graygo_arena/application/models.py` - Provider request/response contracts.
- OpenAI official docs: `https://platform.openai.com/docs/api-reference/responses/create`
- OpenAI official docs: `https://platform.openai.com/docs/guides/structured-outputs`
- Anthropic official docs: `https://docs.anthropic.com/en/api/messages-examples`
- Anthropic official docs: `https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use`
</canonical_refs>

<specifics>
## Specific Ideas

- Add aliases `openai_default` and `anthropic_default`.
- Add settings for `OPENAI_API_KEY`, `OPENAI_MODEL`, `ANTHROPIC_API_KEY`, and `ANTHROPIC_MODEL`.
- Store response IDs/request IDs in provider metadata but not token values.
- Tests should use `httpx.MockTransport`; no real provider calls in CI/local verification.
</specifics>

<deferred>
## Deferred Ideas

- Provider cost estimates and budget guardrails - Phase 5.
- CLI/OAuth adapters - v2.
- Provider SDK migration if direct HTTP becomes too verbose - future maintenance only.
</deferred>

---

*Phase: 04-direct-openai-anthropic-providers*
*Context gathered: 2026-04-25*
