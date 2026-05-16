import type { TurnResponse } from "../api/client";
import {
  cellAt,
  coordinateLabel,
  flattenCaptureLabels,
  parseCoordinate,
  toroidalNeighbors,
  wrapBoardIndex,
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
  const virtualPadding = size === 9 ? 2 : 0;
  const renderSize = size + virtualPadding * 2;
  const isVirtualBoard = virtualPadding > 0;
  const virtualRows = Array.from({ length: renderSize }, (_, row) =>
    wrapBoardIndex(row - virtualPadding, size)
  );
  const virtualCols = Array.from({ length: renderSize }, (_, col) =>
    wrapBoardIndex(col - virtualPadding, size)
  );
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
  const columnGrid = { gridTemplateColumns: `2rem repeat(${renderSize}, var(--point-size))` };
  const rowGrid = { gridTemplateRows: `repeat(${renderSize}, var(--point-size))` };
  const pointGrid = {
    gridTemplateColumns: `repeat(${renderSize}, var(--point-size))`,
    gridTemplateRows: `repeat(${renderSize}, var(--point-size))`
  };
  const boardLabel = isVirtualBoard
    ? `${renderSize} by ${renderSize} virtual Gray Go board over ${size} by ${size} board`
    : `${size} by ${size} Gray Go board`;
  const boardClasses = ["board-grid", isVirtualBoard ? "is-virtual-board" : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={boardClasses}>
      <div className="board-col-axis" style={columnGrid}>
        <div className="board-axis" />
        {virtualCols.map((realCol, col) => (
          <div className="board-axis" key={`col-${col}`}>
            {realCol + 1}
          </div>
        ))}
      </div>
      <div className="board-body">
        <div className="board-row-axis" style={rowGrid}>
          {virtualRows.map((realRow, row) => (
            <div className="board-axis" key={`row-${row}`}>
              {String.fromCharCode("a".charCodeAt(0) + realRow)}
            </div>
          ))}
        </div>
        <div aria-label={boardLabel} className="go-board" style={pointGrid}>
          {Array.from({ length: renderSize }, (_, virtualRow) =>
            Array.from({ length: renderSize }, (_, virtualCol) => {
              const row = virtualRows[virtualRow];
              const col = virtualCols[virtualCol];
              const coordinate = { row, col };
              const label = coordinateLabel(coordinate);
              const symbol = cellAt(board, coordinate);
              const isSelected = selected?.row === row && selected.col === col;
              const isVirtualMargin =
                isVirtualBoard &&
                (virtualRow < virtualPadding ||
                  virtualRow >= renderSize - virtualPadding ||
                  virtualCol < virtualPadding ||
                  virtualCol >= renderSize - virtualPadding);
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
                isCapture ? "is-capture" : "",
                isVirtualMargin ? "is-virtual-margin" : ""
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <button
                  aria-label={`Point ${label} ${symbol === "+" ? "empty" : symbol}`}
                  className={classes}
                  key={`point-${virtualRow}-${virtualCol}`}
                  onClick={() => onSelect(coordinate)}
                  title={isVirtualMargin ? `${label} virtual` : label}
                  type="button"
                >
                  <span aria-hidden="true" className="point-indicator" />
                  {symbol === "+" ? null : <span aria-hidden="true" className="go-stone" />}
                </button>
              );
            })
          ).flat()}
        </div>
      </div>
    </div>
  );
}
