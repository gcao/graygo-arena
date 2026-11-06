# Gray Go Arena

The backend should own the game state. Each AI should only choose a move from the current resolved board. The backend then resolves the two moves simultaneously, applies collision/captures/forbidden updates, stores the new board, and asks both agents for the next move. This avoids the rule mistakes you saw earlier.

## Recommended architecture

```text
SPA UI
  |
  | REST + SSE/WebSocket
  v
Backend API
  |
  +-- Game Orchestrator
  |     - creates games
  |     - starts/stops/steps rounds
  |     - calls both AI seats without peeking
  |     - resolves simultaneous turns
  |
  +-- Gray Go Engine
  |     - board state
  |     - legal move validation
  |     - collision-to-gray
  |     - toroidal liberties
  |     - two-stage captures
  |     - forbidden points
  |     - scoring
  |
  +-- Agent Session Manager
  |     - one isolated session for Black
  |     - one isolated session for White
  |     - same provider/model allowed
  |     - never shares private analysis across seats
  |
  +-- Provider Adapters
  |     - OpenAI Responses adapter
  |     - Anthropic Claude Messages adapter
  |     - Claude Code OAuth/CLI adapter, optional
  |     - Codex CLI/API-key adapter, optional
  |     - local model adapter, optional
  |
  +-- Persistence
        - games
        - turns
        - boards
        - AI calls
        - private seat transcripts
        - public game log
```

I would use **FastAPI + Python** for the backend because you already have Python Gray Go logic and because Pydantic is useful for validating model outputs. Use **React + TypeScript + Vite** for the SPA. For persistence, use SQLite during local development and PostgreSQL once games/transcripts matter.

API tokens should stay entirely on the backend. OpenAI explicitly warns not to expose API keys in browser/client code and recommends loading them from environment variables or server-side key management; the OpenAI API uses bearer authentication. ([OpenAI Platform][1]) Anthropic’s direct Claude API uses `x-api-key`, `anthropic-version`, and `content-type` headers, while Claude Code OAuth-style tokens are specifically a Claude Code/CLI authentication path rather than the normal direct Claude API path. ([Claude API Docs][2])

## Captures before suicide

After both placements (or a collision-created gray stone), remove all
zero-liberty groups that contain no stone placed in this round. Compute all of
these captures before removing any of them. Groups containing a new stone,
including friendly stones joined to it, wait until those captures have been
removed and liberties recomputed.

Then remove every group that still has zero liberties simultaneously. Thus a
capturing move can survive by gaining liberties, while mutually dead played
groups are both removed as suicides. Black, white and gray follow the same order.

## Pass termination

A game ends after **two consecutive simultaneous rounds where both players choose
PASS**. The first PASS/PASS round sets `double_pass_count` to 1 and play continues;
the second consecutive PASS/PASS round sets it to 2 and finishes the game. A round
with any placement resets the streak to 0. The configured maximum-turn limit is
an independent ending condition.

## Core design principle: the backend is the arbiter

Do **not** let the AIs update the board. They are bad at doing exact game-state maintenance.

Instead, each round should work like this:

```text
1. Backend has current resolved board S.
2. Backend computes BoardKey(S).
3. Backend sends Black a prompt containing S.
4. Backend sends White a prompt containing S.
5. These calls are made from separate seat sessions.
6. Neither prompt includes the opponent’s move for this board.
7. Backend receives B move and W move.
8. Backend validates both moves.
9. Backend resolves both moves simultaneously.
10. Backend stores the new resolved board S'.
11. Backend broadcasts the result to the UI.
12. Repeat.
```

This guarantees the simultaneity property. Neither side can peek, because both prompts are generated from the same pre-move board before either result is injected into the other side’s context.

## Session isolation

You should model Black and White as two separate **seat sessions**, even when they use the exact same provider and model.

```ts
type SeatColor = "black" | "white";

type SeatSession = {
  id: string;
  gameId: string;
  color: SeatColor;
  provider: "openai" | "anthropic" | "claude_code" | "codex" | "local";
  model: string;
  credentialRef: string;       // env var alias, not the secret value
  providerSessionId?: string;  // OpenAI conversation id, if used
  previousResponseId?: string; // OpenAI response chain, if used
  localHistory: AgentMessage[];
  privateNotes: PrivateSeatNote[];
  createdAt: string;
};
```

