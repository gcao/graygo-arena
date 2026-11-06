"""Chinese area scoring on a torus, with all remaining stones treated as alive."""

from __future__ import annotations

from graygo_arena.engine.board import Board, Cell
from graygo_arena.engine.coordinates import Coordinate
from graygo_arena.engine.rules import neighbors


def score_board(board: Board) -> dict[str, float]:
    black = 0.0
    visited: set[Coordinate] = set()
    for row in range(board.size):
        for col in range(board.size):
            point = Coordinate(row, col)
            cell = board.get(point)
            if cell == "B":
                black += 1
            elif cell == "G":
                black += 0.5
            elif cell == "+" and point not in visited:
                region = [point]
                visited.add(point)
                border: set[Cell] = set()
                area = 0
                while region:
                    current = region.pop()
                    area += 1
                    for neighbor in neighbors(current, board.size):
                        color = board.get(neighbor)
                        if color != "+":
                            border.add(color)
                        elif neighbor not in visited:
                            visited.add(neighbor)
                            region.append(neighbor)
                # Each bordering faction gets an equal share; gray's share is
                # split between the players. An empty board is shared equally.
                share = (("B" in border) + 0.5 * ("G" in border)) / len(border) if border else 0.5
                black += area * share
    return {"black": black, "white": board.size * board.size - black}
