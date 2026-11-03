from graygo_arena.application.models import SeatSession
from graygo_arena.application.prompt_builder import build_move_request
from graygo_arena.engine import Board, ForbiddenState
from graygo_arena.engine.coordinates import Coordinate


def test_move_request_excludes_own_forbidden_points_from_legal_moves() -> None:
    board = Board.from_key(
        "BBB+WBWBB/+++W+WWB+/+++++++++/+WW+++W++/+W+WW++++/"
        "BBW+G+BB+/B+GW+B++B/+B+BBB+BB/B+BW+BB++"
    )
    forbidden = ForbiddenState(black=frozenset({Coordinate.parse("f4", size=9)}))
    seat = SeatSession(
        id="seat_black",
        game_id="game_1",
        color="black",
        provider="graygo_trained",
        model="champion",
        credential_ref="local_file",
    )

    request = build_move_request(
        game_id="game_1",
        seat=seat,
        board=board,
        forbidden=forbidden,
        public_history=(),
        private_history=(),
        turn_index=40,
    )

    assert request.own_forbidden == ("f4",)
    assert "f4" not in request.legal_moves
    assert "a4" in request.legal_moves
    assert "PASS" in request.legal_moves
