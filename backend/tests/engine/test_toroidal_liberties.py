from graygo_arena.engine import Board, Coordinate, collect_group, liberties, neighbors


def test_neighbors_wrap_from_a1() -> None:
    wrapped = neighbors(Coordinate.parse("a1", size=7), size=7)

    assert tuple(coordinate.to_label() for coordinate in wrapped) == ("g1", "b1", "a7", "a2")


def test_group_connects_through_toroidal_wrap() -> None:
    board = Board.from_key("B+B/+++/B++")

    group = collect_group(board, Coordinate.parse("a1", size=3))

    assert {coordinate.to_label() for coordinate in group} == {"a1", "a3", "c1"}


def test_liberties_use_wrapped_neighbors() -> None:
    board = Board.from_key("B+B/+++/B++")
    group = collect_group(board, Coordinate.parse("a1", size=3))

    liberty_labels = {coordinate.to_label() for coordinate in liberties(board, group)}

    assert liberty_labels == {"a2", "b1", "b3", "c2", "c3"}


def test_gray_group_is_distinct_and_occupied() -> None:
    board = Board.from_key("GG+/+++/+++")

    group = collect_group(board, Coordinate.parse("a1", size=3))

    assert {coordinate.to_label() for coordinate in group} == {"a1", "a2"}
    assert Coordinate.parse("a3", size=3) in liberties(board, group)
