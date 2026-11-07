import pytest

from graygo_arena.engine import (
    Board,
    Cell,
    Coordinate,
    GameState,
    Move,
    PassMove,
    collect_group,
    liberties,
    neighbors,
    resolve_turn,
)


def point(label: str) -> Coordinate:
    return Coordinate.parse(label, 9)


def play(label: str) -> Move:
    return Move(point(label))


def board_with(gray: tuple[str, ...], black: tuple[str, ...], white: tuple[str, ...]) -> Board:
    board = Board.empty(9)
    placements: tuple[tuple[Cell, tuple[str, ...]], ...] = (("G", gray), ("B", black), ("W", white))
    for color, labels in placements:
        for label in labels:
            board = board.with_cell(point(label), color)
    return board


@pytest.mark.parametrize(
    ("gray", "black", "white", "middle"),
    [
        (("e4", "e6"), ("d5",), ("f5",), "e5"),
        (("d5", "f5"), ("e4",), ("e6",), "e5"),
        (("h8", "a8"), ("i7",), ("i9",), "i8"),
        (("c9", "c2"), ("b1",), ("d1",), "c1"),
        (("e4", "d4", "c4", "e6", "d6", "c6"), ("d5", "e3", "f4"), ("f5", "f6", "e7"), "e5"),
    ],
)
def test_gray_bridge_inherits_the_entire_groups_liberties(
    gray: tuple[str, ...], black: tuple[str, ...], white: tuple[str, ...], middle: str
) -> None:
    board = board_with(gray, black, white)
    assert not any(board.get(neighbor) == "+" for neighbor in neighbors(point(middle), 9))
    result = resolve_turn(GameState(board=board), play(middle), play(middle))
    assert result.post_state.board.get(point(middle)) == "G"
    group = collect_group(result.post_state.board, point(middle))
    assert all(point(label) in group for label in gray)
    assert liberties(result.post_state.board, group)
    assert not result.captures


def test_capture_does_not_forbid_the_gray_bridge_on_the_next_round() -> None:
    before = board_with(("a8",), ("i8",), ("i7", "i9"))
    captured = resolve_turn(GameState(board=before), play("h8"), play("h8"))
    assert captured.post_state.board.get(point("i8")) == "+"
    assert point("i8") not in captured.post_state.forbidden.black
    bridge = resolve_turn(captured.post_state, play("i8"), play("i8"))
    assert all(bridge.post_state.board.get(point(label)) == "G" for label in ("a8", "h8", "i8"))
    assert not bridge.captures


def test_group_without_any_liberties_is_removed_as_a_whole() -> None:
    board = board_with(("e4", "e6"), ("e3", "d5", "e7"), ("d4", "f4", "f5", "d6", "f6"))
    result = resolve_turn(GameState(board=board), play("e5"), play("e5"))
    assert all(result.post_state.board.get(point(label)) == "+" for label in ("e4", "e5", "e6"))
    assert len(result.captures) == 1
    assert result.captures[0].captured_color == "gray"
    assert set(result.captures[0].coordinates) == {point(label) for label in ("e4", "e5", "e6")}


@pytest.mark.parametrize("black_plays", [True, False])
def test_black_or_white_placement_does_not_join_gray_groups(black_plays: bool) -> None:
    enemy = ("d5", "f5")
    board = board_with(("e4", "e6"), () if black_plays else enemy, enemy if black_plays else ())
    result = resolve_turn(
        GameState(board=board),
        play("e5") if black_plays else PassMove(),
        PassMove() if black_plays else play("e5"),
    )
    assert result.post_state.board == board
    assert result.captures[0].coordinates == (point("e5"),)
