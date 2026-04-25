# Pitfalls Research

**Domain:** Local-first AI-vs-AI simultaneous Gray Go arena
**Researched:** 2026-04-25
**Confidence:** HIGH

## Phase Names Used In This Research

Roadmap phases do not exist yet, so this file uses provisional phase names for planning.

1. **Deterministic Engine & Rule Fixtures** - board model, BoardKey, legal moves, toroidal liberties, collision, two-stage capture, forbidden points, pass, scoring, and golden tests.
2. **Orchestrator + Fake/Scripted Agents** - simultaneous turn runner, lifecycle controls, seat sessions, invalid-move policy, and zero-cost agents.
3. **API, Persistence & Privacy Boundaries** - REST contracts, SQLite schema, transaction boundaries, transcript views, provider aliases, and secret-free storage.
4. **Live UI Inspection & Event Consistency** - React game screens, board inspection, transcript panels, SSE/WebSocket state sync, and reconnect behavior.
5. **Direct Provider Adapters** - OpenAI and Anthropic direct APIs, structured/JSON output handling, provider retries, timeouts, request IDs, and rate-limit behavior.
6. **Operational Hardening, Replay & Export** - replay audits, crash recovery, retention, export, broader stress testing, and v2 readiness.

## Critical Pitfalls

### Pitfall 1: Model Output Becomes Board Authority

**What goes wrong:**
The backend accepts a model's echoed board, inferred captures, legality claims, or score estimate as game state. A single plausible-looking response can silently mutate the board outside the Gray Go engine.

**Why it happens:**
Model responses are tempting to reuse because they already contain a board echo, audit notes, and a chosen move. During UI prototyping, it is especially easy to render or persist the model's board echo as if it were authoritative.

**How to avoid:**
- Treat the model as a move selector only. The only accepted semantic field is `move`, plus diagnostic fields used for validation/audit.
- Compute `pre_board_key`, legal moves, captures, forbidden updates, `post_board`, `post_board_key`, and scoring inside the engine.
- Persist both model diagnostics and backend resolution audit, but make the schema name the model board field `current_board_echo` or `diagnostic_board_echo`, never `board`.
- Reject or flag responses where the echo does not match the server BoardKey; do not repair server state from the echo.

**Warning signs:**
- Provider adapter return types include `postBoard`, `captures`, `score`, or other rule outcomes.
- Frontend reducers update the board from raw provider JSON instead of `/api/games/{id}` or a backend `turn_resolved` event.
- Tests assert model-provided board strings rather than engine-computed board strings.
- A turn can be persisted without an engine resolution object.

**Early detection checks:**
- Unit test: a model returns a legal move with a deliberately false board echo; the turn resolves from backend state and records the echo mismatch as diagnostic only.
- Static/API contract check: provider adapter output schema contains `move`, `board_key`, and diagnostics, but no authoritative board mutation fields.
- Replay check: recomputing every post-board from persisted pre-board and moves matches stored `post_board_key`.

**Phase to address:**
Phase 1 prevents this in the engine contract. Phase 4 re-checks it in UI state handling.

---

### Pitfall 2: Simultaneity Leaks Through Sequential Orchestration

**What goes wrong:**
Black is called, Black's pending move is stored or appended to history, then White is prompted with context that reveals Black's move for the same board. The game still appears to run, but fairness is broken.

**Why it happens:**
Naive orchestration mirrors normal turn-based games: call one side, update state, call the other. Even when calls are started concurrently, mutable shared history or logging can leak one pending response into the other prompt.

**How to avoid:**
- Build both prompts from an immutable snapshot: `pre_board`, `pre_board_key`, public resolved history, and same-turn legal move lists.
- Create the unresolved turn record before calls, but do not append either pending move to public or opponent-visible history until both calls finish and validation is complete.
- Store pending provider results under the seat's own call record, not under shared game history.
- Apply stale-response checks: a provider response is valid only for the exact turn id, color, and `pre_board_key`.

**Warning signs:**
- `run_one_turn` calls one provider before building the other prompt.
- Prompt builder reads "latest turn history" after one provider response is saved.
- Logs or transcripts show `black_move` for turn N before `white_prompt` for turn N is constructed.
- Same-model mirror games show suspicious immediate counterplay to a hidden pending move.