For OpenAI, you can either manually manage each seat’s message history or use two separate state chains/conversation objects. OpenAI’s Responses API supports state via `previous_response_id`, and the Conversations API can persist conversation state with a durable identifier. ([OpenAI Platform][3]) The important part is that Black and White must not share the same OpenAI conversation or response chain.

For Anthropic direct API, I would manually store two separate `messages` arrays, one per seat, and call the Messages API independently for each side. For Claude Code or Codex CLI-style integrations, isolate process state too: use separate working directories/config directories per seat so cached sessions/transcripts cannot leak. Codex CLI/IDE can authenticate with ChatGPT or API key, and Codex caches login details locally, including under `CODEX_HOME` when file storage is used. ([OpenAI Developers][4])

## Provider credential model

Use `.env` only on the backend:

```bash
# OpenAI direct API
OPENAI_API_KEY=sk-...
OPENAI_PROJECT_ID=proj_...
OPENAI_ORG_ID=org_...

# Anthropic direct API
ANTHROPIC_API_KEY=sk-ant-...

# Claude Code / subscription-style CLI path, optional
CLAUDE_CODE_OAUTH_TOKEN=...

# Codex CLI, optional
CODEX_HOME_BLACK=.runtime/codex_black
CODEX_HOME_WHITE=.runtime/codex_white

# App
DATABASE_URL=sqlite:///./graygo.db
APP_SECRET=...
```

The UI should never ask the user to paste actual secrets. It should only see configured aliases:

```json
[
  {
    "id": "openai_default",
    "provider": "openai",
    "authType": "api_key",
    "configured": true,
    "models": ["gpt-5.5", "gpt-5.1-codex-max", "gpt-4.1"]
  },
  {
    "id": "anthropic_default",
    "provider": "anthropic",
    "authType": "api_key",
    "configured": true,
    "models": ["claude-opus-4.7", "claude-sonnet-4.6"]
  },
  {
    "id": "claude_code_oauth",
    "provider": "claude_code",
    "authType": "oauth_token",
    "configured": true,
    "models": ["default"]
  }
]
```

## Backend API

### Provider/config endpoints

```http
GET /api/providers
```

Returns providers and models available from `.env`, without exposing tokens.

```http
POST /api/providers/test
```

Body:

```json
{
  "provider": "openai",
  "credentialRef": "openai_default",
  "model": "gpt-5.5"
}
```

Returns whether the provider can complete a tiny test request.

### Game endpoints

```http
POST /api/games
```

Creates a game.

```json
{
  "boardSize": 7,
  "ruleset": "graygo-v1",
  "black": {
    "provider": "openai",
    "credentialRef": "openai_default",
    "model": "gpt-5.5",
    "temperature": 0.8,
    "maxOutputTokens": 1200
  },
  "white": {
    "provider": "anthropic",
    "credentialRef": "anthropic_default",
    "model": "claude-sonnet-4.6",
    "temperature": 0.8,
    "maxOutputTokens": 1200
  },
  "maxTurns": 200,
  "showPrivateSummariesInUi": true,
  "autoRun": false
}
```

Same model both sides is allowed:

```json
{
  "black": {
    "provider": "openai",
    "credentialRef": "openai_default",
    "model": "gpt-5.5"
  },
  "white": {
    "provider": "openai",
    "credentialRef": "openai_default",
    "model": "gpt-5.5"
  }
}
```

The backend still creates two seat sessions:

```text
seat_session_black != seat_session_white
```

```http
GET /api/games/{gameId}
```

Returns current game state.

```http
POST /api/games/{gameId}/start
POST /api/games/{gameId}/pause
POST /api/games/{gameId}/resume
POST /api/games/{gameId}/stop
```

Lifecycle controls.

```http
POST /api/games/{gameId}/step
```

Runs exactly one simultaneous turn:

```text
call Black + call White -> validate moves -> resolve -> persist -> broadcast
```

```http
POST /api/games/{gameId}/autorun
```

Runs until pause, game end, invalid-provider failure, or max turns.

