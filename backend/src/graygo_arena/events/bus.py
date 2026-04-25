"""Minimal SSE event formatting."""

from __future__ import annotations

from collections.abc import Iterable

from graygo_arena.application.models import GameEvent


def sse_payloads(events: Iterable[GameEvent]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "event": event.event_type,
            "id": event.id,
            "data": event.payload,
        }
        for event in events
    )
