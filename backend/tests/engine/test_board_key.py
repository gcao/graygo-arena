import pytest

from graygo_arena.engine import Board, Coordinate

EMPTY_7X7 = "+++++++/+++++++/+++++++/+++++++/+++++++/+++++++/+++++++"


def test_empty_board_key_matches_design_example() -> None:
    assert Board.empty(7).to_key() == EMPTY_7X7


def test_board_key_round_trips() -> None:
    key = "B++++++/+W+++++/++G++++/+++++++/+++++++/+++++++/+++++++"
    assert Board.from_key(key).to_key() == key


def test_with_cell_returns_new_board() -> None:
    board = Board.empty(7)
    updated = board.with_cell(Coordinate.parse("d4", size=7), "B")

    assert board.to_key() == EMPTY_7X7
    assert updated.to_key() == "+++++++/+++++++/+++++++/+++B+++/+++++++/+++++++/+++++++"


@pytest.mark.parametrize(
    "key",
    [
        "",
        "++/++",
        "+++/++/+++",
        "+++/+X+/+++",
        "+++/+++/+++/",
        "/+++/+++/+++",
    ],
)
def test_board_key_rejects_malformed_keys(key: str) -> None:
    with pytest.raises(ValueError):
        Board.from_key(key)
