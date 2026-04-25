# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from typing import cast

from hypothesis import assume, given
from hypothesis import strategies as st

from graygo_arena.engine import Board, Coordinate, GameState, Move, resolve_turn
from graygo_arena.engine.board import Cell
from graygo_arena.engine.rules import neighbors


@given(
    size=st.integers(min_value=3, max_value=9),
    row=st.integers(min_value=0, max_value=8),
    col=st.integers(min_value=0, max_value=8),
    cell=st.sampled_from(["+", "B", "W", "G"]),
)
def test_board_key_round_trip_for_generated_board(
    size: int,
    row: int,
    col: int,
    cell: str,
) -> None:
    assume(row < size)
    assume(col < size)
    board = Board.empty(size).with_cell(Coordinate(row=row, col=col), cast(Cell, cell))

    assert Board.from_key(board.to_key()).to_key() == board.to_key()


@given(
    size=st.integers(min_value=3, max_value=9),
    row=st.integers(min_value=0, max_value=8),
    col=st.integers(min_value=0, max_value=8),
)
def test_coordinate_round_trip_for_generated_coordinate(size: int, row: int, col: int) -> None:
    assume(row < size)
    assume(col < size)
    coordinate = Coordinate(row=row, col=col)

    assert Coordinate.parse(coordinate.to_label(), size=size) == coordinate


@given(
    size=st.integers(min_value=3, max_value=9),
    row=st.integers(min_value=0, max_value=8),
    col=st.integers(min_value=0, max_value=8),
)
def test_neighbor_symmetry(size: int, row: int, col: int) -> None:
    assume(row < size)
    assume(col < size)
    coordinate = Coordinate(row=row, col=col)

    for neighbor in neighbors(coordinate, size=size):
        assert coordinate in neighbors(neighbor, size=size)


@given(
    size=st.integers(min_value=3, max_value=9),
    black_row=st.integers(min_value=0, max_value=8),
    black_col=st.integers(min_value=0, max_value=8),
    white_row=st.integers(min_value=0, max_value=8),
    white_col=st.integers(min_value=0, max_value=8),
)
def test_resolve_turn_is_deterministic(
    size: int,
    black_row: int,
    black_col: int,
    white_row: int,
    white_col: int,
) -> None:
    assume(black_row < size)
    assume(black_col < size)
    assume(white_row < size)
    assume(white_col < size)
    state = GameState(board=Board.empty(size))
    black_move = Move(Coordinate(row=black_row, col=black_col))
    white_move = Move(Coordinate(row=white_row, col=white_col))

    first = resolve_turn(state, black_move, white_move)
    second = resolve_turn(state, black_move, white_move)

    assert first == second


@given(
    size=st.integers(min_value=3, max_value=9),
    black_row=st.integers(min_value=0, max_value=8),
    black_col=st.integers(min_value=0, max_value=8),
    white_row=st.integers(min_value=0, max_value=8),
    white_col=st.integers(min_value=0, max_value=8),
)
def test_resolve_turn_does_not_mutate_generated_pre_state(
    size: int,
    black_row: int,
    black_col: int,
    white_row: int,
    white_col: int,
) -> None:
    assume(black_row < size)
    assume(black_col < size)
    assume(white_row < size)
    assume(white_col < size)
    board = Board.empty(size)
    state = GameState(board=board)
    pre_key = board.to_key()

    resolve_turn(
        state,
        Move(Coordinate(row=black_row, col=black_col)),
        Move(Coordinate(row=white_row, col=white_col)),
    )

    assert state.board.to_key() == pre_key
    assert board.to_key() == pre_key
