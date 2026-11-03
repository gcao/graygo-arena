"""Simultaneous Gray Go turn resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from graygo_arena.engine.board import Board, Cell
from graygo_arena.engine.coordinates import Coordinate
from graygo_arena.engine.moves import (
    ForbiddenState,
    Move,
    MoveLike,
    PassMove,
    SeatColor,
    legal_moves,
)
from graygo_arena.engine.rules import groups_for_cell, liberties
from graygo_arena.engine.scoring import score_board

type PlacementEventType = Literal["placement", "collision"]
type CapturedColor = Literal["black", "white", "gray"]
type CaptureByColor = Literal["black", "white", "neutral"]
type Ruleset = Literal["graygo-v1"]

DOUBLE_PASS_FINISH_THRESHOLD = 1


def _empty_forbidden() -> ForbiddenState:
    return ForbiddenState()


@dataclass(frozen=True)
class GameState:
    board: Board
    forbidden: ForbiddenState = field(default_factory=_empty_forbidden)
    double_pass_count: int = 0
    turn_index: int = 0
    ruleset: Ruleset = "graygo-v1"

    def __post_init__(self) -> None:
        if self.ruleset != "graygo-v1":
            msg = "unsupported ruleset"
            raise ValueError(msg)
        if self.double_pass_count < 0:
            msg = "double_pass_count cannot be negative"
            raise ValueError(msg)
        if self.turn_index < 0:
            msg = "turn_index cannot be negative"
            raise ValueError(msg)
        for coordinate in self.forbidden.black | self.forbidden.white:
            coordinate.require_inside(self.board.size)


@dataclass(frozen=True)
class PlacementEvent:
    event_type: PlacementEventType
    coordinate: Coordinate
    color: SeatColor | None = None


@dataclass(frozen=True)
class CaptureEvent:
    captured_color: CapturedColor
    by_color: CaptureByColor
    coordinates: tuple[Coordinate, ...]


@dataclass(frozen=True)
class ForbiddenUpdate:
    color: SeatColor
    coordinates: tuple[Coordinate, ...]


@dataclass(frozen=True)
class TurnResolution:
    pre_board_key: str
    post_board_key: str
    black_move: str
    white_move: str
    placement_events: tuple[PlacementEvent, ...]
    captures: tuple[CaptureEvent, ...]
    forbidden_updates: tuple[ForbiddenUpdate, ...]
    post_state: GameState
    double_pass_count: int
    game_finished: bool
    score_estimate: dict[str, float]


def resolve_turn(state: GameState, black_move: MoveLike, white_move: MoveLike) -> TurnResolution:
    _validate_move(state, "black", black_move)
    _validate_move(state, "white", white_move)

    post_board, placement_events = _apply_simultaneous_placements(
        state.board, black_move, white_move
    )
    post_board, captures = _apply_captures(post_board)
    forbidden, forbidden_updates = _forbidden_from_captures(captures)
    double_pass_count = (
        state.double_pass_count + 1
        if isinstance(black_move, PassMove) and isinstance(white_move, PassMove)
        else 0
    )
    game_finished = double_pass_count >= DOUBLE_PASS_FINISH_THRESHOLD
    score_estimate = score_board(post_board)
    post_state = GameState(
        board=post_board,
        forbidden=forbidden,
        double_pass_count=double_pass_count,
        turn_index=state.turn_index + 1,
        ruleset=state.ruleset,
    )

    return TurnResolution(
        pre_board_key=state.board.to_key(),
        post_board_key=post_board.to_key(),
        black_move=black_move.label,
        white_move=white_move.label,
        placement_events=placement_events,
        captures=captures,
        forbidden_updates=forbidden_updates,
        post_state=post_state,
        double_pass_count=double_pass_count,
        game_finished=game_finished,
        score_estimate=score_estimate,
    )


def _validate_move(state: GameState, color: SeatColor, move: MoveLike) -> None:
    if isinstance(move, PassMove):
        return
    if move not in legal_moves(state.board, color, state.forbidden):
        msg = f"illegal {color} move: {move.label}"
        raise ValueError(msg)


def _apply_simultaneous_placements(
    board: Board,
    black_move: MoveLike,
    white_move: MoveLike,
) -> tuple[Board, tuple[PlacementEvent, ...]]:
    if (
        isinstance(black_move, Move)
        and isinstance(white_move, Move)
        and black_move.coordinate == white_move.coordinate
    ):
        return (
            board.with_cell(black_move.coordinate, "G"),
            (
                PlacementEvent(
                    event_type="collision",
                    coordinate=black_move.coordinate,
                ),
            ),
        )

    post_board = board
    events: list[PlacementEvent] = []
    if isinstance(black_move, Move):
        post_board = post_board.with_cell(black_move.coordinate, "B")
        events.append(
            PlacementEvent(
                event_type="placement",
                coordinate=black_move.coordinate,
                color="black",
            )
        )
    if isinstance(white_move, Move):
        post_board = post_board.with_cell(white_move.coordinate, "W")
        events.append(
            PlacementEvent(
                event_type="placement",
                coordinate=white_move.coordinate,
                color="white",
            )
        )
    return post_board, tuple(events)


def _apply_captures(board: Board) -> tuple[Board, tuple[CaptureEvent, ...]]:
    captures: list[CaptureEvent] = []
    capture_specs: tuple[tuple[Cell, CapturedColor, CaptureByColor], ...] = (
        ("W", "white", "black"),
        ("B", "black", "white"),
        ("G", "gray", "neutral"),
    )
    for captured_cell, captured_color, by_color in capture_specs:
        captured_coordinates = _zero_liberty_coordinates(board, captured_cell)
        if captured_coordinates:
            captures.append(
                CaptureEvent(
                    captured_color=captured_color,
                    by_color=by_color,
                    coordinates=captured_coordinates,
                )
            )

    post_board = board
    for capture in captures:
        for coordinate in capture.coordinates:
            post_board = post_board.with_cell(coordinate, "+")
    return post_board, tuple(captures)


def _zero_liberty_coordinates(board: Board, cell: Cell) -> tuple[Coordinate, ...]:
    captured: set[Coordinate] = set()
    for group in groups_for_cell(board, cell):
        if not liberties(board, group):
            captured.update(group)
    return tuple(sorted(captured))


def _forbidden_from_captures(
    captures: tuple[CaptureEvent, ...],
) -> tuple[ForbiddenState, tuple[ForbiddenUpdate, ...]]:
    black_forbidden: set[Coordinate] = set()
    white_forbidden: set[Coordinate] = set()
    updates: list[ForbiddenUpdate] = []

    for capture in captures:
        coordinates = tuple(sorted(capture.coordinates))
        if capture.captured_color == "gray":
            black_forbidden.update(coordinates)
            white_forbidden.update(coordinates)
            updates.append(ForbiddenUpdate(color="black", coordinates=coordinates))
            updates.append(ForbiddenUpdate(color="white", coordinates=coordinates))
        elif capture.captured_color == "black":
            black_forbidden.update(coordinates)
            updates.append(
                ForbiddenUpdate(
                    color=capture.captured_color,
                    coordinates=coordinates,
                )
            )
        else:
            white_forbidden.update(coordinates)
            updates.append(
                ForbiddenUpdate(
                    color=capture.captured_color,
                    coordinates=coordinates,
                )
            )

    return (
        ForbiddenState(
            black=frozenset(black_forbidden),
            white=frozenset(white_forbidden),
        ),
        tuple(updates),
    )
