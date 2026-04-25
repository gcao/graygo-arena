# Feature Research: Gray Go Arena

**Domain:** Local-first AI-vs-AI simultaneous-turn board game arena
**Researched:** 2026-04-25
**Confidence:** HIGH for v1 scope and anti-features; MEDIUM for v1.x/v2 because those should follow validation data.

## Feature Thesis

Gray Go Arena should feel like a local operator console, not a hosted SaaS game. The v1 product should prove three things: the backend is the only game authority, both AI seats act from the same pre-move board without peeking, and the human operator can inspect enough evidence to trust the result. Every feature should reinforce one of those claims.

For v1, prioritize deterministic game correctness, seat isolation, backend-only credentials, fake/scripted agents, direct OpenAI/Anthropic adapters, live inspection, and replayable local persistence. For v1.x, add features that improve repeatability, comparison, export, and debugging after the core loop works. For v2, consider tournaments, hosted collaboration, CLI/local-model adapters, and plugin surfaces only after the local privacy model is proven.

## Table Stakes

Features users of a developer/operator arena will expect. Missing these makes the product feel incomplete or unsafe.

| Feature | Target | Why Expected | Complexity | Notes |
|---------|--------|--------------|------------|-------|
| Deterministic Gray Go engine | v1 | The arena is meaningless if rule resolution is inconsistent. | HIGH | Backend owns board state, legal moves, collision-to-gray, toroidal liberties, two-stage captures, forbidden points, pass handling, and scoring. |
| Simultaneous-turn orchestrator | v1 | The core product promise is fair simultaneous play. | HIGH | Both seats must be prompted from the same pre-board and BoardKey before either pending move can affect the other seat. |
| Isolated Black and White seat sessions | v1 | Same-model and same-provider matches are a first-class use case. | HIGH | Separate prompt history, provider conversation/reference IDs, private summaries, raw responses, and any future CLI state per seat. |
| Backend-only credential aliases | v1 | Operator tools that call paid APIs must not expose secrets in browser code. | MEDIUM | UI sees provider/model/credential aliases and configured status only. Token values stay in backend env/key management. |
| Fake random and deterministic scripted agents | v1 | Local validation should not require paid model calls. | MEDIUM | Use these to test engine, orchestrator, API, UI, and regression cases before OpenAI/Anthropic adapters. |
| Provider discovery and health test | v1 | Operators need to know what can run before creating a game. | MEDIUM | `GET /api/providers` and provider test calls return safe metadata, readiness, latency, and error details without tokens. |
| Direct OpenAI and Anthropic adapters | v1 | Real AI-vs-AI matches are the product's validation path. | HIGH | Implement after fake/scripted agents. Use strict structured move parsing and server-side validation. |
| Structured move output contract | v1 | LLMs will produce malformed or stale output unless constrained. | MEDIUM | Require JSON with BoardKey, move, board echo for diagnostics, and concise strategic summary. Validate server-side. |
| Invalid-output policy | v1 | Long-running arena sessions need deterministic failure behavior. | MEDIUM | Retry malformed/illegal output once, then apply configured policy: pass, forfeit, or manual intervention. Default to manual intervention during early validation. |
| Local persistence of games, turns, boards, calls, and transcripts | v1 | Inspection and debugging require durable evidence. | HIGH | SQLite first. Persist credential references only, never token values. |
| REST game lifecycle API | v1 | UI and automation need clear control points. | MEDIUM | Create, start, pause, resume, stop, step, autorun, current state, turn history, and transcript endpoints. |
| Live event stream | v1 | Humans need to watch turns resolve without refreshing. | MEDIUM | SSE is enough for v1; WebSocket can follow if bidirectional controls need it. |
| New Game configuration UI | v1 | Operators need to configure seats, providers, models, board size, ruleset, run mode, and visibility. | MEDIUM | Include explicit notice when both seats use the same model: backend creates isolated seat sessions. |
| Live board inspector | v1 | Board games need an inspectable canonical board. | MEDIUM | Coordinates, B/W/G/+ symbols, last moves, collisions, captures, forbidden points, score estimate, and cell details. |
| Turn resolution audit panel | v1 | Trust depends on seeing how a turn was resolved. | MEDIUM | Show pre-BoardKey, both moves, validation status, collision/capture/forbidden updates, post-BoardKey, and errors. |
| Transcript views with privacy boundaries | v1 | Operators need public and seat-private evidence without contaminating prompts. | HIGH | Public view, Black-private view, White-private view, and debug view. Private views are human-visible only when enabled and never injected into opponent prompts. |
| Game history and resume/read-only inspection | v1 | Local tools should preserve prior experiments. | MEDIUM | History list, turn drilldown, finished/error status, and read-only transcript inspection. |
| Basic JSON export | v1.x | Local-first users expect data portability. | LOW | Export game bundle with board history, turn audits, prompts/responses, metadata, and redacted credential refs. |

