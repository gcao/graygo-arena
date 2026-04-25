# Phase 3: React Operator UI & Live Inspection - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers the React/Vite operator console for fake/scripted games. The UI configures games, calls backend lifecycle endpoints, renders authoritative board state, tracks live updates, and inspects turns/transcripts/audit data.

It does not implement direct OpenAI/Anthropic providers, browser-side secrets, hosted auth, provider settings guardrails, redacted exports, or replay bundles. Those remain later phases.

</domain>

<decisions>
## Implementation Decisions

### Backend Authority

- **D-01:** The UI must treat backend REST/SSE state as authoritative. It may render derived highlights, but it must not compute board mutations as truth.
- **D-02:** The UI uses relative `/api` calls so Vite can proxy to the backend during development.
- **D-03:** The UI never asks for or stores provider token values; it only uses provider aliases from `GET /api/providers`.

### UX Shape

- **D-04:** First screen is the actual operator workspace: new game setup alongside live game inspection, not a marketing/landing page.
- **D-05:** Visual style should be dense, calm, and operational: restrained panels, clear state, compact controls, and fast scan paths.
- **D-06:** Buttons with common actions use icons from `lucide-react` plus accessible labels/tooltips where useful.
- **D-07:** Board cells have stable square dimensions and must not resize on hover, highlights, or symbol changes.

### UI State

- **D-08:** React state can hold the current selected game, latest fetched state, selected cell, UI toggles, and transcript view.
- **D-09:** SSE messages trigger refetches; REST responses remain the data source for board/turn/transcript details.
- **D-10:** Export in Phase 3 is a local JSON download of already-fetched game/turn/transcript state, not a backend redacted export bundle.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/REQUIREMENTS.md` - UI-01 through UI-09 requirements.
- `.planning/ROADMAP.md` - Phase 3 goal, plans, and success criteria.
- `.planning/STATE.md` - Current focus and completed backend phases.
- `.planning/phases/02-fair-orchestrator-api-persistence/02-03-SUMMARY.md` - REST/SSE API contract.
- `.planning/phases/02-fair-orchestrator-api-persistence/02-04-SUMMARY.md` - SQLite persistence and transcript behavior.
- `docs/design.md` - UI state types, board features, history panel, transcript/privacy policy.
- `backend/src/graygo_arena/api/schemas.py` - Actual backend response shapes.
- `backend/src/graygo_arena/api/routes.py` - Actual endpoint paths.

</canonical_refs>

<specifics>
## Specific Ideas

- Use a two-column desktop layout: setup/control rail and live board/audit workspace.
- On narrow screens, stack setup, board, and audit sections.
- Include same-provider/model notice inline in the setup form when both seats match.
- Show board coordinates on all sides needed for scanability; use B/W/G/+ symbols and color-coded cells.
- Cell inspector should show coordinate, content, wrapped orthogonal neighbors, and highlight toggles.

</specifics>

<deferred>
## Deferred Ideas

- Direct provider credential settings - Phase 4/5.
- Redacted export/replay bundles - Phase 5.
- Provider cost/budget guardrails - Phase 5.

</deferred>

---

*Phase: 03-react-operator-ui-live-inspection*
*Context gathered: 2026-04-25*
