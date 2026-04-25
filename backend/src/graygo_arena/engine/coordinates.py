"""Coordinate parsing and rendering for Gray Go boards."""

from __future__ import annotations

from dataclasses import dataclass

MIN_BOARD_SIZE = 3
MAX_BOARD_SIZE = 26


def validate_board_size(size: int) -> None:
    if size < MIN_BOARD_SIZE or size > MAX_BOARD_SIZE:
        msg = f"board size must be between {MIN_BOARD_SIZE} and {MAX_BOARD_SIZE}"
        raise ValueError(msg)


@dataclass(frozen=True, order=True)
class Coordinate:
    """Zero-based row and column coordinate."""

    row: int
    col: int

    @classmethod
    def parse(cls, value: str, size: int) -> Coordinate:
        validate_board_size(size)
        if len(value) < 2:
            msg = "coordinate must contain a lowercase row letter and 1-based column"
            raise ValueError(msg)

        row_label = value[0]
        col_label = value[1:]
        if not row_label.isascii() or not row_label.islower() or not row_label.isalpha():
            msg = "coordinate row must be a lowercase ASCII letter"
            raise ValueError(msg)
        if not col_label.isdecimal():
            msg = "coordinate column must be a positive integer"
            raise ValueError(msg)

        row = ord(row_label) - ord("a")
        col = int(col_label) - 1
        if row < 0 or row >= size:
            msg = "coordinate row is outside the board"
            raise ValueError(msg)
        if col < 0 or col >= size:
            msg = "coordinate column is outside the board"
            raise ValueError(msg)
        return cls(row=row, col=col)

    def to_label(self) -> str:
        if self.row < 0 or self.row >= MAX_BOARD_SIZE:
            msg = "coordinate row cannot be rendered as a single lowercase ASCII letter"
            raise ValueError(msg)
        if self.col < 0:
            msg = "coordinate column cannot be negative"
            raise ValueError(msg)
        return f"{chr(ord('a') + self.row)}{self.col + 1}"

    def require_inside(self, size: int) -> None:
        validate_board_size(size)
        if self.row < 0 or self.row >= size or self.col < 0 or self.col >= size:
            msg = "coordinate is outside the board"
            raise ValueError(msg)
