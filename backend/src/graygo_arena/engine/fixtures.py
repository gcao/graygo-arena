"""Golden fixture loading for engine regression cases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from graygo_arena.engine.board import Board
from graygo_arena.engine.coordinates import Coordinate
from graygo_arena.engine.moves import ForbiddenState, MoveLike, parse_move
from graygo_arena.engine.resolution import GameState


@dataclass(frozen=True)
class EngineCase:
    name: str
    state: GameState
    black_move: MoveLike
    white_move: MoveLike
    post_board_key: str
    expected_event_types: tuple[str, ...]


def load_engine_cases(path: Path) -> tuple[EngineCase, ...]:
    raw_cases = cast(list[dict[str, object]], json.loads(path.read_text(encoding="utf-8")))
    return tuple(_case_from_dict(raw_case) for raw_case in raw_cases)


def _case_from_dict(raw_case: dict[str, object]) -> EngineCase:
    name = _required_str(raw_case, "name")
    size = _required_int(raw_case, "size")
    forbidden = _forbidden_from_dict(_required_dict(raw_case, "forbidden"), size)
    state = GameState(
        board=Board.from_key(_required_str(raw_case, "pre_board_key")),
        forbidden=forbidden,
        double_pass_count=_required_int(raw_case, "double_pass_count"),
    )
    return EngineCase(
        name=name,
        state=state,
        black_move=parse_move(_required_str(raw_case, "black_move"), size=size),
        white_move=parse_move(_required_str(raw_case, "white_move"), size=size),
        post_board_key=_required_str(raw_case, "post_board_key"),
        expected_event_types=_expected_event_types(raw_case),
    )


def _forbidden_from_dict(raw_forbidden: dict[str, object], size: int) -> ForbiddenState:
    black_labels = _required_str_list(raw_forbidden, "black")
    white_labels = _required_str_list(raw_forbidden, "white")
    return ForbiddenState(
        black=frozenset(Coordinate.parse(value, size=size) for value in black_labels),
        white=frozenset(Coordinate.parse(value, size=size) for value in white_labels),
    )


def _expected_event_types(raw_case: dict[str, object]) -> tuple[str, ...]:
    raw_events = _required_list(raw_case, "expected_events")
    event_types: list[str] = []
    for raw_event in raw_events:
        if not isinstance(raw_event, dict):
            msg = "expected_events entries must be objects"
            raise ValueError(msg)
        event_types.append(_required_str(cast(dict[str, object], raw_event), "type"))
    return tuple(event_types)


def _required_str(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string"
        raise ValueError(msg)
    return value


def _required_int(raw: dict[str, object], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int):
        msg = f"{key} must be an integer"
        raise ValueError(msg)
    return value


def _required_dict(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        msg = f"{key} must be an object"
        raise ValueError(msg)
    return cast(dict[str, object], value)


def _required_list(raw: dict[str, object], key: str) -> list[object]:
    value = raw.get(key)
    if not isinstance(value, list):
        msg = f"{key} must be a list"
        raise ValueError(msg)
    return cast(list[object], value)


def _required_str_list(raw: dict[str, object], key: str) -> tuple[str, ...]:
    values = _required_list(raw, key)
    if not all(isinstance(value, str) for value in values):
        msg = f"{key} must be a list of strings"
        raise ValueError(msg)
    return tuple(cast(list[str], values))