**Early detection checks:**
- Spy fake agents record exact prompt payloads; assert Black and White prompts for the same turn have identical `pre_board_key` and neither includes the other's pending move.
- Delay-injection test: Black sleeps and White returns instantly, then invert delays; resulting prompt payloads remain identical except color/objective/private history.
- Database invariant: unresolved same-turn moves are not visible in public transcript or opponent prompt material.

**Phase to address:**
Phase 2 must block this before any real provider exists.

---

### Pitfall 3: Seat Privacy Cross-Contaminates Same-Model Games

**What goes wrong:**
Black and White share provider conversation state, response chains, local histories, previous response IDs, raw outputs, CLI working directories, or transcript views. Same provider/model games become contaminated and no longer test isolated agents.

**Why it happens:**
Developers often key state by provider/model instead of game/seat, reuse one SDK client abstraction with hidden conversation state, or treat transcript viewing as a UI concern instead of a server-side privacy boundary.

**How to avoid:**
- Key all seat session state by `(game_id, color)` and give each seat its own session id.
- Prefer manual per-seat history for direct providers in v1; if provider-side conversation objects are used, create one per seat and never share `previous_response_id` chains.
- Enforce transcript view separation server-side: `public`, `black_private`, `white_private`, and `debug` are different views over stored data, not frontend filters over one raw blob.
- For v2 CLI adapters, use separate working/config directories such as separate `CODEX_HOME` paths per seat.

**Warning signs:**
- `seat_sessions` has one row per game instead of two.
- `previous_response_id`, `provider_conversation_id`, or local message arrays are attached to provider/model config rather than seat session.
- Prompt builder accepts "all transcripts" and filters in the frontend.
- A private Black phrase appears in a White prompt or White transcript endpoint.

**Early detection checks:**
- Sentinel test: inject `BLACK_PRIVATE_SENTINEL` and `WHITE_PRIVATE_SENTINEL` into each seat's private history; assert each is absent from the opponent prompt, public transcript, and opponent transcript endpoint.
- Same provider/model game test: two separate seat session ids, two separate local histories, and no shared previous-response pointer.
- API test: transcript endpoints return only the view-specific records and never expose the other seat's raw response unless the explicit debug view is requested.

**Phase to address:**
Phase 2 establishes seat sessions. Phase 3 enforces transcript and persistence boundaries.

---

### Pitfall 4: Malformed, Stale, Or Illegal Model Output Is Normalized Away

**What goes wrong:**
The backend parses loose prose, accepts stale `BoardKey` values, coerces invalid coordinates, silently chooses a fallback move, or retries against a changed board. Bad model behavior becomes invisible and can corrupt game outcomes.

**Why it happens:**
Strict validation feels like friction early on, and fake agents return clean output. Real providers can return partial JSON, extra text, stale context, refusal-like responses, truncation, or a legal-looking move for the wrong board.

**How to avoid:**
- Require structured output for providers that support it and still validate server-side with Pydantic or equivalent typed schemas.
- Require exact `board_key` match and `move in legal_moves`.
- Retry once using the same board, same `BoardKey`, same legal move list, same turn id, and a validation error summary.
- Make the invalid-move policy explicit: `manual_intervention`, `retry_then_pass`, or `retry_then_forfeit`. Use `manual_intervention` while researching failure modes.

**Warning signs:**
- Parsing uses regex over raw text for coordinates.
- The adapter returns a move even when JSON validation failed.
- Retry code rebuilds the prompt from current game state instead of the original pre-turn snapshot.
- Invalid move rates are not visible in stored audit data.

**Early detection checks:**
- Fuzz tests feed malformed JSON, extra prose, missing fields, stale `board_key`, illegal coordinates, lowercase/uppercase variants, duplicated fields, and truncation.
- Retry test asserts the retry prompt has the same `pre_board_key`, same legal moves, and no opponent pending move.
- Policy test verifies each invalid-move policy transitions the turn to the expected status without advancing the board incorrectly.

**Phase to address:**
Phase 2 implements validation with fake adapters. Phase 5 adds provider-specific structured output and error handling.

---

### Pitfall 5: Provider Credentials Escape The Backend Boundary

