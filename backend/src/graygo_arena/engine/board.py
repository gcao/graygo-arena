"""Immutable board representation and BoardKey serialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from graygo_arena.engine.coordinates import Coordinate, validate_board_size

type Cell = Literal["+", "B", "W", "G"]
VALID_CELLS: frozenset[str] = frozenset({"+", "B", "W", "G"})


@dataclass(frozen=True)
class Board:
    size: int
    cells: tuple[tuple[Cell, ...], ...]

    def __post_init__(self) -> None:
        validate_board_size(self.size)
        if len(self.cells) != self.size:
            msg = "board row count must match size"
            raise ValueError(msg)
        for row in self.cells:
            if len(row) != self.size:
                msg = "board row length must match size"
                raise ValueError(msg)
            unsupported = set(row).difference(VALID_CELLS)
            if unsupported:
                msg = f"unsupported board cell symbols: {sorted(unsupported)}"
                raise ValueError(msg)

    @classmethod
    def empty(cls, size: int) -> Board:
        validate_board_size(size)
        row: tuple[Cell, ...] = tuple("+" for _ in range(size))
        return cls(size=size, cells=tuple(row for _ in range(size)))

    @classmethod
    def from_key(cls, key: str) -> Board:
        rows = key.split("/")
        if not rows or any(row == "" for row in rows):
            msg = "BoardKey must contain non-empty slash-separated rows"
            raise ValueError(msg)

        size = len(rows)
        validate_board_size(size)
        cells: list[tuple[Cell, ...]] = []
        for row in rows:
            if len(row) != size:
                msg = "BoardKey must be square with equal row count and row length"
                raise ValueError(msg)
            unsupported = set(row).difference(VALID_CELLS)
            if unsupported:
                msg = f"unsupported BoardKey symbols: {sorted(unsupported)}"
                raise ValueError(msg)
            cells.append(tuple(row))  # type: ignore[arg-type]
        return cls(size=size, cells=tuple(cells))

    def to_key(self) -> str:
        return "/".join("".join(row) for row in self.cells)

    def get(self, coordinate: Coordinate) -> Cell:
        coordinate.require_inside(self.size)
        return self.cells[coordinate.row][coordinate.col]

    def with_cell(self, coordinate: Coordinate, cell: Cell) -> Board:
        coordinate.require_inside(self.size)
        if cell not in VALID_CELLS:
            msg = f"unsupported board cell symbol: {cell}"
            raise ValueError(msg)
        rows = [list(row) for row in self.cells]
        rows[coordinate.row][coordinate.col] = cell
        return Board(
            size=self.size,
            cells=tuple(tuple(row) for row in rows),  # type: ignore[arg-type]
        )
