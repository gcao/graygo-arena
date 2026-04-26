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
  const columnGrid = { gridTemplateColumns: `2rem repeat(${size}, var(--point-size))` };
  const rowGrid = { gridTemplateRows: `repeat(${size}, var(--point-size))` };
  const pointGrid = {
    gridTemplateColumns: `repeat(${size}, var(--point-size))`,
    gridTemplateRows: `repeat(${size}, var(--point-size))`
  };

  return (
    <div className="board-grid">
      <div className="board-col-axis" style={columnGrid}>
        <div className="board-axis" />
        {Array.from({ length: size }, (_, col) => (
          <div className="board-axis" key={`col-${col}`}>
            {col + 1}
          </div>
        ))}
      </div>
      <div className="board-body">
        <div className="board-row-axis" style={rowGrid}>
          {Array.from({ length: size }, (_, row) => (
            <div className="board-axis" key={`row-${row}`}>
              {String.fromCharCode("a".charCodeAt(0) + row)}
            </div>
          ))}
        </div>
        <div aria-label={`${size} by ${size} Gray Go board`} className="go-board" style={pointGrid}>
          {board.flatMap((rowValue, row) =>
            Array.from(rowValue).map((_, col) => {
              const coordinate = { row, col };
              const label = coordinateLabel(coordinate);
              const symbol = cellAt(board, coordinate);
              const isSelected = selected?.row === row && selected.col === col;
              const isBlackMove =
                showLastMoves && blackMove?.row === row && blackMove.col === col;
              const isWhiteMove =
                showLastMoves && whiteMove?.row === row && whiteMove.col === col;
              const isCollision =
                showCollisions && collision?.row === row && collision.col === col;
              const isCapture = showCaptures && captures.has(label);
              const classes = [
                "board-point",
                `point-${symbol === "+" ? "empty" : symbol.toLowerCase()}`,
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
                  aria-label={`Point ${label} ${symbol === "+" ? "empty" : symbol}`}
                  className={classes}
                  key={label}
                  onClick={() => onSelect(coordinate)}
                  title={label}
                  type="button"
                >
                  <span aria-hidden="true" className="point-indicator" />
                  {symbol === "+" ? null : <span aria-hidden="true" className="go-stone" />}
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
