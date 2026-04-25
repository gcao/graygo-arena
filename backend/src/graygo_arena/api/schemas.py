"""FastAPI request and response schemas."""

from __future__ import annotations

from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from graygo_arena.application.guardrails import GuardrailCheck
from graygo_arena.application.models import (
    CreateGameCommand,
    GameEvent,
    GameRecord,
    SeatConfig,
    StepResult,
    TranscriptRecord,
    TranscriptView,
    TurnRecord,
)
from graygo_arena.providers.base import ProviderInfo, ProviderTestResult


class SeatConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "fake_random"
    credential_ref: str = "fake"
    model: str = "deterministic"
    temperature: float = 0.0
    max_output_tokens: int = 256
    script: tuple[str, ...] = ()


class CreateGameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    board_size: int = Field(default=7, ge=3, le=26)
    ruleset: str = "graygo-v1"
    black: SeatConfigRequest = Field(default_factory=SeatConfigRequest)
    white: SeatConfigRequest = Field(default_factory=SeatConfigRequest)
    max_turns: int = Field(default=200, ge=1)
    show_private_summaries_in_ui: bool = True
    auto_run: bool = False
    invalid_move_policy: str = "pass"

    def to_command(self) -> CreateGameCommand:
        return CreateGameCommand(
            board_size=self.board_size,
            ruleset="graygo-v1",
            black=_seat_config(self.black),
            white=_seat_config(self.white),
            max_turns=self.max_turns,
            show_private_summaries_in_ui=self.show_private_summaries_in_ui,
            auto_run=self.auto_run,
            invalid_move_policy="pass",
        )


class ProviderTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str = "default"


class ProviderInfoResponse(BaseModel):
    id: str
    provider: str
    auth_type: str
    configured: bool
    models: tuple[str, ...]


class ProviderTestResponse(BaseModel):
    provider: str
    model: str
    ok: bool
    message: str


class GameResponse(BaseModel):
    id: str
    status: str
    board_size: int
    ruleset: str
    current_turn: int
    board: tuple[str, ...]
    board_key: str
    black_seat_id: str
    white_seat_id: str
    double_pass_count: int
    max_turns: int


class TurnResponse(BaseModel):
    turn_index: int
    pre_board_key: str
    post_board_key: str
    black_move: str
    white_move: str
    status: str
    captures: tuple[str, ...]
    forbidden_updates: tuple[str, ...]


class StepResponse(BaseModel):
    game: GameResponse
    turn: TurnResponse


class TranscriptResponse(BaseModel):
    view: TranscriptView
    entries: tuple[str, ...]


class EventResponse(BaseModel):
    id: str
    event_type: str
    payload: dict[str, str]


class ExportBundleResponse(BaseModel):
    version: str
    game: dict[str, object]
    seats: list[dict[str, object]]
    turns: list[dict[str, object]]
    agent_calls: list[dict[str, object]]
    transcripts: list[dict[str, object]]
    events: list[dict[str, object]]


class GuardrailCheckResponse(BaseModel):
    name: str
    ok: bool
    detail: str


def provider_info_response(info: ProviderInfo) -> ProviderInfoResponse:
    return ProviderInfoResponse(**info.__dict__)


def provider_test_response(result: ProviderTestResult) -> ProviderTestResponse:
    return ProviderTestResponse(**result.__dict__)


def game_response(game: GameRecord) -> GameResponse:
    return GameResponse(
        id=game.id,
        status=game.status,
        board_size=game.board_size,
        ruleset=game.ruleset,
        current_turn=game.current_turn,
        board=tuple(game.board.to_key().split("/")),
        board_key=game.board.to_key(),
        black_seat_id=game.black_seat_id,
        white_seat_id=game.white_seat_id,
        double_pass_count=game.double_pass_count,
        max_turns=game.max_turns,
    )


def turn_response(turn: TurnRecord) -> TurnResponse:
    captures = tuple(
        ",".join(coordinate.to_label() for coordinate in capture.coordinates)
        for capture in turn.resolution.captures
    )
    forbidden_updates = tuple(
        f"{update.color}:{','.join(coordinate.to_label() for coordinate in update.coordinates)}"
        for update in turn.resolution.forbidden_updates
    )
    return TurnResponse(
        turn_index=turn.turn_index,
        pre_board_key=turn.pre_board_key,
        post_board_key=turn.post_board_key,
        black_move=turn.black_move,
        white_move=turn.white_move,
        status=turn.status,
        captures=captures,
        forbidden_updates=forbidden_updates,
    )


def step_response(result: StepResult) -> StepResponse:
    return StepResponse(game=game_response(result.game), turn=turn_response(result.turn))


def transcript_response(
    view: TranscriptView,
    entries: tuple[TranscriptRecord, ...],
) -> TranscriptResponse:
    return TranscriptResponse(view=view, entries=tuple(entry.text for entry in entries))


def event_response(event: GameEvent) -> EventResponse:
    return EventResponse(id=event.id, event_type=event.event_type, payload=event.payload)


def export_bundle_response(bundle: dict[str, object]) -> ExportBundleResponse:
    return ExportBundleResponse(
        version=cast(str, bundle["version"]),
        game=cast(dict[str, object], bundle["game"]),
        seats=cast(list[dict[str, object]], bundle["seats"]),
        turns=cast(list[dict[str, object]], bundle["turns"]),
        agent_calls=cast(list[dict[str, object]], bundle["agent_calls"]),
        transcripts=cast(list[dict[str, object]], bundle["transcripts"]),
        events=cast(list[dict[str, object]], bundle["events"]),
    )


def guardrail_check_response(check: GuardrailCheck) -> GuardrailCheckResponse:
    return GuardrailCheckResponse(name=check.name, ok=check.ok, detail=check.detail)


def _seat_config(request: SeatConfigRequest) -> SeatConfig:
    return SeatConfig(
        provider=request.provider,
        model=request.model,
        credential_ref=request.credential_ref,
        temperature=request.temperature,
        max_output_tokens=request.max_output_tokens,
        script=request.script,
    )