```http
GET /api/games/{gameId}/events
```

SSE stream for UI updates.

Events:

```json
{ "type": "agent_call_started", "gameId": "...", "color": "black", "turn": 12 }
{ "type": "agent_call_finished", "gameId": "...", "color": "black", "turn": 12 }
{ "type": "turn_resolved", "gameId": "...", "turn": 12, "postBoard": ["..."] }
{ "type": "game_finished", "gameId": "...", "score": { "black": 25.5, "white": 23.5 } }
```

### Transcript endpoints

```http
GET /api/games/{gameId}/turns
GET /api/games/{gameId}/turns/{turnIndex}
GET /api/games/{gameId}/transcript?view=public
GET /api/games/{gameId}/transcript?view=black_private
GET /api/games/{gameId}/transcript?view=white_private
GET /api/games/{gameId}/transcript?view=debug
```

The public transcript contains only:

```text
board
BoardKey
B move
W move
captures
post-board
score estimate if available
```

Private transcripts contain each side’s own strategic summary and raw model output. The opponent never receives those.

## Data model

A minimal schema:

```sql
games (
  id text primary key,
  board_size integer not null,
  ruleset text not null,
  status text not null,
  current_turn integer not null,
  current_board_json jsonb not null,
  current_board_key text not null,
  forbidden_black_json jsonb not null,
  forbidden_white_json jsonb not null,
  double_pass_count integer not null,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

seat_sessions (
  id text primary key,
  game_id text not null references games(id),
  color text not null,
  provider text not null,
  model text not null,
  credential_ref text not null,
  provider_conversation_id text,
  previous_response_id text,
  local_history_json jsonb not null,
  created_at timestamptz not null
);

turns (
  id text primary key,
  game_id text not null references games(id),
  turn_index integer not null,
  pre_board_json jsonb not null,
  pre_board_key text not null,
  black_move text,
  white_move text,
  black_valid boolean,
  white_valid boolean,
  resolution_json jsonb,
  post_board_json jsonb,
  post_board_key text,
  captures_json jsonb,
  forbidden_updates_json jsonb,
  double_pass_count integer,
  status text not null,
  created_at timestamptz not null,
  resolved_at timestamptz
);

agent_calls (
  id text primary key,
  game_id text not null references games(id),
  turn_id text not null references turns(id),
  seat_session_id text not null references seat_sessions(id),
  color text not null,
  provider text not null,
  model text not null,
  prompt_json jsonb not null,
  raw_response text,
  parsed_response_json jsonb,
  move text,
  valid boolean,
  error text,
  latency_ms integer,
  input_tokens integer,
  output_tokens integer,
  created_at timestamptz not null
);
```

Do not store token values. Store only `credential_ref`.

## Agent output format

Use structured JSON, not free text. OpenAI supports structured outputs against JSON Schema, which is useful here because the backend can reject malformed outputs instead of trying to parse prose. ([OpenAI Platform][5]) Anthropic can also be instructed to emit JSON, though you should still validate server-side.

Recommended schema:

```json
{
  "board_key": "+++++++/+++++++/+++++++/+++++++/+++++++/+++++++/+++++++",
  "current_board_echo": [
    "+++++++",
    "+++++++",
    "+++++++",
    "+++++++",
    "+++++++",
    "+++++++",
    "+++++++"
  ],
  "update_audit": {
    "understood_board_key": true,
    "zero_liberty_check": "passed",
    "legal_moves_considered": ["d4", "c4", "d3"],
    "notes": "No captures yet; opening position."
  },
  "strategic_summary": {
    "objective": "Create central influence while avoiding predictable same-point collision.",
    "tactical_concerns": "Empty board; all points equivalent under torus, but simultaneous collision risk matters.",
    "candidate_moves": [
      { "move": "d4", "reason": "Central-looking anchor, though torus makes all points symmetric." },
      { "move": "c4", "reason": "Avoids the most obvious mirror collision." },
      { "move": "d3", "reason": "Equivalent alternative with some randomization." }
    ],
    "chosen_reason": "Choose a strong but not maximally obvious opening point."
  },
  "move": "c4"
}
```

