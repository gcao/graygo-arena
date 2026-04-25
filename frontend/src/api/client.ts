export type ProviderInfo = {
  id: string;
  provider: string;
  auth_type: string;
  configured: boolean;
  models: string[];
};

export type SeatConfigRequest = {
  provider: string;
  credential_ref: string;
  model: string;
  temperature?: number;
  max_output_tokens?: number;
  script?: string[];
};

export type CreateGameRequest = {
  board_size: number;
  ruleset: "graygo-v1";
  black: SeatConfigRequest;
  white: SeatConfigRequest;
  max_turns: number;
  show_private_summaries_in_ui: boolean;
  auto_run: boolean;
  invalid_move_policy: "pass";
};

export type GameResponse = {
  id: string;
  status: string;
  board_size: number;
  ruleset: string;
  current_turn: number;
  board: string[];
  board_key: string;
  black_seat_id: string;
  white_seat_id: string;
  double_pass_count: number;
  max_turns: number;
};

export type TurnResponse = {
  turn_index: number;
  pre_board_key: string;
  post_board_key: string;
  black_move: string;
  white_move: string;
  status: string;
  captures: string[];
  forbidden_updates: string[];
};

export type StepResponse = {
  game: GameResponse;
  turn: TurnResponse;
};

export type TranscriptView = "public" | "black_private" | "white_private" | "debug";

export type TranscriptResponse = {
  view: TranscriptView;
  entries: string[];
};

export type EventResponse = {
  id: string;
  event_type: string;
  payload: Record<string, string>;
};

export type ExportBundleResponse = {
  version: string;
  game: Record<string, unknown>;
  seats: Record<string, unknown>[];
  turns: Record<string, unknown>[];
  agent_calls: Record<string, unknown>[];
  transcripts: Record<string, unknown>[];
  events: Record<string, unknown>[];
};

export type GuardrailCheckResponse = {
  name: string;
  ok: boolean;
  detail: string;
};

export async function listProviders(): Promise<ProviderInfo[]> {
  return request<ProviderInfo[]>("/api/providers");
}

export async function createGame(payload: CreateGameRequest): Promise<GameResponse> {
  return request<GameResponse>("/api/games", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getGame(gameId: string): Promise<GameResponse> {
  return request<GameResponse>(`/api/games/${gameId}`);
}

export async function startGame(gameId: string): Promise<GameResponse> {
  return request<GameResponse>(`/api/games/${gameId}/start`, { method: "POST" });
}

export async function pauseGame(gameId: string): Promise<GameResponse> {
  return request<GameResponse>(`/api/games/${gameId}/pause`, { method: "POST" });
}

export async function resumeGame(gameId: string): Promise<GameResponse> {
  return request<GameResponse>(`/api/games/${gameId}/resume`, { method: "POST" });
}

export async function stopGame(gameId: string): Promise<GameResponse> {
  return request<GameResponse>(`/api/games/${gameId}/stop`, { method: "POST" });
}

export async function stepGame(gameId: string): Promise<StepResponse> {
  return request<StepResponse>(`/api/games/${gameId}/step`, { method: "POST" });
}

export async function autorunGame(gameId: string): Promise<StepResponse[]> {
  return request<StepResponse[]>(`/api/games/${gameId}/autorun`, { method: "POST" });
}

export async function listTurns(gameId: string): Promise<TurnResponse[]> {
  return request<TurnResponse[]>(`/api/games/${gameId}/turns`);
}

export async function getTranscript(
  gameId: string,
  view: TranscriptView
): Promise<TranscriptResponse> {
  return request<TranscriptResponse>(`/api/games/${gameId}/transcript?view=${view}`);
}

export async function listEvents(gameId: string): Promise<EventResponse[]> {
  return request<EventResponse[]>(`/api/games/${gameId}/events/list`);
}

export async function exportGame(gameId: string): Promise<ExportBundleResponse> {
  return request<ExportBundleResponse>(`/api/games/${gameId}/export`);
}

export async function getGuardrails(gameId: string): Promise<GuardrailCheckResponse[]> {
  return request<GuardrailCheckResponse[]>(`/api/games/${gameId}/guardrails`);
}

export async function getProviderSettings(): Promise<ProviderInfo[]> {
  return request<ProviderInfo[]>("/api/settings/providers");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    }
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  return (await response.json()) as T;
}
