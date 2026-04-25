import { Fragment } from "react";

import type { TurnResponse } from "../api/client";
import {
  cellAt,
  coordinateLabel,
  flattenCaptureLabels,
  parseCoordinate,
  toroidalNeighbors,
  type Coordinate
} from "../game/board";

type BoardGridProps = {
  board: string[];
  latestTurn: TurnResponse | null;
  selected: Coordinate | null;
  showNeighbors: boolean;
  showLastMoves: boolean;
  showCollisions: boolean;
  showCaptures: boolean;
  onSelect: (coordinate: Coordinate) => void;
};

export function BoardGrid({
  board,
  latestTurn,
  selected,
  showNeighbors,
  showLastMoves,
  showCollisions,
  showCaptures,
  onSelect
}: BoardGridProps) {
  const size = board.length;
  const blackMove = latestTurn ? parseCoordinate(latestTurn.black_move) : null;
  const whiteMove = latestTurn ? parseCoordinate(latestTurn.white_move) : null;
  const collision =
    latestTurn && latestTurn.black_move === latestTurn.white_move
      ? parseCoordinate(latestTurn.black_move)
      : null;
  const captures = new Set(latestTurn ? flattenCaptureLabels(latestTurn.captures) : []);
  const neighborLabels = new Set(
    selected && showNeighbors
      ? toroidalNeighbors(selected, size).map((coordinate) => coordinateLabel(coordinate))
      : []
  );

  return (
    <div
      className="board-grid"
      style={{ gridTemplateColumns: `2rem repeat(${size}, minmax(2.4rem, 1fr))` }}
    >
      <div className="board-axis" />
      {Array.from({ length: size }, (_, col) => (
        <div className="board-axis" key={`col-${col}`}>
          {col + 1}
        </div>
      ))}
      {board.map((rowValue, row) => (
        <Fragment key={`row-${row}`}>
          <div className="board-axis">
            {String.fromCharCode("a".charCodeAt(0) + row)}
          </div>
          {Array.from(rowValue).map((_, col) => {
            const coordinate = { row, col };
            const label = coordinateLabel(coordinate);
            const symbol = cellAt(board, coordinate);
            const isSelected = selected?.row === row && selected.col === col;
            const isBlackMove = showLastMoves && blackMove?.row === row && blackMove.col === col;
            const isWhiteMove = showLastMoves && whiteMove?.row === row && whiteMove.col === col;
            const isCollision = showCollisions && collision?.row === row && collision.col === col;
            const isCapture = showCaptures && captures.has(label);
            const classes = [
              "board-cell",
              `cell-${symbol === "+" ? "empty" : symbol.toLowerCase()}`,
              isSelected ? "is-selected" : "",
              neighborLabels.has(label) ? "is-neighbor" : "",
              isBlackMove ? "is-black-move" : "",
              isWhiteMove ? "is-white-move" : "",
              isCollision ? "is-collision" : "",
              isCapture ? "is-capture" : ""
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <button
                aria-label={`Cell ${label} ${symbol}`}
                className={classes}
                key={label}
                onClick={() => onSelect(coordinate)}
                title={label}
                type="button"
              >
                {symbol}
              </button>
            );
          })}
        </Fragment>
      ))}
    </div>
  );
}