Do not ask for hidden chain-of-thought. Ask for a concise visible strategic summary and candidate-move comparison. That gives the model a reasoning scaffold without polluting the opponent’s context or relying on inaccessible internal reasoning.

## Agent prompt shape

The backend prompt to each seat should be generated fresh from authoritative state.

```text
You are playing Gray Go as Black.

You must choose exactly one legal move from the current resolved board.
You are trying to maximize Black's final score.

Important:
- You must not assume the opponent's move for this board.
- The opponent is choosing simultaneously from this same BoardKey.
- Your move will be resolved by the server together with the opponent's move.
- Do not update the board yourself.
- Do not include hidden reasoning.
- Return only JSON matching the schema.

Current resolved board:
Board
  1234567
a +++++++
b +++++++
c +++++++
d +++++++
e +++++++
f +++++++
g +++++++

BoardKey=+++++++/+++++++/+++++++/+++++++/+++++++/+++++++/+++++++

Legal moves:
["a1", "a2", ..., "g7", "PASS"]

Recent resolved history:
Turn 0: none

Return:
{
  board_key,
  current_board_echo,
  update_audit,
  strategic_summary,
  move
}
```

For White, only color/objective changes. The board is identical for both seats on each round.

## Turn orchestration pseudocode

```python
async def run_one_turn(game_id: str) -> TurnResult:
    game = await repo.get_game_for_update(game_id)

    if game.status not in {"running", "created"}:
        raise InvalidState("game is not running")

    pre_board = game.current_board
    board_key = compute_board_key(pre_board)

    legal_black = engine.legal_moves(game, "black")
    legal_white = engine.legal_moves(game, "white")

    turn = await repo.create_turn(
        game_id=game.id,
        turn_index=game.current_turn,
        pre_board=pre_board,
        pre_board_key=board_key,
        status="agent_thinking",
    )

    black_session = await repo.get_seat_session(game.id, "black")
    white_session = await repo.get_seat_session(game.id, "white")

    black_prompt = prompt_builder.build(
        color="black",
        board=pre_board,
        board_key=board_key,
        legal_moves=legal_black,
        public_history=await repo.get_public_history(game.id),
        private_history=await repo.get_private_history(black_session.id),
    )

    white_prompt = prompt_builder.build(
        color="white",
        board=pre_board,
        board_key=board_key,
        legal_moves=legal_white,
        public_history=await repo.get_public_history(game.id),
        private_history=await repo.get_private_history(white_session.id),
    )

    # Important: no opponent current move is included in either prompt.
    black_task = agent_runner.call(black_session, black_prompt)
    white_task = agent_runner.call(white_session, white_prompt)

    black_reply, white_reply = await asyncio.gather(black_task, white_task)

    black_move = parse_and_validate_move(black_reply, board_key, legal_black)
    white_move = parse_and_validate_move(white_reply, board_key, legal_white)

    resolution = engine.resolve_turn(
        game_state=game,
        black_move=black_move,
        white_move=white_move,
    )

    await repo.save_agent_call(turn.id, black_session.id, black_reply, black_move)
    await repo.save_agent_call(turn.id, white_session.id, white_reply, white_move)

    await repo.resolve_turn(
        turn.id,
        black_move=black_move,
        white_move=white_move,
        resolution=resolution,
    )

    await repo.update_game_from_resolution(game.id, resolution)

    await event_bus.publish("turn_resolved", serialize_turn(turn, resolution))

    return resolution
```

## Invalid output handling

The backend should be strict.

If a model returns malformed JSON:

```text
Retry once with the same board, same BoardKey, same legal-move list, and an error message.
```

If it returns an illegal coordinate:

```text
Retry once.
If still invalid, either force PASS or forfeit, depending on game setting.
```

Suggested game setting:

```json
{
  "invalidMovePolicy": "retry_then_pass"
}
```

Options:

```text
retry_then_pass
retry_then_forfeit
manual_intervention
```

For experiments, I would use `manual_intervention` first so you can inspect failure modes.

## Provider adapter interface

