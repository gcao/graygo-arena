# Phase 5: Trust Hardening, Replay & Guardrails - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 completes v1 trust features: redacted game export/replay data, secret-storage and privacy guardrail checks, and provider settings/status UI without browser-side token entry.

It does not add hosted auth, cost billing integrations, tournaments, CLI providers, or cloud sync.
</domain>

<decisions>
## Implementation Decisions

- **D-01:** Export bundles must be generated from backend persisted state, not scraped from transient UI state.
- **D-02:** Export bundles may include public and private transcript classes only with explicit operator action; token values must never appear.
- **D-03:** Guardrails are local deterministic checks over persisted records and configured provider aliases.
- **D-04:** UI settings show provider aliases, configured status, auth type, and model names only; no token entry/display fields.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` - PROV-07, API-06, UI-10.
- `.planning/ROADMAP.md` - Phase 5 success criteria.
- `backend/src/graygo_arena/api/routes.py` - API route structure.
- `backend/src/graygo_arena/persistence/repositories.py` - persisted data access.
- `frontend/src/App.tsx` - operator console layout.
</canonical_refs>

---

*Phase: 05-trust-hardening-replay-guardrails*
*Context gathered: 2026-04-25*