## Differentiators

Features that make Gray Go Arena more than a generic chat-with-two-models demo.

| Feature | Target | Value Proposition | Complexity | Notes |
|---------|--------|-------------------|------------|-------|
| Fairness proof per turn | v1 | Makes simultaneity auditable, not just promised. | MEDIUM | Store both prompt hashes, same pre-BoardKey, call start/end times, and resolution inputs. |
| Seat isolation proof | v1 | Builds confidence that same-model matches are valid. | MEDIUM | Expose per-seat session IDs, prompt-context summaries, and "not included" private-context checks in debug view. |
| Gray Go-specific resolution visualization | v1 | Explains simultaneous collision and capture behavior better than a generic board grid. | MEDIUM | Highlight collision-to-gray, capture stages, forbidden updates, and toroidal neighbors. |
| Deterministic regression scenarios | v1 | Lets engine and orchestrator bugs be caught before paid calls. | MEDIUM | Scripted agents plus named scenario fixtures for collisions, captures, passes, and illegal moves. |
| Provider comparison metrics | v1.x | Turns games into useful model behavior experiments. | HIGH | Track invalid-rate, pass-rate, collision-rate, latency, token usage, cost estimate, and win/loss by model alias. |
| Replayable redacted game bundles | v1.x | Makes bugs and notable games portable without leaking secrets. | MEDIUM | Bundle includes version, ruleset, prompts, raw outputs, parsed moves, audits, and no token values. |
| Prompt and strategy profile presets | v1.x | Operators can compare model behavior under controlled prompt variants. | MEDIUM | Keep presets backend-managed and versioned; never allow prompts to override backend authority. |
| Privacy/leakage audit mode | v1.x | Directly protects the product's hardest trust boundary. | HIGH | Diff prompt inputs by seat, scan for opponent-private terms, verify pending moves are absent before calls. |
| Batch match runner | v1.x | Enables local model/provider benchmarking without full v2 tournaments. | MEDIUM | Run N games with seed/config matrix and summarized outcomes. |
| Tournament ladder and ranking | v2 | Adds replay value and systematic evaluation. | HIGH | Requires robust persistence, batching, exports, and provider cost controls first. |
| CLI and local-model adapters with seat sandboxes | v2 | Opens Codex/Claude Code/local agents without compromising isolation. | HIGH | Needs separate working dirs/config homes, subprocess limits, redaction, timeouts, and cleanup. |
| Hosted or collaborative mode | v2 | Allows sharing matches or remote operators. | HIGH | Requires auth, tenancy, secret isolation, audit logging, retention policy, and stronger threat modeling. |

## Anti-Features

Features that may be requested but should be rejected or deferred because they break backend authority, secret handling, seat isolation, privacy, or v1 scope.