```ts
interface ModelProviderAdapter {
  id: string;

  listConfiguredModels(): Promise<ModelDescriptor[]>;

  createSeatSession(input: {
    gameId: string;
    color: "black" | "white";
    model: string;
    credentialRef: string;
    options: ModelOptions;
  }): Promise<ProviderSessionRef>;

  completeMove(input: {
    session: SeatSession;
    prompt: AgentPrompt;
    responseSchema: JsonSchema;
    timeoutMs: number;
  }): Promise<ModelMoveResponse>;
}
```

### OpenAI adapter

Use server-side `OPENAI_API_KEY`. For strict move parsing, use structured outputs when the selected model supports them. The Responses API accepts `model` and `input`, and OpenAI documents using bearer authentication for API calls. ([OpenAI Platform][6])

Session strategy:

```text
Option A: Manual history per seat, store=false.
Option B: Separate OpenAI conversation object per seat.
Option C: Separate previous_response_id chain per seat.
```

I prefer **manual history** for this project because you have complete control over exactly what context each seat sees.

### Anthropic direct API adapter

Use `ANTHROPIC_API_KEY` server-side. The direct API is RESTful at `https://api.anthropic.com`, and the general model interaction endpoint is the Messages API at `POST /v1/messages`. ([Claude API Docs][2])

Session strategy:

```text
Maintain separate local messages[] for Black and White.
Call Claude independently for each seat.
Validate JSON server-side.
```

### Claude Code OAuth adapter

Treat this as a separate adapter from direct Claude API. Claude Code supports `CLAUDE_CODE_OAUTH_TOKEN` for CI/scripts, while `ANTHROPIC_API_KEY` is the direct API-key path and `ANTHROPIC_AUTH_TOKEN` is a bearer-token path often used with gateways/proxies. ([Claude API Docs][7])

I would only implement this after the direct Anthropic adapter works, because CLI adapters are more operationally fragile.

### Codex adapter

For programmatic usage, the Codex docs recommend API key authentication for workflows like CI/CD, and they warn not to expose Codex execution in untrusted or public environments. ([OpenAI Developers][4]) If you run Codex CLI as a backend subprocess, configure separate `CODEX_HOME` directories for Black and White so cached auth/session state does not cross-contaminate. Codex file-based credential storage uses `auth.json` under `CODEX_HOME`, so treat those files as secrets. ([OpenAI Developers][4])

## SPA UI design

### Main screens

```text
1. New Game
2. Live Game
3. Game History
4. Provider Status
5. Settings
```

### New Game screen

Controls:

```text
Board size: 7x7 default
Ruleset: graygo-v1

Black:
  Provider dropdown
  Model dropdown
  Credential alias dropdown
  Temperature
  Max output tokens
  Reasoning/strategy verbosity: low / medium / high

White:
  Same controls

Run mode:
  Manual step
  Auto-run
  Auto-run delay
  Stop after N turns

Visibility:
  Show Black strategic summary
  Show White strategic summary
  Show raw model JSON
  Show backend resolution audit
```

Important: if the same model is selected for both sides, show:

```text
Same model selected for both sides. The backend will create two isolated seat sessions.
```

### Live Game screen

Layout:

```text
+----------------------------------------------------+
| Game status: running | Turn 18 | Auto-run: on      |
+----------------------+-----------------------------+
| Board                | Turn Resolution             |
|                      | B: d4                       |
|  1234567             | W: d4                       |
| a ++WGBB+            | Collision: d4 -> G          |
| b BWWWBG+            | Captures: d4 removed        |
| ...                  | BoardKey before/after       |
+----------------------+-----------------------------+
| Black panel          | White panel                 |
| model/provider       | model/provider              |
| current move         | current move                |
| strategic summary    | strategic summary           |
| raw JSON toggle      | raw JSON toggle             |
+----------------------------------------------------+
| Controls: Step | Run | Pause | Stop | Export       |
+----------------------------------------------------+
```

Board UI features:

```text
- 7x7 grid with row/column labels
- B/W/G/+ symbols
- highlight last Black move
- highlight last White move
- highlight collision points
- highlight captured stones from previous turn
- hover cell: coordinate, neighbors, group liberties
- toggle toroidal neighbor visualization
```

### History panel

Each turn:

```text
Turn 12
Pre BoardKey: ...
B: d4
W: d4
Placement: collision -> G at d4
Captures: d4
Post BoardKey: ...
```

