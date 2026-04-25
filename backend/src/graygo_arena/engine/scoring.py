"""Deterministic graygo-v1 score estimates."""

from __future__ import annotations

from graygo_arena.engine.board import Board


def score_board(board: Board) -> dict[str, float]:
    black = 0
    white = 0
    for row in board.cells:
        for cell in row:
            if cell == "B":
                black += 1
            elif cell == "W":
                white += 1
    return {"black": float(black), "white": float(white)}
