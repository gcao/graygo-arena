"""Toroidal group and liberty helpers."""

from __future__ import annotations

from collections import deque

from graygo_arena.engine.board import Board, Cell
from graygo_arena.engine.coordinates import Coordinate, validate_board_size


def neighbors(coordinate: Coordinate, size: int) -> tuple[Coordinate, ...]:
    validate_board_size(size)
    coordinate.require_inside(size)
    return (
        Coordinate((coordinate.row - 1) % size, coordinate.col),
        Coordinate((coordinate.row + 1) % size, coordinate.col),
        Coordinate(coordinate.row, (coordinate.col - 1) % size),
        Coordinate(coordinate.row, (coordinate.col + 1) % size),
    )


def collect_group(board: Board, start: Coordinate) -> frozenset[Coordinate]:
    start.require_inside(board.size)
    cell = board.get(start)
    if cell == "+":
        return frozenset()

    visited: set[Coordinate] = {start}
    queue: deque[Coordinate] = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in neighbors(current, board.size):
            if neighbor not in visited and board.get(neighbor) == cell:
                visited.add(neighbor)
                queue.append(neighbor)
    return frozenset(visited)


def liberties(board: Board, group: frozenset[Coordinate]) -> frozenset[Coordinate]:
    empty_neighbors: set[Coordinate] = set()
    for coordinate in group:
        coordinate.require_inside(board.size)
        for neighbor in neighbors(coordinate, board.size):
            if board.get(neighbor) == "+":
                empty_neighbors.add(neighbor)
    return frozenset(empty_neighbors)


def groups_for_cell(board: Board, cell: Cell) -> tuple[frozenset[Coordinate], ...]:
    if cell == "+":
        return ()

    seen: set[Coordinate] = set()
    groups: list[frozenset[Coordinate]] = []
    for row in range(board.size):
        for col in range(board.size):
            coordinate = Coordinate(row=row, col=col)
            if coordinate in seen or board.get(coordinate) != cell:
                continue
            group = collect_group(board, coordinate)
            seen.update(group)
            groups.append(group)
    return tuple(groups)
