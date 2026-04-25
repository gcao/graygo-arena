# Phase 3 Research: React Operator UI & Live Inspection

**Researched:** 2026-04-25
**Confidence:** High for fake/scripted UI scope.

## Scope

The UI should prove the backend slice can be operated by a human:

- provider discovery
- new fake/scripted game setup
- same-provider/model isolation notice
- live board rendering from backend BoardKeys
- lifecycle controls
- turn history and latest-turn audit
- transcript views with public/private/debug modes
- cell inspector with toroidal neighbors
- SSE-triggered refetch behavior

## Stack Choice

Use React + TypeScript + Vite with `lucide-react` for icons. Keep dependencies lean:

- `react`
- `react-dom`
- `lucide-react`
- `@vitejs/plugin-react`
- `vite`
- `typescript`

Use direct `fetch` wrappers rather than generated OpenAPI in Phase 3. The backend schemas are still local and small; generated clients can be added after Phase 4 stabilizes provider payloads.

## API Client Shape

Create a narrow typed client in `frontend/src/api/client.ts`:

- `listProviders`
- `createGame`
- `getGame`
- `startGame`
- `pauseGame`
- `resumeGame`
- `stopGame`
- `stepGame`
- `autorunGame`
- `listTurns`
- `getTranscript`
- `listEvents`

Use relative paths and Vite proxy config:

```ts
server: {
  proxy: {
    "/api": "http://127.0.0.1:8000"
  }
}
```

## UI Design Notes

This is an operator console. Avoid marketing composition and oversized hero sections. Use:

- compact panels
- dense but readable labels
- stable grid dimensions
- explicit state/status chips
- restrained palette with black/white/gray board semantics and teal/amber highlights
- accessible buttons with icons and labels

## Verification

Phase 3 should pass:

```bash
cd frontend
npm run typecheck
npm run build
```

Run the backend during manual UI verification:

```bash
cd backend
uv run uvicorn graygo_arena.main:app --reload --port 8000
```

Then run Vite and verify a fake/scripted game can be created and stepped:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## Risks

| Risk | Response |
|------|----------|
| UI computes game state locally | Board changes only after REST/SSE fetches. |
| Dense layout becomes unreadable | Use clear sectioning, stable spacing, and no nested cards. |
| SSE stream creates stale state | Treat SSE as a refetch trigger, not as a state replacement. |
| Browser secrets creep in | Provider form only uses backend aliases and credential refs. |

---

*Research completed: 2026-04-25*
