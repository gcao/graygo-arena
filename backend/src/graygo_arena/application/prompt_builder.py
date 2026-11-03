"""Privacy-preserving provider request construction."""

from __future__ import annotations

from graygo_arena.application.models import (
    ProviderMoveRequest,
    PublicRuleRound,
    SeatSession,
    TurnRecord,
)
from graygo_arena.engine import Board, ForbiddenState, legal_moves


def build_move_request(
    *,
    game_id: str,
    seat: SeatSession,
    board: Board,
    forbidden: ForbiddenState,
    public_history: tuple[str, ...],
    private_history: tuple[str, ...],
    turn_index: int,
    turns: tuple[TurnRecord, ...] = (),
    max_turns: int = 200,
    mutual_pass_streak: int = 0,
) -> ProviderMoveRequest:
    moves = legal_moves(board, seat.color, forbidden)
    own_forbidden = forbidden.for_color(seat.color)
    opponent_forbidden = forbidden.for_color("white" if seat.color == "black" else "black")
    return ProviderMoveRequest(
        game_id=game_id,
        seat_session_id=seat.id,
        color=seat.color,
        model=seat.model,
        board_key=board.to_key(),
        board_rows=tuple(board.to_key().split("/")),
        legal_moves=tuple(move.label for move in moves),
        public_history=public_history,
        private_history=private_history,
        turn_index=turn_index,
        rule_history=tuple(
            PublicRuleRound(tuple(turn.pre_board_key.split("/")), turn.black_move, turn.white_move)
            for turn in turns
            if turn.turn_index < turn_index
        )[-2:],
        max_turns=max_turns,
        mutual_pass_streak=mutual_pass_streak,
        own_forbidden=tuple(coordinate.to_label() for coordinate in sorted(own_forbidden)),
        opponent_forbidden=tuple(
            coordinate.to_label() for coordinate in sorted(opponent_forbidden)
        ),
    )
