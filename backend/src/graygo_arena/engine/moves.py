"""Move parsing and legal-move validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from graygo_arena.engine.board import Board
from graygo_arena.engine.coordinates import Coordinate

type SeatColor = Literal["black", "white"]


@dataclass(frozen=True)
class PassMove:
    label: Literal["PASS"] = "PASS"


@dataclass(frozen=True)
class Move:
    coordinate: Coordinate

    @property
    def label(self) -> str:
        return self.coordinate.to_label()


type MoveLike = Move | PassMove


def _empty_forbidden() -> frozenset[Coordinate]:
    return frozenset()


@dataclass(frozen=True)
class ForbiddenState:
    black: frozenset[Coordinate] = field(default_factory=_empty_forbidden)
    white: frozenset[Coordinate] = field(default_factory=_empty_forbidden)

    def for_color(self, color: SeatColor) -> frozenset[Coordinate]:
        if color == "black":
            return self.black
        if color == "white":
            return self.white
        msg = f"unsupported color: {color}"
        raise ValueError(msg)


def parse_move(value: str, size: int) -> MoveLike:
    if value == "PASS":
        return PassMove()
    return Move(Coordinate.parse(value, size))


def legal_moves(board: Board, color: SeatColor, forbidden: ForbiddenState) -> tuple[MoveLike, ...]:
    forbidden_coordinates = forbidden.for_color(color)
    moves: list[MoveLike] = []
    for row in range(board.size):
        for col in range(board.size):
            coordinate = Coordinate(row=row, col=col)
            if board.get(coordinate) == "+" and coordinate not in forbidden_coordinates:
                moves.append(Move(coordinate))
    moves.append(PassMove())
    return tuple(moves)
