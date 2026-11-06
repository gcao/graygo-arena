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


@pytest.mark.parametrize("black_plays", [True, False])
def test_capturing_stone_survives_by_gaining_captured_groups_liberties(black_plays: bool) -> None:
    enemy = "W" if black_plays else "B"
    played = "B" if black_plays else "W"
    board = Board.from_key(f"{enemy * 3}/{enemy}+{enemy}/{enemy * 3}")
    placement = move("b2", size=3)

    resolution = resolve_turn(
        GameState(board=board),
        placement if black_plays else PassMove(),
        PassMove() if black_plays else placement,
    )

    assert resolution.post_board_key == f"+++/+{played}+/+++"
    assert len(resolution.captures) == 1
    assert resolution.captures[0].captured_color == ("white" if black_plays else "black")
    assert len(resolution.captures[0].coordinates) == 8
    assert placement.coordinate not in resolution.captures[0].coordinates
    own_forbidden = (
        resolution.post_state.forbidden.black
        if black_plays
        else resolution.post_state.forbidden.white
    )
    assert placement.coordinate not in own_forbidden
    assert board.to_key() == f"{enemy * 3}/{enemy}+{enemy}/{enemy * 3}"


def test_both_zero_liberty_placements_survive_their_simultaneous_captures() -> None:
    board = Board.from_key(
        "++B++++++/+BWB+++++/BW+WB++++/+BWB+++++/++B+++W++/+++++WBW+/++++WB+BW/+++++WBW+/++++++W++"
    )

    resolution = resolve_turn(GameState(board=board), move("c3", size=9), move("g7", size=9))

    assert resolution.post_state.board.get(Coordinate.parse("c3", size=9)) == "B"
    assert resolution.post_state.board.get(Coordinate.parse("g7", size=9)) == "W"
    assert [
        (capture.captured_color, len(capture.coordinates)) for capture in resolution.captures
    ] == [
        ("white", 4),
        ("black", 4),
    ]
    removed = {coordinate for capture in resolution.captures for coordinate in capture.coordinates}
    assert Coordinate.parse("c3", size=9) not in removed
    assert Coordinate.parse("g7", size=9) not in removed


def test_connected_capturing_group_survives_opponent_taking_its_last_liberty() -> None:
    board = Board.from_key("+++++++/++WB+++/+W+WB++/+WBBW++/+++W+++/+++++++/+++++++")

    resolution = resolve_turn(GameState(board=board), move("c3"), move("e3"))

    for label in ("c3", "d3", "d4"):
        assert resolution.post_state.board.get(Coordinate.parse(label, size=7)) == "B"
    assert resolution.post_state.board.get(Coordinate.parse("e3", size=7)) == "W"
    assert resolution.post_state.board.get(Coordinate.parse("c4", size=7)) == "+"
    assert len(resolution.captures) == 1
    assert resolution.captures[0].captured_color == "white"
    assert tuple(c.to_label() for c in resolution.captures[0].coordinates) == ("c4",)


def test_collision_gray_stone_survives_after_capturing_an_existing_group() -> None:
    placement = move("b2", size=3)

    resolution = resolve_turn(GameState(board=Board.from_key("WWW/W+W/WWW")), placement, placement)

    assert resolution.post_board_key == "+++/+G+/+++"
    assert len(resolution.captures) == 1
    assert resolution.captures[0].captured_color == "white"


@pytest.mark.parametrize("black_plays", [True, False])
def test_played_stone_without_a_capture_is_still_removed_if_suicidal(black_plays: bool) -> None:
    enemy = "W" if black_plays else "B"
    key = f"+++++/++{enemy}++/+{enemy}+{enemy}+/++{enemy}++/+++++"
    placement = move("c3", size=5)

    resolution = resolve_turn(
        GameState(board=Board.from_key(key)),
        placement if black_plays else PassMove(),
        PassMove() if black_plays else placement,
    )

    assert resolution.post_board_key == key
    assert len(resolution.captures) == 1
    assert resolution.captures[0].captured_color == ("black" if black_plays else "white")
    assert resolution.captures[0].coordinates == (placement.coordinate,)


def test_gray_collision_is_still_removed_if_it_cannot_gain_a_liberty() -> None:
    key = "+++++/++W++/+W+W+/++W++/+++++"
    placement = move("c3", size=5)

    resolution = resolve_turn(GameState(board=Board.from_key(key)), placement, placement)

    assert resolution.post_board_key == key
    assert len(resolution.captures) == 1
    assert resolution.captures[0].captured_color == "gray"
    assert resolution.captures[0].coordinates == (placement.coordinate,)


def test_both_remaining_dead_played_groups_are_removed_simultaneously() -> None:
    resolution = resolve_turn(
        GameState(board=Board.from_key("BBB/W++/WWW")), move("b2", size=3), move("b3", size=3)
    )

    assert resolution.post_board_key == "+++/+++/+++"
    assert sum(len(capture.coordinates) for capture in resolution.captures) == 9


