import pytest

from graygo_arena.engine import (
    Board,
    Coordinate,
    ForbiddenState,
    GameState,
    Move,
    PassMove,
    RoundHistory,
    resolve_turn,
)

KO_BOARD = "++W++/+WBW+/+B+B+/++B++/+++++"


def move(label: str) -> Move:
    return Move(Coordinate.parse(label, 5))


def test_capture_repetition_resolves_then_bans_the_moves_after_the_matching_board() -> None:
    initial = GameState(board=Board.from_key(KO_BOARD))
    captured = resolve_turn(initial, PassMove(), move("c3"))
    assert captured.post_state.forbidden == ForbiddenState()
    repeated = resolve_turn(captured.post_state, move("b3"), PassMove())
    assert repeated.post_board_key == KO_BOARD
    assert repeated.post_state.forbidden.black == frozenset()
    assert repeated.post_state.forbidden.white == frozenset({move("c3").coordinate})
    assert move("b3").coordinate not in repeated.post_state.forbidden.black
    with pytest.raises(ValueError, match="illegal white"):
        resolve_turn(repeated.post_state, PassMove(), move("c3"))
    passed = resolve_turn(repeated.post_state, PassMove(), PassMove())
    assert passed.post_state.forbidden == repeated.post_state.forbidden
    escaped = resolve_turn(passed.post_state, move("e5"), PassMove())
    assert escaped.post_state.forbidden == ForbiddenState()


def test_only_two_previous_rounds_are_retained() -> None:
    state = GameState(board=Board.empty(5))
    for label in ("a1", "b2", "c3"):
        state = resolve_turn(state, move(label), PassMove()).post_state
    assert len(state.history) == 2
    assert [round_.black_move for round_ in state.history] == ["b2", "c3"]


def test_a_match_of_either_saved_before_board_forbids_each_seats_own_past_move() -> None:
    board = Board.empty(5)
    state = GameState(
        board=board,
        history=(
            RoundHistory(board.to_key(), "a1", "PASS"),
            RoundHistory(board.to_key(), "b2", "c3"),
        ),
    )
    result = resolve_turn(state, PassMove(), PassMove())
    assert result.post_state.forbidden.black == frozenset(
        {move("a1").coordinate, move("b2").coordinate}
    )
    assert result.post_state.forbidden.white == frozenset({move("c3").coordinate})