Expandable:

```text
Black private strategic summary
White private strategic summary
Raw provider responses
Backend validation audit
```

Private summaries are visible to the human operator if enabled, but they are not inserted into the opponent’s future prompts.

## UI state types

```ts
type GameView = {
  id: string;
  status: "created" | "running" | "paused" | "finished" | "error";
  boardSize: number;
  board: string[];
  boardKey: string;
  currentTurn: number;
  black: SeatView;
  white: SeatView;
  lastTurn?: TurnView;
  scoreEstimate?: {
    black: number;
    white: number;
  };
};

type SeatView = {
  color: "black" | "white";
  provider: string;
  model: string;
  sessionId: string;
  lastMove?: string;
  lastStrategicSummary?: StrategicSummary;
  thinking: boolean;
  error?: string;
};

type TurnView = {
  turnIndex: number;
  preBoard: string[];
  preBoardKey: string;
  blackMove: string;
  whiteMove: string;
  placementEvents: PlacementEvent[];
  captures: string[];
  postBoard: string[];
  postBoardKey: string;
  validation: ValidationAudit;
};
```

## Backend prompt/privacy policy

The prompt builder should enforce these rules:

```text
Included in both seats' prompts:
- rules
- current resolved board
- current BoardKey
- legal moves for that color
- public resolved turn history
- score if game ended
- backend capture/legality audit from previous turns

Included only in Black's prompt:
- Black's own previous strategic summaries, if you choose to preserve them
- Black's own previous raw outputs, preferably summarized

Included only in White's prompt:
- White's own previous strategic summaries
- White's own previous raw outputs

Never included:
- opponent's private strategic summary
- opponent's raw model response
- opponent's pending move before the simultaneous turn is resolved
- API tokens
```

This is the main protection that lets the same model play both sides without leaking earlier thoughts.

## Strong recommendation: do not ask models to print boards as authority

The board shown in the UI should come from the backend engine only.

The model may echo the board as a validation check, but the backend should treat it as non-authoritative:

```text
authoritative_board = backend engine board
model_board_echo = diagnostic only
```

This single design choice will eliminate most of the illegal-board problems.

## Minimal implementation plan

Build in this order:

```text
1. Gray Go engine as a pure deterministic module.
2. Unit tests for board resolution, toroidal liberties, captures, gray collision, scoring.
3. In-memory game orchestrator with fake random agents.
4. REST API around orchestrator.
5. React board UI and manual step mode.
6. OpenAI provider adapter.
7. Anthropic provider adapter.
8. Persistent DB storage.
9. SSE/WebSocket live updates.
10. Optional CLI adapters for Codex/Claude Code.
```

The first milestone should not call any paid model. Use fake agents:

```python
class RandomLegalAgent:
    async def complete_move(self, prompt):
        return {"board_key": prompt.board_key, "move": random.choice(prompt.legal_moves)}
```

Then add a deterministic scripted agent:

```python
class ScriptedAgent:
    moves = ["d4", "d5", "c4", "PASS"]
```

Once the engine and UI are correct, plug in real model providers.

## Final verdict

The best version is:

```text
Backend = arbiter, state owner, session isolator, provider caller.
Frontend = configuration, visualization, controls, transcript inspection.
Models = move selectors only.
```

That architecture will let GPT, Claude, Codex, or the same model on both sides play without peeking, without sharing hidden/session context, and without relying on the model to do exact Gray Go bookkeeping.

[1]: https://platform.openai.com/docs/api-reference/authentication "API Overview | OpenAI API Reference"
[2]: https://docs.anthropic.com/claude/reference/getting-started-with-the-api "API Overview - Claude API Docs"
[3]: https://platform.openai.com/docs/guides/conversation-state "Conversation state | OpenAI API"
[4]: https://developers.openai.com/codex/auth "Authentication – Codex | OpenAI Developers"
[5]: https://platform.openai.com/docs/guides/structured-outputs "Structured model outputs | OpenAI API"
[6]: https://platform.openai.com/docs/api-reference/responses "Responses | OpenAI API Reference"
[7]: https://docs.anthropic.com/en/docs/claude-code/iam "Authentication - Claude Code Docs"
