"""Redacted export bundle assembly."""

from __future__ import annotations

import re
from typing import cast

from graygo_arena.application.models import GameRepository

SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]+|sk-ant-[A-Za-z0-9_-]+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
)


def build_export_bundle(repository: GameRepository, game_id: str) -> dict[str, object]:
    game = repository.get_game(game_id)
    seats = repository.get_seats(game_id)
    turns = repository.list_turns(game_id)
    calls = repository.list_agent_calls(game_id)
    transcripts = repository.list_transcripts(game_id, "debug")
    events = repository.list_events(game_id)
    return cast(
        dict[str, object],
        _redact(
            {
                "version": "graygo-arena-export-v1",
                "game": {
                    "id": game.id,
                    "status": game.status,
                    "board_size": game.board_size,
                    "ruleset": game.ruleset,
                    "current_turn": game.current_turn,
                    "board_key": game.board.to_key(),
                    "double_pass_count": game.double_pass_count,
                    "max_turns": game.max_turns,
                },
                "seats": [
                    {
                        "id": seat.id,
                        "color": seat.color,
                        "provider": seat.provider,
                        "model": seat.model,
                        "credential_ref": seat.credential_ref,
                    }
                    for seat in seats
                ],
                "turns": [
                    {
                        "turn_index": turn.turn_index,
                        "pre_board_key": turn.pre_board_key,
                        "post_board_key": turn.post_board_key,
                        "black_move": turn.black_move,
                        "white_move": turn.white_move,
                        "status": turn.status,
                    }
                    for turn in turns
                ],
                "agent_calls": [
                    {
                        "turn_index": call.turn_index,
                        "seat_session_id": call.seat_session_id,
                        "color": call.color,
                        "provider": call.provider,
                        "model": call.model,
                        "prompt_board_key": call.prompt_board_key,
                        "parsed_move": call.parsed_move,
                        "valid": call.valid,
                        "error": call.error,
                        "attempt": call.attempt,
                        "raw_response": call.raw_response,
                    }
                    for call in calls
                ],
                "transcripts": [
                    {
                        "turn_index": transcript.turn_index,
                        "seat_session_id": transcript.seat_session_id,
                        "view": transcript.view,
                        "text": transcript.text,
                    }
                    for transcript in transcripts
                ],
                "events": [
                    {"id": event.id, "event_type": event.event_type, "payload": event.payload}
                    for event in events
                ],
            }
        ),
    )


def _redact(value: object) -> object:
    if isinstance(value, str):
        return SECRET_PATTERN.sub("[REDACTED]", value)
    if isinstance(value, list):
        return [_redact(item) for item in cast(list[object], value)]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in cast(tuple[object, ...], value))
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in cast(dict[object, object], value).items()}
    return value
