"""Per-player no-change restrictions and non-reverting two-round repetition."""

from __future__ import annotations

from dataclasses import dataclass

from graygo_arena.engine.board import Board
from graygo_arena.engine.moves import ForbiddenState, Move, MoveLike, parse_move


@dataclass(frozen=True)
class RoundHistory:
    pre_board_key: str
    black_move: str
    white_move: str


def forbidden_after_round(
    before: Board,
    after: Board,
    previous: ForbiddenState,
    black_move: MoveLike,
    white_move: MoveLike,
    history: tuple[RoundHistory, ...],
) -> ForbiddenState:
    matching = tuple(round_ for round_ in history if round_.pre_board_key == after.to_key())
    black, white = set(previous.black), set(previous.white)
    if before != after and not matching:
        black.clear()
        white.clear()
    if before == after:
        if isinstance(black_move, Move):
            black.add(black_move.coordinate)
        if isinstance(white_move, Move):
            white.add(white_move.coordinate)
    for round_ in matching:
        past_black = parse_move(round_.black_move, before.size)
        past_white = parse_move(round_.white_move, before.size)
        if isinstance(past_black, Move):
            black.add(past_black.coordinate)
        if isinstance(past_white, Move):
            white.add(past_white.coordinate)
    return ForbiddenState(black=frozenset(black), white=frozenset(white))
