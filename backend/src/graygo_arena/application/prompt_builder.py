"""Privacy-preserving provider request construction."""

from __future__ import annotations

from graygo_arena.application.models import ProviderMoveRequest, SeatSession
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
) -> ProviderMoveRequest:
    moves = legal_moves(board, seat.color, forbidden)
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
    )
