"""Zero-cost fake and scripted provider adapters."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from graygo_arena.application.models import (
    ProviderMoveRequest,
    ProviderMoveResponse,
    SeatSession,
)


def _empty_indexes() -> dict[str, int]:
    return {}


class FakeRandomProvider:
    def __init__(self, *, seed: int = 0) -> None:
        self._seed = seed

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        choices = tuple(move for move in request.legal_moves if move != "PASS") or ("PASS",)
        rng = random.Random(f"{self._seed}:{seat.id}:{request.turn_index}:{request.board_key}")
        move = rng.choice(choices)
        return ProviderMoveResponse(
            board_key=request.board_key,
            move=move,
            raw_response=f"fake_random selected {move}",
            strategic_summary="Deterministic fake random move.",
        )


class ScriptedCenterProvider:
    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        size = len(request.board_rows)
        center = f"{chr(ord('a') + size // 2)}{size // 2 + 1}"
        move = center if center in request.legal_moves else _first_non_pass(request.legal_moves)
        return ProviderMoveResponse(
            board_key=request.board_key,
            move=move,
            raw_response=f"scripted_center selected {move}",
            strategic_summary="Choose the center-like point when legal.",
        )


class ScriptedPassProvider:
    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        return ProviderMoveResponse(
            board_key=request.board_key,
            move="PASS",
            raw_response="scripted_pass selected PASS",
            strategic_summary="Pass immediately.",
        )


@dataclass
class ScriptedSequenceProvider:
    fallback: str = "PASS"
    _indexes: dict[str, int] = field(default_factory=_empty_indexes)

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        index = self._indexes.get(seat.id, 0)
        script = seat.script or (self.fallback,)
        candidate = script[min(index, len(script) - 1)]
        self._indexes[seat.id] = index + 1
        move = candidate if candidate in request.legal_moves else self.fallback
        return ProviderMoveResponse(
            board_key=request.board_key,
            move=move,
            raw_response=f"scripted_sequence selected {move}",
            strategic_summary=f"Script index {index}.",
        )


def _first_non_pass(legal_moves: tuple[str, ...]) -> str:
    return next((move for move in legal_moves if move != "PASS"), "PASS")
