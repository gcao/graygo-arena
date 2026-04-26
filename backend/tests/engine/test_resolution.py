import pytest

from graygo_arena.engine import (
    Board,
    Coordinate,
    ForbiddenState,
    GameState,
    Move,
    PassMove,
    resolve_turn,
)

EMPTY_7X7 = "+++++++/+++++++/+++++++/+++++++/+++++++/+++++++/+++++++"


def move(label: str, size: int = 7) -> Move:
    return Move(Coordinate.parse(label, size=size))


def test_same_point_collision_produces_gray_without_mutating_pre_board() -> None:
    board = Board.empty(7)
    state = GameState(board=board)

    resolution = resolve_turn(state, move("d4"), move("d4"))

    assert resolution.pre_board_key == EMPTY_7X7
    assert resolution.post_board_key == "+++++++/+++++++/+++++++/+++G+++/+++++++/+++++++/+++++++"
    assert "+++G+++" in resolution.post_board_key
    assert resolution.placement_events[0].event_type == "collision"
    assert resolution.placement_events[0].coordinate.to_label() == "d4"
    assert board.to_key() == EMPTY_7X7


def test_adjacent_simultaneous_placements_produce_black_and_white() -> None:
    resolution = resolve_turn(GameState(board=Board.empty(7)), move("d4"), move("d5"))

    assert resolution.post_board_key == "+++++++/+++++++/+++++++/+++BW++/+++++++/+++++++/+++++++"
    placement_summary = [
        (event.color, event.coordinate.to_label()) for event in resolution.placement_events
    ]
    assert placement_summary == [
        ("black", "d4"),
        ("white", "d5"),
    ]


def test_invalid_occupied_move_raises_value_error() -> None:
    board = Board.empty(7).with_cell(Coordinate.parse("d4", size=7), "B")

    with pytest.raises(ValueError):
        resolve_turn(GameState(board=board), move("d4"), PassMove())


def test_resolve_turn_does_not_mutate_input_board() -> None:
    board = Board.empty(7)
    state = GameState(board=board)

    resolve_turn(state, move("c4"), move("d4"))

    assert state.board is board
    assert state.board.to_key() == EMPTY_7X7


def test_capture_removes_zero_liberty_group() -> None:
    state = GameState(board=Board.from_key("+B+/BW+/+B+"))

    resolution = resolve_turn(state, move("b3", size=3), PassMove())

    assert resolution.post_board_key == "+B+/B+B/+B+"
    assert len(resolution.captures) == 1
    assert resolution.captures[0].captured_color == "white"
    captured_labels = tuple(
        coordinate.to_label() for coordinate in resolution.captures[0].coordinates
    )
    assert captured_labels == ("b2",)


def test_capture_removes_zero_liberty_gray_group_without_forbidden_update() -> None:
    state = GameState(
        board=Board.from_key(
            "+++++++/+WWG+++/+BWBBB+/+BGGWW+/++WBBW+/+++GBB+/+++WW++"
        )
    )

    resolution = resolve_turn(state, PassMove(), PassMove())

    assert (
        resolution.post_board_key
        == "+++++++/+WWG+++/+BWBBB+/+B++WW+/++WBBW+/+++GBB+/+++WW++"
    )
    assert len(resolution.captures) == 1
    capture = resolution.captures[0]
    assert capture.captured_color == "gray"
    assert capture.by_color == "neutral"
    assert tuple(coordinate.to_label() for coordinate in capture.coordinates) == (
        "d3",
        "d4",
    )
    assert resolution.forbidden_updates == ()
    assert not resolution.post_state.forbidden.black
    assert not resolution.post_state.forbidden.white


def test_capture_creates_color_specific_forbidden_update() -> None:
    state = GameState(board=Board.from_key("+B+/BW+/+B+"))

    resolution = resolve_turn(state, move("b3", size=3), PassMove())

    assert resolution.forbidden_updates[0].color == "white"
    assert tuple(
        coordinate.to_label() for coordinate in resolution.forbidden_updates[0].coordinates
    ) == ("b2",)
    assert Coordinate.parse("b2", size=3) in resolution.post_state.forbidden.white
    assert Coordinate.parse("b2", size=3) not in resolution.post_state.forbidden.black


def test_forbidden_point_blocks_only_matching_color() -> None:
    forbidden = ForbiddenState(white=frozenset({Coordinate.parse("b2", size=3)}))
    state = GameState(board=Board.empty(3), forbidden=forbidden)

    with pytest.raises(ValueError):
        resolve_turn(state, PassMove(), move("b2", size=3))

    resolution = resolve_turn(state, move("b2", size=3), PassMove())
    assert resolution.post_board_key == "+++/+B+/+++"


def test_pass_pass_finishes_game_and_scores() -> None:
    state = GameState(board=Board.from_key("B++/+W+/++G"))

    resolution = resolve_turn(state, PassMove(), PassMove())

    assert resolution.double_pass_count == 1
    assert resolution.game_finished is True
    assert resolution.score_estimate == {"black": 1.0, "white": 1.0}


def test_pass_plus_placement_does_not_collide_and_resets_double_pass_count() -> None:
    state = GameState(board=Board.empty(3), double_pass_count=1)

    resolution = resolve_turn(state, PassMove(), move("b2", size=3))

    assert resolution.post_board_key == "+++/+W+/+++"
    assert all(event.event_type != "collision" for event in resolution.placement_events)
    assert resolution.double_pass_count == 0
    assert resolution.game_finished is False
