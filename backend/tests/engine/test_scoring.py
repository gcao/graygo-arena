from graygo_arena.engine import Board, score_board


def test_score_board_counts_black_and_white_stones_only() -> None:
    board = Board.from_key("B++/+WG/++B")

    assert score_board(board) == {"black": 2.0, "white": 1.0}
