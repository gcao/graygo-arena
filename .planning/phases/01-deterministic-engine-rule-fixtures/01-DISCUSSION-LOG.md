# Phase 1: Deterministic Engine & Rule Fixtures - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 1 - Deterministic Engine & Rule Fixtures
**Mode:** Auto
**Areas discussed:** Engine authority, rule semantics, board and move shape, testing strategy

---

## Engine Authority

| Option | Description | Selected |
|--------|-------------|----------|
| Backend engine only | Backend computes all board/rule outcomes; models later select moves only. | yes |
| Shared authority | Let model diagnostics influence board/capture/scoring state. | |
| Defer authority boundary | Decide during provider integration. | |

**Auto choice:** Backend engine only.
**Notes:** This is the core project invariant from `docs/design.md` and `.planning/PROJECT.md`.

---

## Rule Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Freeze `graygo-v1` and fixture every ambiguity | Keep one ruleset and convert unclear edge cases into fixtures before coding. | yes |
| Add rule variants early | Make the engine configurable for multiple rule variants in Phase 1. | |
| Implement likely behavior and revisit later | Move quickly without locking fixtures first. | |

**Auto choice:** Freeze `graygo-v1` and fixture every ambiguity.
**Notes:** Rule variants are out of scope. Fixture-first handling prevents ordinary-Go assumptions from leaking into Gray Go.

---

## Board and Move Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Match the design document | Use `+`, `B`, `W`, `G`, lowercase row plus 1-based column coordinates, `PASS`, and slash-separated BoardKey rows. | yes |
| Use hashed BoardKeys only | Store opaque hashes instead of human-readable board keys. | |
| Choose implementation-local notation | Let code choose whatever internal notation is simplest. | |

**Auto choice:** Match the design document.
**Notes:** Human-readable BoardKeys are useful for prompts, transcripts, tests, and operator inspection.

---

## Testing Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Golden fixtures plus property tests | Use named examples for every rule mechanic and property checks for invariants. | yes |
| Unit tests only | Handwrite direct unit tests without fixture files or property checks. | |
| Add tests after implementation | Build engine first, then backfill coverage. | |

**Auto choice:** Golden fixtures plus property tests.
**Notes:** This aligns with Phase 1 success criteria and the research warning that Gray Go edge cases must be locked early.

---

## the agent's Discretion

- Exact Python module names and helper boundaries.
- Fixture file format, as long as it is deterministic and readable.
- How to split scoring/forbidden-update ambiguity into explicit spec or fixture tasks.

## Deferred Ideas

- Fake/scripted agents, API, persistence, UI, provider adapters, replay/export, and trust hardening remain in later phases.
