"""Application-layer data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from graygo_arena.engine import (
    Board,
    ForbiddenState,
    TurnResolution,
)
from graygo_arena.engine.moves import SeatColor

type GameStatus = Literal["created", "running", "paused", "stopped", "finished", "error"]
type InvalidMovePolicy = Literal["pass", "error", "forfeit"]
type TranscriptView = Literal["public", "black_private", "white_private", "debug"]


def _empty_str_tuple() -> tuple[str, ...]:
    return ()


def _empty_dict() -> dict[str, str]:
    return {}


def _default_black_config() -> SeatConfig:
    return SeatConfig("fake_random", "deterministic", "fake")


def _default_white_config() -> SeatConfig:
    return SeatConfig("fake_random", "deterministic", "fake")


@dataclass(frozen=True)
class SeatConfig:
    provider: str
    model: str
    credential_ref: str
    temperature: float = 0.0
    max_output_tokens: int = 256
    script: tuple[str, ...] = field(default_factory=_empty_str_tuple)


@dataclass(frozen=True)
class CreateGameCommand:
    board_size: int = 7
    ruleset: Literal["graygo-v1"] = "graygo-v1"
    black: SeatConfig = field(default_factory=_default_black_config)
    white: SeatConfig = field(default_factory=_default_white_config)
    max_turns: int = 200
    show_private_summaries_in_ui: bool = True
    auto_run: bool = False
    invalid_move_policy: InvalidMovePolicy = "pass"


@dataclass(frozen=True)
class SeatSession:
    id: str
    game_id: str
    color: SeatColor
    provider: str
    model: str
    credential_ref: str
    local_history: tuple[str, ...] = field(default_factory=_empty_str_tuple)
    provider_session_id: str | None = None
    previous_response_id: str | None = None
    script: tuple[str, ...] = field(default_factory=_empty_str_tuple)


@dataclass(frozen=True)
class GameRecord:
    id: str
    board_size: int
    ruleset: Literal["graygo-v1"]
    status: GameStatus
    current_turn: int
    board: Board
    forbidden: ForbiddenState
    double_pass_count: int
    black_seat_id: str
    white_seat_id: str
    max_turns: int
    invalid_move_policy: InvalidMovePolicy
    show_private_summaries_in_ui: bool


@dataclass(frozen=True)
class ProviderMoveRequest:
    game_id: str
    seat_session_id: str
    color: SeatColor
    model: str
    board_key: str
    board_rows: tuple[str, ...]
    legal_moves: tuple[str, ...]
    public_history: tuple[str, ...]
    private_history: tuple[str, ...]
    turn_index: int


@dataclass(frozen=True)
class ProviderMoveResponse:
    board_key: str
    move: str
    raw_response: str
    strategic_summary: str = ""
    metadata: dict[str, str] = field(default_factory=_empty_dict)


@dataclass(frozen=True)
class AgentCallRecord:
    id: str
    game_id: str
    turn_index: int
    seat_session_id: str
    color: SeatColor
    provider: str
    model: str
    prompt_board_key: str
    raw_response: str
    parsed_move: str
    valid: bool
    error: str | None = None
    attempt: int = 1


@dataclass(frozen=True)
class TurnRecord:
    id: str
    game_id: str
    turn_index: int
    pre_board_key: str
    post_board_key: str
    black_move: str
    white_move: str
    resolution: TurnResolution
    status: Literal["resolved", "invalid", "finished"]


@dataclass(frozen=True)
class TranscriptRecord:
    id: str
    game_id: str
    turn_index: int
    seat_session_id: str | None
    view: TranscriptView
    text: str


@dataclass(frozen=True)
class GameEvent:
    id: str
    game_id: str
    event_type: str
    payload: dict[str, str]


@dataclass(frozen=True)
class StepResult:
    game: GameRecord
    turn: TurnRecord
    black_call: AgentCallRecord
    white_call: AgentCallRecord
    events: tuple[GameEvent, ...]


class ProviderAdapter(Protocol):
    def request_move(
        self, request: ProviderMoveRequest, seat: SeatSession
    ) -> ProviderMoveResponse: ...


class ProviderRegistry(Protocol):
    def adapter_for(self, provider: str) -> ProviderAdapter: ...


class GameRepository(Protocol):
    def create_game(self, game: GameRecord, seats: tuple[SeatSession, SeatSession]) -> None: ...

    def save_game(self, game: GameRecord) -> None: ...

    def get_game(self, game_id: str) -> GameRecord: ...

    def get_seats(self, game_id: str) -> tuple[SeatSession, SeatSession]: ...

    def get_seat(self, seat_id: str) -> SeatSession: ...

    def update_seat(self, seat: SeatSession) -> None: ...

    def list_public_history(self, game_id: str) -> tuple[str, ...]: ...

    def list_private_history(self, seat_session_id: str) -> tuple[str, ...]: ...

    def save_turn(self, turn: TurnRecord) -> None: ...

    def save_agent_call(self, call: AgentCallRecord) -> None: ...

    def save_transcript(self, transcript: TranscriptRecord) -> None: ...

    def save_event(self, event: GameEvent) -> None: ...

    def list_turns(self, game_id: str) -> tuple[TurnRecord, ...]: ...

    def get_turn(self, game_id: str, turn_index: int) -> TurnRecord: ...

    def list_transcripts(
        self, game_id: str, view: TranscriptView
    ) -> tuple[TranscriptRecord, ...]: ...

    def list_events(self, game_id: str) -> tuple[GameEvent, ...]: ...

    def list_agent_calls(self, game_id: str) -> tuple[AgentCallRecord, ...]: ...