| Anti-Feature | Why Requested | Why Problematic | What to Do Instead |
|--------------|---------------|-----------------|--------------------|
| Browser-side provider API tokens | Easy setup from the UI. | Secret handling failure: browser code, network traces, local storage, crash reports, and screenshots can expose paid API keys. | Backend-only env/key-management configuration; UI shows configured aliases only. |
| AI-authored board updates | Seems simpler than implementing all rules. | Backend authority failure: models will eventually create illegal boards, missed captures, or stale state. | Models choose moves only; backend engine computes all board changes. |
| Shared provider conversation between seats | Saves tokens and implementation work. | Seat isolation failure: Black and White can inherit each other's private summaries, raw outputs, or response-chain state. | Create two independent seat sessions even for the same provider/model/credential. |
| Feeding opponent private transcript into prompts | Makes agents appear more strategic. | Privacy and fairness failure: future moves become contaminated by information the opponent should not have. | Only public resolved history is shared; each seat may receive its own prior private summaries. |
| Revealing pending move before both calls return | Improves UI drama or lets one side react. | Simultaneity failure: one seat can peek or appear to peek. | Show "thinking" status only until both moves are validated and resolved. |
| Chain-of-thought capture or display | Operators may want deeper reasoning. | Privacy, policy, and noise risk; also encourages treating model reasoning as authoritative. | Request concise visible strategic summaries and candidate-move comparisons. |
| Prompt fields that can override backend rules | Power users may want custom experiments. | Authority failure: prompts can tell models to update boards, ignore legal moves, or leak private state. | Versioned strategy profiles may tune style, but backend rules and output schema are immutable per ruleset. |
| Production multi-user auth in v1 | Makes the app feel launch-ready. | Major scope and privacy expansion: tenancy, authorization, audit retention, admin roles, and hosted secret handling. | Keep v1 local/trusted; design data boundaries so auth can be added later. |
| Cloud sync or telemetry by default | Useful for support and analytics. | Local-first privacy failure: transcripts and raw model outputs are sensitive experiment data. | Local storage by default; explicit redacted export or opt-in telemetry only after validation. |
| CLI adapters before direct APIs | Lets Codex/Claude Code play immediately. | Operationally fragile and isolation-heavy: cached auth, workdirs, subprocess state, logs, file access, and cleanup can leak between seats. | Ship fake/scripted plus direct OpenAI/Anthropic first; add CLI adapters after sandbox design. |
| PostgreSQL-first or cloud database-first deployment | Feels more scalable. | Adds setup burden before local product value is proven. | SQLite v1 with schema discipline; add PostgreSQL when concurrent operators or hosted mode require it. |
| Full ruleset editor or many game variants in v1 | Broadens appeal. | Dilutes engine correctness and test coverage for Gray Go. | Freeze `graygo-v1`; add variants only after core resolution has regression coverage. |
| Autonomous provider key creation or account management | Reduces setup friction. | Expands trust boundary and increases risk of secret leakage or billing surprises. | Document backend env configuration and provider test endpoint. |
| Raw transcript sharing links | Easy collaboration. | Accidentally shares private reasoning, raw responses, prompts, and provider metadata. | Export redacted bundles with explicit operator action and visible privacy checklist. |

## Feature Dependencies

```text
Deterministic engine
  -> engine regression tests
  -> simultaneous-turn orchestrator
  -> fake/scripted agents
  -> REST lifecycle API
  -> Live Game UI
  -> direct provider adapters

Backend-only credential aliases
  -> provider discovery/test
  -> direct provider adapters
  -> provider comparison metrics

Seat session model
  -> isolated prompt builder
  -> transcript persistence
  -> privacy-preserving transcript UI
  -> leakage audit mode

Structured move schema + BoardKey validation
  -> invalid-output policy
  -> turn resolution audit
  -> replayable game bundles

SQLite persistence
  -> game history
  -> export/replay
  -> batch match runner
  -> tournament ladder

Event stream
  -> live board updates
  -> autorun visibility
  -> operator intervention on invalid output

Sandboxed runtime isolation
  -> CLI adapters
  -> local-model adapters
  -> hosted/collaborative mode
```

### Dependency Notes

