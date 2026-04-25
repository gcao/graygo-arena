export type CellSymbol = "+" | "B" | "W" | "G";

export type Coordinate = {
  row: number;
  col: number;
};

export function coordinateLabel(coordinate: Coordinate): string {
  return `${String.fromCharCode("a".charCodeAt(0) + coordinate.row)}${coordinate.col + 1}`;
}

export function parseCoordinate(label: string): Coordinate | null {
  if (label === "PASS" || label.length < 2) {
    return null;
  }
  const row = label.charCodeAt(0) - "a".charCodeAt(0);
  const col = Number(label.slice(1)) - 1;
  if (!Number.isInteger(row) || !Number.isInteger(col) || row < 0 || col < 0) {
    return null;
  }
  return { row, col };
}

export function toroidalNeighbors(coordinate: Coordinate, size: number): Coordinate[] {
  return [
    { row: (coordinate.row - 1 + size) % size, col: coordinate.col },
    { row: (coordinate.row + 1) % size, col: coordinate.col },
    { row: coordinate.row, col: (coordinate.col - 1 + size) % size },
    { row: coordinate.row, col: (coordinate.col + 1) % size }
  ];
}

export function cellAt(board: string[], coordinate: Coordinate): CellSymbol {
  return board[coordinate.row]?.[coordinate.col] as CellSymbol;
}

export function flattenCaptureLabels(captures: string[]): string[] {
  return captures.flatMap((entry) => entry.split(",").filter(Boolean));
}
