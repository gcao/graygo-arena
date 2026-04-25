import pytest

from graygo_arena.engine import (
    Board,
    Coordinate,
    ForbiddenState,
    Move,
    PassMove,
    legal_moves,
    parse_move,
)


def labels(moves: tuple[Move | PassMove, ...]) -> set[str]:
    return {move.label for move in moves}


def test_parse_pass_move() -> None:
    assert parse_move("PASS", size=7) == PassMove()


def test_parse_coordinate_move() -> None:
    assert parse_move("d4", size=7) == Move(Coordinate(row=3, col=3))


def test_legal_moves_include_empty_cells_and_pass() -> None:
    board = Board.empty(3)

    assert labels(legal_moves(board, "black", ForbiddenState())) == {
        "a1",
        "a2",
        "a3",
        "b1",
        "b2",
        "b3",
        "c1",
        "c2",
        "c3",
        "PASS",
    }


def test_legal_moves_exclude_occupied_cells() -> None:
    board = (
        Board.empty(3)
        .with_cell(Coordinate.parse("a1", size=3), "B")
        .with_cell(Coordinate.parse("a2", size=3), "W")
        .with_cell(Coordinate.parse("a3", size=3), "G")
    )

    move_labels = labels(legal_moves(board, "black", ForbiddenState()))

    assert "a1" not in move_labels
    assert "a2" not in move_labels
    assert "a3" not in move_labels
    assert "PASS" in move_labels


def test_forbidden_points_are_color_specific() -> None:
    forbidden = ForbiddenState(
        black=frozenset({Coordinate.parse("b2", size=3)}),
        white=frozenset({Coordinate.parse("c3", size=3)}),
    )
    board = Board.empty(3)

    black_labels = labels(legal_moves(board, "black", forbidden))
    white_labels = labels(legal_moves(board, "white", forbidden))

    assert "b2" not in black_labels
    assert "b2" in white_labels
    assert "c3" in black_labels
    assert "c3" not in white_labels


@pytest.mark.parametrize("value", ["pass", "D4", "h1", "a0"])
def test_parse_move_rejects_invalid_place_moves(value: str) -> None:
    with pytest.raises(ValueError):
        parse_move(value, size=7)