- **Engine before providers:** Paid model calls cannot validate the product until rule resolution is deterministic and covered by scripted cases.
- **Seat sessions before transcripts:** Transcript views must be backed by isolation in the data model, not just UI filtering.
- **Credential aliases before provider config UI:** The frontend must never become a place where secrets are entered, displayed, cached, or replayed.
- **Persistence before export/replay:** Export should serialize an authoritative stored game, not scrape transient UI state.
- **Provider metrics after direct adapters:** Cost/latency/invalid-rate dashboards are useful only once real provider calls exist.
- **CLI adapters require sandbox design:** A subprocess provider is not just another HTTP adapter because local auth, config, filesystem, logs, and working directories become part of seat isolation.

## MVP Recommendation

### Launch With (v1)

- [ ] Deterministic Gray Go engine with regression tests for collision-to-gray, toroidal liberties, two-stage captures, forbidden points, pass handling, and scoring.
- [ ] Simultaneous-turn orchestrator that creates games, prompts both seats from the same pre-board, validates moves, resolves turns, persists results, and exposes step/autorun controls.
- [ ] Seat session model with strict Black/White isolation, including separate prompt histories, private summaries, raw responses, and provider state references.
- [ ] Fake random and deterministic scripted agents for cheap end-to-end validation.
- [ ] Backend-only provider credential aliases, provider discovery, and provider health testing.
- [ ] Direct OpenAI and Anthropic adapters using structured move output, server-side JSON/BoardKey validation, timeouts, token/latency capture, and invalid-output retry policy.
- [ ] SQLite persistence for games, turns, boards, seat sessions, agent calls, public logs, and private transcripts, storing credential refs only.
- [ ] REST API plus SSE event stream for game lifecycle, current state, step, autorun, turns, transcript views, and provider status.
- [ ] React/TypeScript UI for New Game, Live Game, Game History, Provider Status, and Settings.
- [ ] Board inspector with coordinates, canonical symbols, last moves, collisions, captures, forbidden points, cell details, and toroidal-neighbor visualization.
- [ ] Turn audit and transcript inspector with public, Black-private, White-private, and debug views that never feed opponent-private content back into prompts.
- [ ] Basic local error handling: provider timeout, malformed response, illegal move, manual intervention mode, retry-then-pass, retry-then-forfeit.

**v1 priority call:** Do not split effort across many adapters. Ship fake/scripted plus OpenAI and Anthropic direct APIs. That is enough to validate the arena, fairness model, UI, persistence, and transcript boundaries.

### Post-Validation Features (v1.x)

Add these after v1 proves local games can run end to end and operators have real transcript/debug feedback.

| Feature | Trigger | Complexity | Notes |
|---------|---------|------------|-------|
| Redacted game export/import | Operators need to share bugs or notable games. | MEDIUM | Make export explicit and show exactly which transcript classes are included. |
| Deterministic replay viewer | Operators need to re-check resolution without re-calling models. | MEDIUM | Rehydrate stored turns and step through board states from persisted data. |
| Batch match runner | Operators want repeated trials for a config pair. | MEDIUM | Use seeded scripted/fake agents and real providers with max-cost/turn caps. |
| Provider comparison dashboard | Enough games exist to compare behavior. | HIGH | Show win/loss, invalid moves, collisions, latency, token usage, and estimated cost by model alias. |
| Prompt/profile presets | Operators are repeatedly editing prompt style. | MEDIUM | Version profile configs; do not allow profile changes to alter authoritative rules. |
| Leakage audit mode | Same-model or same-provider tests need stronger proof. | HIGH | Store prompt-context manifests and flag opponent-private content before a provider call. |
| Redaction and retention controls | Transcript data starts accumulating. | MEDIUM | Per-game delete, raw-response retention toggle, and export redaction defaults. |
| OpenTelemetry-compatible local traces | Debugging spans multiple API/provider/orchestrator steps. | MEDIUM | Correlate game, turn, seat, provider call, and validation IDs without sending telemetry by default. |
| Cost and budget guardrails | Real model calls become routine. | MEDIUM | Per-game max turns, max tokens, max estimated spend, and stop-on-threshold. |

### Future Considerations (v2)

