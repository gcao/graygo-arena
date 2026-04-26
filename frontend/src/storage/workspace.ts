import type { GameResponse, TranscriptView } from "../api/client";

export type SeatForm = {
  provider: string;
  model: string;
  credential_ref: string;
};

export type GameConfigSnapshot = {
  black: SeatForm;
  white: SeatForm;
};

export type BoardDisplaySettings = {
  showNeighbors: boolean;
  showLastMoves: boolean;
  showCollisions: boolean;
  showCaptures: boolean;
};

export type WorkspaceSettings = {
  black: SeatForm;
  white: SeatForm;
  boardSize: number;
  maxTurns: number;
  transcriptView: TranscriptView;
  display: BoardDisplaySettings;
};

export type PersistedWorkspace = {
  activeGameId: string | null;
  game: GameResponse | null;
  gameConfig: GameConfigSnapshot | null;
  settings: WorkspaceSettings;
};

const STORAGE_KEY = "graygo-arena.workspace.v1";
const TRANSCRIPT_VIEWS = new Set<TranscriptView>([
  "public",
  "black_private",
  "white_private",
  "debug"
]);
const RESUMABLE_STATUSES = new Set(["created", "running", "paused"]);

export const defaultBlackSeat: SeatForm = {
  provider: "scripted_center",
  model: "default",
  credential_ref: "fake"
};

export const defaultWhiteSeat: SeatForm = {
  provider: "scripted_pass",
  model: "default",
  credential_ref: "fake"
};

export const defaultDisplaySettings: BoardDisplaySettings = {
  showNeighbors: true,
  showLastMoves: true,
  showCollisions: true,
  showCaptures: true
};

const defaultWorkspace: PersistedWorkspace = {
  activeGameId: null,
  game: null,
  gameConfig: null,
  settings: {
    black: defaultBlackSeat,
    white: defaultWhiteSeat,
    boardSize: 7,
    maxTurns: 40,
    transcriptView: "public",
    display: defaultDisplaySettings
  }
};

export function readPersistedWorkspace(): PersistedWorkspace {
  if (!hasLocalStorage()) {
    return defaultWorkspace;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaultWorkspace;
    }
    return normalizeWorkspace(JSON.parse(raw) as unknown);
  } catch {
    return defaultWorkspace;
  }
}

export function writePersistedWorkspace(workspace: PersistedWorkspace): void {
  if (!hasLocalStorage()) {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace));
  } catch {
    // Storage can be unavailable in private windows or locked-down browser contexts.
  }
}

export function isResumableGame(game: GameResponse | null): game is GameResponse {
  return game !== null && RESUMABLE_STATUSES.has(game.status);
}

function normalizeWorkspace(value: unknown): PersistedWorkspace {
  const record = objectRecord(value);
  if (!record) {
    return defaultWorkspace;
  }

  const game = normalizeGame(record.game);
  const activeGameId =
    typeof record.activeGameId === "string" && record.activeGameId
      ? record.activeGameId
      : game?.id ?? null;
  const settings = normalizeSettings(record.settings);

  return {
    activeGameId,
    game,
    gameConfig: normalizeGameConfig(record.gameConfig),
    settings
  };
}

function normalizeSettings(value: unknown): WorkspaceSettings {
  const record = objectRecord(value);
  if (!record) {
    return defaultWorkspace.settings;
  }
  return {
    black: normalizeSeat(record.black, defaultBlackSeat),
    white: normalizeSeat(record.white, defaultWhiteSeat),
    boardSize: clampNumber(record.boardSize, 7, 3, 13),
    maxTurns: clampNumber(record.maxTurns, 40, 1, 1000),
    transcriptView: normalizeTranscriptView(record.transcriptView),
    display: normalizeDisplay(record.display)
  };
}

function normalizeGameConfig(value: unknown): GameConfigSnapshot | null {
  const record = objectRecord(value);
  if (!record) {
    return null;
  }
  return {
    black: normalizeSeat(record.black, defaultBlackSeat),
    white: normalizeSeat(record.white, defaultWhiteSeat)
  };
}

function normalizeSeat(value: unknown, fallback: SeatForm): SeatForm {
  const record = objectRecord(value);
  if (!record) {
    return fallback;
  }
  return {
    provider: nonEmptyString(record.provider, fallback.provider),
    model: nonEmptyString(record.model, fallback.model),
    credential_ref: nonEmptyString(record.credential_ref, fallback.credential_ref)
  };
}

function normalizeDisplay(value: unknown): BoardDisplaySettings {
  const record = objectRecord(value);
  if (!record) {
    return defaultDisplaySettings;
  }
  return {
    showNeighbors: booleanOr(record.showNeighbors, defaultDisplaySettings.showNeighbors),
    showLastMoves: booleanOr(record.showLastMoves, defaultDisplaySettings.showLastMoves),
    showCollisions: booleanOr(record.showCollisions, defaultDisplaySettings.showCollisions),
    showCaptures: booleanOr(record.showCaptures, defaultDisplaySettings.showCaptures)
  };
}

function normalizeGame(value: unknown): GameResponse | null {
  const record = objectRecord(value);
  if (!record) {
    return null;
  }
  if (
    typeof record.id !== "string" ||
    typeof record.status !== "string" ||
    !Array.isArray(record.board)
  ) {
    return null;
  }
  return record as unknown as GameResponse;
}

function normalizeTranscriptView(value: unknown): TranscriptView {
  return typeof value === "string" && TRANSCRIPT_VIEWS.has(value as TranscriptView)
    ? (value as TranscriptView)
    : "public";
}

function clampNumber(value: unknown, fallback: number, min: number, max: number): number {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.min(max, Math.max(min, Math.trunc(value)))
    : fallback;
}

function nonEmptyString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function booleanOr(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function objectRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function hasLocalStorage(): boolean {
  return typeof window !== "undefined" && "localStorage" in window;
}