def test_capture_removes_zero_liberty_gray_group_and_forbids_both_colors() -> None:
    state = GameState(
        board=Board.from_key("+++++++/+WWG+++/+BWBBB+/+BGGWW+/++WBBW+/+++GBB+/+++WW++")
    )

    resolution = resolve_turn(state, PassMove(), PassMove())

    assert resolution.post_board_key == "+++++++/+WWG+++/+BWBBB+/+B++WW+/++WBBW+/+++GBB+/+++WW++"
    assert len(resolution.captures) == 1
    capture = resolution.captures[0]
    assert capture.captured_color == "gray"
    assert capture.by_color == "neutral"
    assert tuple(coordinate.to_label() for coordinate in capture.coordinates) == (
        "d3",
        "d4",
    )
    assert [
        (update.color, tuple(c.to_label() for c in update.coordinates))
        for update in resolution.forbidden_updates
    ] == [
        ("black", ("d3", "d4")),
        ("white", ("d3", "d4")),
    ]
    assert Coordinate.parse("d3", size=7) in resolution.post_state.forbidden.black
    assert Coordinate.parse("d4", size=7) in resolution.post_state.forbidden.black
    assert Coordinate.parse("d3", size=7) in resolution.post_state.forbidden.white
    assert Coordinate.parse("d4", size=7) in resolution.post_state.forbidden.white


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


def test_first_mutual_pass_keeps_game_running_and_scores() -> None:
    state = GameState(board=Board.from_key("B++/+W+/++G"))

    resolution = resolve_turn(state, PassMove(), PassMove())

    assert resolution.double_pass_count == 1
    assert resolution.game_finished is False
    assert resolution.score_estimate == {"black": 1.0, "white": 1.0}


def test_second_consecutive_mutual_pass_finishes_game() -> None:
    first = resolve_turn(GameState(board=Board.from_key("B++/+W+/++G")), PassMove(), PassMove())

    second = resolve_turn(first.post_state, PassMove(), PassMove())

    assert second.double_pass_count == 2
    assert second.post_state.double_pass_count == 2
    assert second.game_finished is True
    assert second.score_estimate == first.score_estimate


@pytest.mark.parametrize("black_places", [True, False])
def test_either_player_placing_requires_two_new_mutual_pass_rounds(black_places: bool) -> None:
    first = resolve_turn(GameState(board=Board.empty(3)), PassMove(), PassMove())
    placement = move("b2", size=3)
    interrupted = resolve_turn(
        first.post_state,
        placement if black_places else PassMove(),
        PassMove() if black_places else placement,
    )
    restarted = resolve_turn(interrupted.post_state, PassMove(), PassMove())
    finished = resolve_turn(restarted.post_state, PassMove(), PassMove())

    assert interrupted.double_pass_count == 0
    assert interrupted.game_finished is False
    assert restarted.double_pass_count == 1
    assert restarted.game_finished is False
    assert finished.double_pass_count == 2
    assert finished.game_finished is True


def test_pass_plus_placement_does_not_collide_and_resets_double_pass_count() -> None:
    state = GameState(board=Board.empty(3), double_pass_count=1)

    resolution = resolve_turn(state, PassMove(), move("b2", size=3))

    assert resolution.post_board_key == "+++/+W+/+++"
    assert all(event.event_type != "collision" for event in resolution.placement_events)
    assert resolution.double_pass_count == 0
    assert resolution.game_finished is False


def test_captured_same_turn_collision_forbids_coordinate_for_both_colors() -> None:
    state = GameState(
        board=Board.from_key(
            "++++W+W++/++B++W+W+/++B+W+W++/++BW+W+BW/W+++W+B+W/"
            "BBBBBWWBW/+++++W+B+/+++++++B+/B++++++B+"
        ),
        turn_index=21,
    )

    resolution = resolve_turn(state, move("e8", size=9), move("e8", size=9))

    assert (
        resolution.post_board_key == "++++W+W++/++B++W+W+/++B+W+W++/++BW+W+BW/W+++W+B+W/"
        "BBBBBWWBW/+++++W+B+/+++++++B+/B++++++B+"
    )
    assert len(resolution.captures) == 1
    assert resolution.captures[0].captured_color == "gray"
    assert tuple(coordinate.to_label() for coordinate in resolution.captures[0].coordinates) == (
        "e8",
    )
    assert [
        (update.color, tuple(c.to_label() for c in update.coordinates))
        for update in resolution.forbidden_updates
    ] == [
        ("black", ("e8",)),
        ("white", ("e8",)),
    ]
    assert Coordinate.parse("e8", size=9) in resolution.post_state.forbidden.black
    assert Coordinate.parse("e8", size=9) in resolution.post_state.forbidden.white
    assert resolution.placement_events[0].event_type == "collision"