- [ ] Tournament ladder, Elo-like rankings, and scheduled match matrices. Defer until batch runs, replay, exports, and provider metrics are stable.
- [ ] CLI adapters for Codex and Claude Code. Defer until each seat can run in a separate filesystem/config/auth sandbox with strict timeouts and cleanup.
- [ ] Local model adapter. Defer until the provider abstraction can represent local inference latency, availability, and model-specific structured-output limitations.
- [ ] Human seat or human override mode. Useful for debugging and demonstrations, but not required to validate AI-vs-AI fairness.
- [ ] Hosted/collaborative deployment. Requires auth, tenancy, server-side secret management, retention controls, encrypted storage strategy, and threat modeling.
- [ ] Rule variants and plugin rulesets. Defer until `graygo-v1` has stable engine coverage and exported replay compatibility.
- [ ] Public match gallery. Only after redaction, consent, and transcript classification are robust.
- [ ] External eval integration. Useful later, but v1 should keep the canonical artifact as local game/turn/agent-call records.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Deterministic engine | HIGH | HIGH | P1 |
| Simultaneous orchestrator | HIGH | HIGH | P1 |
| Seat isolation | HIGH | HIGH | P1 |
| Backend-only credential aliases | HIGH | MEDIUM | P1 |
| Fake/scripted agents | HIGH | MEDIUM | P1 |
| Structured move validation | HIGH | MEDIUM | P1 |
| REST lifecycle API | HIGH | MEDIUM | P1 |
| SQLite persistence | HIGH | HIGH | P1 |
| Live board and audit UI | HIGH | MEDIUM | P1 |
| Transcript inspector | HIGH | HIGH | P1 |
| Direct OpenAI/Anthropic adapters | HIGH | HIGH | P1 |
| SSE live updates | MEDIUM | MEDIUM | P1 |
| Basic JSON export | MEDIUM | LOW | P2 |
| Replay viewer | MEDIUM | MEDIUM | P2 |
| Provider comparison metrics | MEDIUM | HIGH | P2 |
| Leakage audit mode | HIGH | HIGH | P2 |
| Batch match runner | MEDIUM | MEDIUM | P2 |
| CLI adapters | MEDIUM | HIGH | P3 |
| Hosted/collaborative mode | MEDIUM | HIGH | P3 |
| Tournament ladder | MEDIUM | HIGH | P3 |

**Priority key:** P1 = launch requirement; P2 = post-validation v1.x; P3 = v2 or later.

## Roadmap Guidance

Recommended phase order:

1. **Engine correctness:** Pure Gray Go engine and regression fixtures.
2. **Local orchestration:** In-memory games, seat sessions, fake/scripted agents, and one-turn stepping.
3. **Persistence and API:** SQLite schema, REST lifecycle, turn history, transcript endpoints, and event stream.
4. **Operator UI:** New Game, Live Game, board inspector, audit panel, history, provider status, and settings.
5. **Direct providers:** OpenAI and Anthropic adapters with structured output, retries, timeouts, and provider call records.
6. **Trust hardening:** Export, replay, redaction, leakage audit, and budget guardrails.
7. **Scale and extension:** Batch runs, comparison dashboards, tournaments, CLI/local adapters, and hosted mode.

## Sources

- Local project context: `/Users/gcao/proj/graygo-arena/.planning/PROJECT.md`
- Local design context: `/Users/gcao/proj/graygo-arena/docs/design.md`
- Research template: `/Users/gcao/.codex/get-shit-done/templates/research-project/FEATURES.md`
- OpenAI API authentication docs: https://platform.openai.com/docs/api-reference/authentication
- Anthropic API getting started and Messages docs: https://docs.anthropic.com/en/api/getting-started and https://docs.anthropic.com/en/api/messages-examples
- OWASP Secrets Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- LangSmith observability concepts for LLM traces: https://docs.langchain.com/langsmith/observability-concepts
- OpenTelemetry overview for traces/metrics/logs correlation: https://opentelemetry.io/
- Ink & Switch local-first software paper: https://www.inkandswitch.com/essay/local-first/local-first.pdf

---
*Feature research for: Gray Go Arena*
*Researched: 2026-04-25*
