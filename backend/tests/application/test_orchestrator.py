from __future__ import annotations

from dataclasses import replace

import pytest

from graygo_arena.application.models import (
    AgentCallRecord,
    CreateGameCommand,
    GameEvent,
    GameRecord,
    ProviderMoveRequest,
    ProviderMoveResponse,
    SeatConfig,
    SeatSession,
    TranscriptRecord,
    TurnRecord,
)
from graygo_arena.application.orchestrator import GameOrchestrator


class MemoryRepository:
    def __init__(self) -> None:
        self.games: dict[str, GameRecord] = {}
        self.seats: dict[str, SeatSession] = {}
        self.turns: list[TurnRecord] = []
        self.calls: list[AgentCallRecord] = []
        self.transcripts: list[TranscriptRecord] = []
        self.events: list[GameEvent] = []

    def create_game(self, game: GameRecord, seats: tuple[SeatSession, SeatSession]) -> None:
        self.games[game.id] = game
        for seat in seats:
            self.seats[seat.id] = seat

    def save_game(self, game: GameRecord) -> None:
        self.games[game.id] = game

    def get_game(self, game_id: str) -> GameRecord:
        return self.games[game_id]

    def get_seats(self, game_id: str) -> tuple[SeatSession, SeatSession]:
        seats = tuple(seat for seat in self.seats.values() if seat.game_id == game_id)
        return (seats[0], seats[1])

    def get_seat(self, seat_id: str) -> SeatSession:
        return self.seats[seat_id]

    def update_seat(self, seat: SeatSession) -> None:
        self.seats[seat.id] = seat

    def list_public_history(self, game_id: str) -> tuple[str, ...]:
        return tuple(
            item.text
            for item in self.transcripts
            if item.game_id == game_id and item.view == "public"
        )

    def list_private_history(self, seat_session_id: str) -> tuple[str, ...]:
        return tuple(
            item.text for item in self.transcripts if item.seat_session_id == seat_session_id
        )

    def save_turn(self, turn: TurnRecord) -> None:
        self.turns.append(turn)

    def save_agent_call(self, call: AgentCallRecord) -> None:
        self.calls.append(call)

    def save_transcript(self, transcript: TranscriptRecord) -> None:
        self.transcripts.append(transcript)

    def save_event(self, event: GameEvent) -> None:
        self.events.append(event)


class SequenceProvider:
    def __init__(self, moves: list[str]) -> None:
        self.moves = moves
        self.requests: list[ProviderMoveRequest] = []

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        self.requests.append(request)
        index = min(len(self.requests) - 1, len(self.moves) - 1)
        move = self.moves[index]
        return ProviderMoveResponse(
            board_key=request.board_key,
            move=move,
            raw_response=f"{seat.color}:{move}",
            strategic_summary=f"choose {move}",
        )


class StaticRegistry:
    def __init__(self, black_provider: SequenceProvider, white_provider: SequenceProvider) -> None:
        self.black_provider = black_provider
        self.white_provider = white_provider

    def adapter_for(self, provider: str) -> SequenceProvider:
        if provider == "black_provider":
            return self.black_provider
        if provider == "white_provider":
            return self.white_provider
        return self.black_provider


def counter_ids():
    counts: dict[str, int] = {}

    def make_id(prefix: str) -> str:
        counts[prefix] = counts.get(prefix, 0) + 1
        return f"{prefix}_{counts[prefix]}"

    return make_id


def make_orchestrator(
    black_moves: list[str],
    white_moves: list[str],
) -> tuple[GameOrchestrator, MemoryRepository, SequenceProvider, SequenceProvider]:
    repo = MemoryRepository()
    black = SequenceProvider(black_moves)
    white = SequenceProvider(white_moves)
    orchestrator = GameOrchestrator(
        repository=repo,
        providers=StaticRegistry(black, white),
        id_factory=counter_ids(),
    )
    return orchestrator, repo, black, white


def command(**overrides: object) -> CreateGameCommand:
    base = CreateGameCommand(
        board_size=7,
        black=SeatConfig("black_provider", "scripted", "fake"),
        white=SeatConfig("white_provider", "scripted", "fake"),
        max_turns=10,
    )
    return replace(base, **overrides)


def test_create_game_creates_distinct_seat_sessions_for_same_provider() -> None:
    orchestrator, repo, _, _ = make_orchestrator(["d4"], ["d5"])
    same_provider = SeatConfig("black_provider", "same-model", "fake")

    game = orchestrator.create_game(command(black=same_provider, white=same_provider))
    seats = repo.get_seats(game.id)

    assert game.black_seat_id != game.white_seat_id
    assert seats[0].provider == seats[1].provider == "black_provider"


def test_lifecycle_transitions() -> None:
    orchestrator, _, _, _ = make_orchestrator(["d4"], ["d5"])
    game = orchestrator.create_game(command())

    assert orchestrator.start_game(game.id).status == "running"
    assert orchestrator.pause_game(game.id).status == "paused"
    assert orchestrator.resume_game(game.id).status == "running"
    assert orchestrator.stop_game(game.id).status == "stopped"


def test_step_uses_same_pre_board_for_both_provider_requests() -> None:
    orchestrator, _, black, white = make_orchestrator(["d4"], ["d5"])
    game = orchestrator.create_game(command())

    result = orchestrator.step_game(game.id)

    assert black.requests[0].board_key == white.requests[0].board_key
    assert result.turn.black_move == "d4"
    assert result.turn.white_move == "d5"
    assert result.turn.post_board_key == "+++++++/+++++++/+++++++/+++BW++/+++++++/+++++++/+++++++"


def test_private_history_is_seat_scoped() -> None:
    orchestrator, repo, black, white = make_orchestrator(["d4", "e4"], ["d5", "e5"])
    game = orchestrator.create_game(command())

    orchestrator.step_game(game.id)
    orchestrator.step_game(game.id)

    assert len(black.requests[1].private_history) == 1
    assert len(white.requests[1].private_history) == 1
    assert black.requests[1].private_history != white.requests[1].private_history
    assert len(repo.transcripts) == 6


def test_invalid_output_retries_once_then_forces_pass() -> None:
    orchestrator, repo, black, _ = make_orchestrator(["z9", "z9"], ["d5"])
    game = orchestrator.create_game(command())

    result = orchestrator.step_game(game.id)

    assert len(black.requests) == 2
    assert result.black_call.valid is False
    assert result.black_call.parsed_move == "PASS"
    assert repo.calls[0].error is not None
    assert result.turn.black_move == "PASS"


def test_autorun_stops_at_max_turns() -> None:
    orchestrator, _, _, _ = make_orchestrator(["a1", "a2", "a3"], ["b1", "b2", "b3"])
    game = orchestrator.create_game(command(max_turns=2))

    results = orchestrator.autorun_game(game.id)

    assert len(results) == 2
    assert results[-1].game.status == "finished"


def test_cannot_step_paused_game() -> None:
    orchestrator, _, _, _ = make_orchestrator(["d4"], ["d5"])
    game = orchestrator.create_game(command())
    orchestrator.pause_game(game.id)

    with pytest.raises(ValueError):
        orchestrator.step_game(game.id)
