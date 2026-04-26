import { cellAt, coordinateLabel, toroidalNeighbors, type Coordinate } from "../game/board";

type CellInspectorProps = {
  board: string[];
  selected: Coordinate | null;
};

export function CellInspector({ board, selected }: CellInspectorProps) {
  if (!selected) {
    return (
      <section className="panel">
        <h2>Point Inspector</h2>
        <p className="muted">Select a board point.</p>
      </section>
    );
  }
  const neighbors = toroidalNeighbors(selected, board.length).map((coordinate) =>
    coordinateLabel(coordinate)
  );
  return (
    <section className="panel">
      <h2>Point Inspector</h2>
      <dl className="kv-list">
        <div>
          <dt>Coordinate</dt>
          <dd>{coordinateLabel(selected)}</dd>
        </div>
        <div>
          <dt>Contents</dt>
          <dd>{cellAt(board, selected)}</dd>
        </div>
        <div>
          <dt>Neighbors</dt>
          <dd>{neighbors.join(", ")}</dd>
        </div>
      </dl>
    </section>
  );
}