**What goes wrong:**
API keys or OAuth tokens appear in SPA bundles, provider-list responses, logs, persisted `agent_calls`, raw error payloads, exported transcripts, or browser devtools traffic.

**Why it happens:**
Local-first apps can feel "trusted," so developers may add convenience fields, frontend `.env` variables, or verbose debugging logs. Provider SDK errors and request dumps can also include sensitive headers if not sanitized.

**How to avoid:**
- UI sees only configured aliases and `configured: true/false`; actual token values live in backend environment/config only.
- Store `credential_ref`, never token values, in games, seat sessions, turns, agent calls, transcripts, and exports.
- Add response/log sanitization for known token patterns and provider auth headers.
- Keep provider test endpoints backend-only in execution even though the SPA can trigger a test by alias.

**Warning signs:**
- Frontend code references `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, or `VITE_*_API_KEY`.
- `/api/providers` returns a value resembling `sk-`, `sk-ant-`, bearer tokens, or OAuth tokens.
- Debug transcript/export includes request headers.
- SQLite rows contain raw token-looking strings.

**Early detection checks:**
- API test calls every provider/config endpoint and asserts no known secret patterns appear.
- Secret scan over frontend build output, backend logs, SQLite database, and exported transcript fixtures.
- Unit test for log sanitizer with OpenAI bearer auth and Anthropic `x-api-key` style inputs.

**Phase to address:**
Phase 3 must prevent this before the Provider Status and Settings screens ship. Phase 5 repeats the scan with real provider adapters enabled.

---

### Pitfall 6: Provider Flakiness Advances Or Corrupts Game State

**What goes wrong:**
Timeouts, rate limits, overloaded providers, partial streaming failures, duplicate retries, or late responses are treated as moves. The game advances a turn with one real move and one ambiguous provider failure, or a stale late response lands on a later turn.

**Why it happens:**
The orchestrator may initially assume fake agents are deterministic and immediate. Real APIs return transient failures, request ids, rate-limit errors, overload errors, and timeouts that require explicit state transitions.

**How to avoid:**
- Model provider calls as auditable call records with status: `started`, `succeeded`, `invalid_output`, `retrying`, `failed`, `timed_out`, or `cancelled`.
- Advance the game only after both seats have valid moves or the configured invalid/failure policy explicitly resolves the turn.
- Bind each response to `(game_id, turn_id, color, pre_board_key, attempt_index)`.
- Record provider request ids and error classes for debugging, but sanitize secrets.
- Implement bounded retries with exponential backoff for transient provider errors; never retry indefinitely inside autorun.

**Warning signs:**
- Exception handlers convert provider failures to `PASS` without an explicit game setting.
- A timeout leaves `thinking=true` forever in UI.
- Late provider responses can update `current_turn` without checking turn id.
- Autorun has no stop condition for repeated provider failures.

**Early detection checks:**
- Fake provider raises timeout, 429/rate-limit, overload, connection reset, and malformed response; assert turn status and game board remain correct.
- Duplicate-response test sends the same provider result twice; only one call record resolves and game turn advances once.
- Late-response test resolves turn N, then delivers a delayed response for turn N after turn N+1 starts; stale response is stored as ignored and cannot mutate game state.

**Phase to address:**
Phase 5, with a Phase 2 placeholder state model so provider failure states do not require rewiring the orchestrator later.

---

### Pitfall 7: UI Displays A Different Game Than The Backend

**What goes wrong:**
The live board, move highlights, transcript panels, or thinking indicators drift from backend state due to optimistic UI updates, dropped SSE/WebSocket events, out-of-order messages, or reconnects. The operator trusts an inspection screen that is not actually inspecting authoritative state.

**Why it happens:**
Realtime UI code often treats event streams as the state source. But event streams are delivery mechanisms; the backend game resource remains the authority, especially after reconnect, pause/resume, and autorun.

**How to avoid:**
- UI renders board state from backend `GameView`/`TurnView` payloads only, never from model output or local guessed resolution.
- Add monotonically increasing `turn_index` and `event_sequence` to live events.
- On reconnect, reload `/api/games/{id}` and recent turns, then resume events from current state.
- Display `pre_board_key`/`post_board_key` in turn resolution so the operator can compare UI, history, and backend audit.

**Warning signs:**
- Frontend applies local Gray Go rules to predict the next board.
- Events lack turn index or sequence.
- Reloading the page after several turns shows a different board than the pre-reload view.
- Captures/collisions are highlighted from frontend inference rather than backend placement/capture events.

**Early detection checks:**
- Playwright flow: start fake-agent game, step several turns, reload, reconnect event stream, and assert board symbols, turn number, last moves, and BoardKey match backend `GET /api/games/{id}`.
- Out-of-order event test: deliver `agent_call_finished` after `turn_resolved`; UI does not regress thinking state or board.
- Contract test: every UI highlight comes from backend `TurnView` placement/capture fields.

**Phase to address:**
Phase 4.

---

### Pitfall 8: Persistence Cannot Reconstruct A Turn

**What goes wrong:**
The database stores the current board but not enough pre-board, prompt, response, validation, resolution, capture, and forbidden-point data to explain how it got there. Debugging privacy leaks, illegal moves, or provider failures becomes guesswork.

**Why it happens:**
Early in-memory implementations often add persistence as snapshots only. SQLite also makes it easy to rely on implicit autocommit, leaving partial records after crashes or exceptions.

**How to avoid:**
- Persist each turn as an audit record: pre-board, pre-BoardKey, prompts or prompt metadata, raw/sanitized provider output, parsed output, validation result, resolution object, post-board, post-BoardKey, captures, forbidden updates, and status.
- Wrap turn creation, call records, resolution, and game-current-state update in explicit transaction boundaries appropriate to the step being committed.
- Use statuses that make crash recovery explicit: `agent_thinking`, `awaiting_retry`, `manual_intervention`, `resolved`, `failed`, `cancelled`.
- Replay from persisted turns in tests and compare BoardKeys.

**Warning signs:**
- `games.current_board_json` is updated but no matching resolved `turns` row exists.
- `agent_calls.raw_response` is stored without parsed validation outcome.
- A crash mid-step leaves `current_turn` advanced with no `post_board_key`.
- Replay requires reading frontend logs.

**Early detection checks:**
- Crash-injection test after turn row creation, after one agent call, after both calls, after resolution, and after game update; recovery produces an inspectable status without double-applying moves.
- Replay test recomputes game state from turn 0 to latest and matches `games.current_board_key`.
- SQLite transaction test verifies related writes commit or roll back together for a resolved turn.

**Phase to address:**
Phase 3, with replay hardening in Phase 6.

---

### Pitfall 9: Paid Provider Integration Starts Before Fake-Agent Proof

**What goes wrong:**
OpenAI/Anthropic calls are wired before engine, orchestrator, API, persistence, and UI inspection are proven with fake/scripted agents. Every defect becomes slower, more expensive, harder to reproduce, and mixed with provider variability.

**Why it happens:**
Watching real models play is the exciting demo. It also masks deterministic defects because model output and provider failures create noise.

**How to avoid:**
- Make fake random and deterministic scripted adapters first-class provider adapters.
- Require engine, orchestrator, API, UI, persistence, and transcript privacy smoke tests to pass using fake/scripted agents before enabling real provider adapters.
- Keep paid-provider configuration paths absent or disabled until the zero-cost path proves the board and privacy invariants.

**Warning signs:**
- Provider credentials are needed to run the first end-to-end test.
- Engine tests are being debugged through real model transcripts.
- UI inspection cannot run offline.
- Rate limits or costs appear before simultaneous-turn invariants are tested.

**Early detection checks:**
- CI/local smoke command runs a complete game with deterministic scripted agents and no provider environment variables.
- Provider absence test: app starts, provider list shows fake/scripted adapters, and game stepping works without paid credentials.
- Roadmap gate: Phase 5 cannot start until fake-agent E2E covers engine, orchestration, persistence, UI BoardKey display, and privacy sentinels.

**Phase to address:**
Phase 1 and Phase 2 establish this gate. Phase 5 is explicitly blocked until the gate passes.

---

### Pitfall 10: Gray Go Edge Cases Are Treated Like Ordinary Go

**What goes wrong:**
The engine implements standard grid Go assumptions and misses Gray Go specifics: toroidal neighbors, same-point collision-to-gray, two-stage captures, forbidden points, simultaneous passes, or color-specific legality after forbidden updates.

**Why it happens:**
The board looks small and Go-like, making it easy to reuse familiar algorithms without encoding simultaneous resolution and toroidal topology directly into tests.

**How to avoid:**
- Build the engine as a pure deterministic module before adapters or UI.
- Create golden fixtures for every rule mechanic and edge case.
- Include symmetry/property tests for toroidal wrapping and BoardKey round-trips.
- Keep resolution order explicit: validate moves from pre-board, place simultaneously, convert collisions, apply two-stage capture/forbidden updates, then compute post-board and score/pass status.

**Warning signs:**
- Neighbor logic has boundary checks instead of modular wrapping.
- Legal moves are computed once globally rather than per color with forbidden points.
- Collision code runs after capture code without an explicit rule test.
- Pass handling is bolted onto provider logic instead of engine state.

**Early detection checks:**
- Golden tests for corner wrapping liberties, edge wrapping groups, same-point collision, adjacent simultaneous placements, two-stage captures, forbidden-point updates, double-pass termination, and scoring.
- BoardKey round-trip and canonicalization tests for every fixture.
- Determinism test: same pre-board and moves always produce identical resolution JSON.

**Phase to address:**
Phase 1.

---

### Pitfall 11: Step, Autorun, Pause, And Stop Race Each Other

**What goes wrong:**
Two manual step requests run the same turn, autorun overlaps with manual step, pause occurs after one provider call but before the second, stop fails to cancel pending calls, or resume applies stale pending output.

**Why it happens:**
Lifecycle controls are easy to model as UI buttons but hard to model as a backend state machine. Provider calls are slow and asynchronous, so state transitions need turn-level locking and idempotency.

**How to avoid:**
- Define a backend game state machine before UI controls: `created`, `running`, `agent_thinking`, `paused`, `manual_intervention`, `finished`, `error`, `stopped`.
- Use a per-game lock or transactional compare-and-set for `run_one_turn`.
- Make `POST /step` idempotent enough to reject or return the active turn when a turn is already in progress.
- Cancellation and late-response handling must check game status, turn id, and attempt id before applying results.

**Warning signs:**
- `/step` creates a new turn without checking current status.
- Autorun is a frontend loop over `/step` with no backend guardrails.
- Pause only changes UI state.
- There is no test for two concurrent `/step` calls.

**Early detection checks:**
- Concurrency test fires two `/step` requests at once; exactly one turn is created and resolved.
- Autorun/pause test pauses while fake providers are delayed; board does not advance after pause unless the selected policy explicitly allows finishing the in-flight turn.
- Stop test cancels or ignores pending provider responses and records auditable cancelled/ignored call statuses.

**Phase to address:**
Phase 2 for backend lifecycle semantics; Phase 4 for UI controls reflecting those semantics.

---

### Pitfall 12: Private Transcript Inspection Becomes Prompt Injection

**What goes wrong:**
The operator can inspect private strategic summaries and raw outputs, but those private/debug views accidentally get fed back into future prompts for the opponent or into public history. Private UI visibility becomes gameplay context.

**Why it happens:**
Transcript display and prompt-building often share data access helpers. A broad "history" query can accidentally include private rows once those rows exist for UI inspection.

**How to avoid:**
- Separate prompt-history queries from transcript-display queries.
- Make prompt builder inputs explicit: rules, current board, BoardKey, legal moves, public resolved history, own private history, and never opponent private/debug data.
- Store transcript rows with `visibility` and `seat_session_id`; require prompt builder tests for every visibility class.
- Treat raw provider response as debug material, not default prompt memory. Prefer concise own-seat summaries if any private memory is retained.

**Warning signs:**
- Prompt builder takes a `debug=true` or `include_private=true` option.
- UI visibility toggles affect backend prompt generation.
- Public transcript includes raw provider response fields.
- Opponent raw JSON appears in "recent history" prompt sections.

**Early detection checks:**
- Visibility matrix test: for each transcript row class, assert whether it can appear in Black prompt, White prompt, public transcript, black_private view, white_private view, and debug view.
- UI toggle test: changing "show raw JSON" changes only response payload/view state, never future prompt payloads.
- Sentinel tests from Pitfall 3 remain part of every prompt-builder regression suite.

**Phase to address:**
Phase 3, with UI verification in Phase 4.

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Regex-parsing coordinates from free text | Fast fake demo with real models | Ambiguous moves, stale BoardKeys ignored, hard-to-debug invalid games | Never for providers; only throwaway manual experiments outside the app |
| Frontend resolving board transitions locally | Snappy prototype | UI can diverge from backend authority and hide engine bugs | Never for persisted/live games |
| One provider session per game/provider/model | Less session plumbing | Same-model games leak private context and invalidate fairness | Never |
| Storing only current board snapshots | Simple database schema | No replay, no audit, impossible failure diagnosis | Only before persistence phase, not after Phase 3 |
| Treating provider failure as automatic PASS | Keeps autorun moving | Provider outage changes game outcome silently | Only if explicitly selected as invalid/failure policy and audited |
| Adding OpenAI/Anthropic before fake E2E | Exciting demo | Cost, flakiness, privacy risk, slow iteration | Never before Phase 2 gates pass |
| Deferring BoardKey validation | Fewer validation failures | Stale context accepted as valid play | Never |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OpenAI direct API | Sharing response chains or conversation state between seats | Use manual per-seat history for v1 or separate provider conversation/response chains per seat |
| OpenAI structured output | Assuming schema output eliminates validation work | Use structured output where supported, then validate `board_key`, legal move, retry policy, and extra-field behavior server-side |
| Anthropic direct API | Treating any text response as JSON-like enough | Require server-side JSON parsing/validation and explicit invalid-output handling |
| Provider retries | Retrying against the latest board | Retry against the original turn snapshot only |
| Provider errors | Collapsing auth, billing, rate-limit, overload, timeout, and malformed output into one "agent failed" state | Store provider error class, sanitized message, request id if available, attempt index, and game policy outcome |
| CLI adapters | Reusing default user-level CLI config/cache for both seats | Defer to v2; use separate working/config dirs and treat cached auth files as secrets |

## Performance And Reliability Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded prompt history | Provider calls slow down, request-size errors, rising cost | Keep public history compact; summarize own private memory; cap raw debug material outside prompts | After dozens to hundreds of turns, depending on verbosity |
| Long SQLite read transactions during live UI/history inspection | Writes intermittently hit busy errors or UI sees stale snapshots | Keep read transactions short; use explicit transactions; consider WAL with checkpoint awareness if concurrent reads/writes matter | During autorun plus active history browsing |
| Event stream as sole source of truth | Reconnect shows stale board or missing turns | Reload current game and recent turns on reconnect; sequence events | Any network interruption |
| Autorun without backpressure | Provider rate limits, accumulating pending calls, runaway cost | One in-flight turn per game; max turns; delay controls; provider failure stop policy | As soon as real providers are enabled |
| Persisting huge raw responses forever | Database grows quickly, exports become sensitive/noisy | Store raw responses with retention/export policy; keep parsed audit separate | After repeated provider games with verbose output |

## Security And Privacy Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Browser-visible provider secrets | Token theft from SPA bundle, network responses, browser logs | Backend-only env/config; UI receives aliases only; secret scans on build/logs/database |
| Private transcript leakage between seats | Same-model games become unfair and privacy promise breaks | Per-seat session ids, prompt visibility matrix tests, server-side transcript view separation |
| Raw provider headers in debug transcript | Credentials leak through operator-facing debug tools | Sanitize request/response logs and never persist auth headers |
| CLI adapter shared home directory | Cached auth/session state crosses seats | Defer CLI adapters; use isolated config dirs per seat in v2 |
| Exporting debug transcript by default | Private strategy and raw model outputs leave local machine unintentionally | Separate public/export/debug modes; require explicit debug export option |
| Treating local-first as no-security | Secrets and private transcripts still sit on disk | Store credential refs only; document storage location; consider retention controls in Phase 6 |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Hiding BoardKey and validation audit | Operator cannot tell whether models used stale state | Show pre/post BoardKeys, move validation, retry/invalid policy outcome |
| Showing private summaries without seat labels | Operator mistakes one seat's reasoning for the other's | Strong color/seat labeling and separate Black/White panels |
| Same-model warning omitted | Operator may assume same model implies shared state or miss isolation guarantee | New Game screen explicitly states two isolated seat sessions will be created |
| Thinking state not tied to backend call status | UI appears stuck or falsely complete | Render status from call records/events and clear it on resolved/failed/cancelled states |
| Captures/collisions shown without source | Operator cannot trust visual highlights | Source all highlights from backend `TurnView` placement/capture events |
| Raw JSON shown as gameplay truth | Operator may believe model's board echo is authoritative | Label model echo as diagnostic and show backend resolution beside it |

## "Looks Done But Isn't" Checklist

- [ ] **Engine authority:** Model can return a false board echo and the backend still resolves from server state only.
- [ ] **Simultaneous prompts:** Black and White prompt snapshots for the same turn have the same `pre_board_key` and no opponent pending move.
- [ ] **Seat isolation:** Same provider/model game creates two seat sessions, two histories, and no shared previous-response/conversation pointer.
- [ ] **Transcript privacy:** Sentinel strings from Black private history never appear in White prompt, public transcript, or White transcript endpoint, and vice versa.
- [ ] **Structured validation:** Malformed JSON, stale BoardKey, illegal coordinate, and provider refusal all follow explicit retry/policy paths.
- [ ] **Credential boundary:** Provider aliases/config endpoints, SPA build output, logs, SQLite rows, and exports contain no raw token patterns.
- [ ] **Provider failure handling:** Timeout, rate limit, overload, duplicate response, and late response cannot silently advance the board.
- [ ] **Persistence audit:** Every resolved turn can be replayed from stored pre-board and moves to the stored post-BoardKey.
- [ ] **UI consistency:** Reload/reconnect after several fake-agent turns shows the same board and BoardKey as backend `GET /api/games/{id}`.
- [ ] **Fake-first gate:** Full local E2E game works with fake/scripted agents and no paid provider credentials.
- [ ] **Lifecycle races:** Concurrent `/step`, pause-during-call, stop-during-call, and autorun max-turn tests are covered.
- [ ] **Rule fixtures:** Toroidal liberty, collision, two-stage capture, forbidden-point, pass, and scoring fixtures are in the Phase 1 test suite.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Model output used as authority | HIGH | Freeze provider/UI work; restore engine-only state contract; add false-echo regression tests; migrate or discard affected games |
| Simultaneity leak | HIGH | Audit prompt construction and turn history writes; add spy-agent prompt tests; invalidate contaminated match results |
| Seat privacy leak | HIGH | Stop provider runs; inspect persisted transcripts; add sentinel tests; rotate any exposed credentials if logs included secrets; mark contaminated games |
| Malformed/stale output accepted | MEDIUM | Tighten schema/BoardKey/legal validation; replay stored games to find affected turns; add invalid-policy tests |
| Credential exposure | HIGH | Remove leaked values, rotate affected tokens, sanitize logs/exports, add secret scans, and audit persistence/browser responses |
| Provider failure corrupts state | MEDIUM | Add provider call state machine and stale-response guards; replay games to identify turns advanced by failures |
| UI/backend divergence | MEDIUM | Make backend state reload authoritative; add event sequence/reconnect tests; remove optimistic board resolution |
| Persistence gap | HIGH | Add missing audit schema; start replay from next version; accept that pre-gap games may not be reconstructable |
| Paid provider too early | LOW/MEDIUM | Disable real adapters by default; complete fake-agent gates; use recorded fixtures only until invariants pass |
| Gray Go edge-case bug | MEDIUM/HIGH | Add fixture for the failing rule; replay all games if persisted; patch engine before provider/UI feature work continues |
| Lifecycle race | MEDIUM | Add per-game locks/status transitions; mark ambiguous in-flight turns failed/manual; add concurrency tests |
| Private transcript prompt injection | HIGH | Split prompt and transcript queries; run visibility matrix tests; invalidate affected games |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Model output becomes board authority | Phase 1; Phase 4 | False board echo test; provider schema has no authoritative board fields; UI renders backend BoardKey |
| Simultaneity leaks through sequential orchestration | Phase 2 | Spy fake agents prove same pre-board snapshot and no opponent pending move in prompts |
| Seat privacy cross-contaminates same-model games | Phase 2; Phase 3 | Same-model game has two seat sessions; sentinel strings never cross prompts or transcript views |
| Malformed/stale/illegal model output normalized away | Phase 2; Phase 5 | Fuzz invalid outputs; exact BoardKey/legal-move validation; retry uses original snapshot |
| Provider credentials escape backend | Phase 3; Phase 5 | Secret scan API responses, logs, DB, exports, and SPA build output |
| Provider flakiness corrupts state | Phase 5 | Fake provider error matrix; timeout/rate-limit/overload/late/duplicate response tests |
| UI displays different game than backend | Phase 4 | Playwright reload/reconnect compares UI board and BoardKey to backend `GET /api/games/{id}` |
| Persistence cannot reconstruct a turn | Phase 3; Phase 6 | Replay persisted turns to recompute current BoardKey; crash-injection recovery tests |
| Paid providers before fake-agent proof | Phase 1; Phase 2 gate before Phase 5 | Complete game runs offline with fake/scripted agents and no paid credentials |
| Gray Go treated like ordinary Go | Phase 1 | Golden fixtures for toroidal neighbors, collision, capture, forbidden points, pass, scoring |
| Lifecycle controls race each other | Phase 2; Phase 4 | Concurrent step, autorun/pause, stop/cancel, and stale-response tests |
| Private transcript inspection becomes prompt injection | Phase 3; Phase 4 | Visibility matrix tests; UI toggles do not change future prompt payloads |

## Phase-Specific Research Flags

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Phase 1 engine | Rule ambiguity around two-stage captures and forbidden updates | Write examples before code; make every ambiguous rule a golden fixture |
| Phase 2 orchestration | Simultaneity and lifecycle races | Use fake spy/delay agents and per-game turn locks from the start |
| Phase 3 persistence/privacy | Audit schema too thin or privacy enforced only in UI | Server-side transcript views, visibility matrix, replay tests, explicit transactions |
| Phase 4 UI/events | Event stream drift and optimistic board rendering | Backend state reload on reconnect; event sequence numbers; no local rule resolution |
| Phase 5 providers | Real API errors, malformed output, and cost/rate-limit surprises | Provider error matrix, bounded retries, manual intervention mode, fake-first gate |
| Phase 6 hardening | Retention/export accidentally leaks private debug data | Separate public/private/debug export modes and add retention decisions |
| v2 CLI adapters | Shared CLI auth/session caches | Separate per-seat working/config dirs; treat CLI auth files as secrets |

## Sources

- `/Users/gcao/proj/graygo-arena/.planning/PROJECT.md` - project constraints and active requirements. Confidence: HIGH.
- `/Users/gcao/proj/graygo-arena/.planning/REQUIREMENTS.md` - requirement ids and unresolved phase mapping. Confidence: HIGH.
- `/Users/gcao/proj/graygo-arena/docs/design.md` - architecture, data model, provider order, prompt/privacy policy, and minimal implementation plan. Confidence: HIGH.
- OpenAI API authentication docs: https://developers.openai.com/api/reference/overview#authentication - bearer-token backend auth boundary. Confidence: HIGH.
- OpenAI structured output docs: https://developers.openai.com/api/docs/guides/structured-outputs - structured JSON schema support and strict schema usage. Confidence: HIGH.
- OpenAI error/rate-limit docs: https://developers.openai.com/api/docs/guides/error-codes#api-errors - provider error handling and backoff guidance. Confidence: HIGH.
- Anthropic API error docs: https://platform.claude.com/docs/en/api/errors - auth, billing, rate-limit, timeout, overload, request id, and request-size behavior. Confidence: HIGH.
- SQLite transaction docs: https://www.sqlite.org/lang_transaction.html - explicit transaction behavior, write contention, rollback considerations. Confidence: HIGH.
- SQLite WAL docs: https://www.sqlite.org/wal.html - local persistence concurrency/checkpoint tradeoffs. Confidence: HIGH.
- OWASP Secrets Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html - secret storage, monitoring, encryption, and detection practices. Confidence: HIGH.

---
*Pitfalls research for: local-first AI-vs-AI simultaneous Gray Go arena*
*Researched: 2026-04-25*
