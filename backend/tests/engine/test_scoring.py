import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from graygo_arena.engine import Board, score_board


@pytest.mark.parametrize(
    ("key", "black", "white"),
    [
        ("BBB/B+B/BBB", 9.0, 0.0),
        ("WWW/W+W/WWW", 0.0, 9.0),
        ("GGG/G+G/GGG", 4.5, 4.5),
        ("BBB/B+W/BBB", 7.5, 1.5),
        ("BBB/B+G/BBB", 8.25, 0.75),
        ("WWW/W+G/WWW", 0.75, 8.25),
        ("BWB/G+G/BBB", 6.5, 2.5),
        ("+++/+++/+++", 4.5, 4.5),
        ("BBB/WWG/GGB", 5.5, 3.5),
    ],
)
def test_stones_and_each_territory_boundary_combination(
    key: str, black: float, white: float
) -> None:
    board = Board.from_key(key)
    assert score_board(board) == {"black": black, "white": white}
    # Even stones without liberties are counted; scoring never marks groups dead.
    assert board.to_key() == key


@pytest.mark.parametrize("key", ["+BB/BBB/WBB", "+BW/BBB/BBB"])
def test_territory_sees_opposite_color_across_both_wrapped_edges(key: str) -> None:
    assert score_board(Board.from_key(key)) == {"black": 7.5, "white": 1.5}


def test_empty_region_joins_across_the_seam_before_dividing_territory() -> None:
    board = Board.from_key("++BBB/BBBBB/BBBBB/WBBBB/+WBBW")
    assert score_board(board) == {"black": 20.5, "white": 4.5}


@given(st.lists(st.sampled_from("+BWG"), min_size=25, max_size=25))
@settings(max_examples=40)
def test_scores_cover_the_board_and_are_symmetric_under_color_swap(cells: list[str]) -> None:
    key = "/".join("".join(cells[row : row + 5]) for row in range(0, 25, 5))
    score = score_board(Board.from_key(key))
    swapped = score_board(Board.from_key(key.translate(str.maketrans("BW", "WB"))))
    assert score["black"] + score["white"] == 25
    assert score["black"] >= 0 and score["white"] >= 0
    assert swapped == {"black": score["white"], "white": score["black"]}
