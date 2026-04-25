"""Repository implementations."""

from __future__ import annotations

from threading import RLock

from graygo_arena.application.models import (
    AgentCallRecord,
    GameEvent,
    GameRecord,
    SeatSession,
    TranscriptRecord,
    TranscriptView,
    TurnRecord,
)


class InMemoryRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.games: dict[str, GameRecord] = {}
        self.seats: dict[str, SeatSession] = {}
        self.turns: list[TurnRecord] = []
        self.calls: list[AgentCallRecord] = []
        self.transcripts: list[TranscriptRecord] = []
        self.events: list[GameEvent] = []

    def create_game(self, game: GameRecord, seats: tuple[SeatSession, SeatSession]) -> None:
        with self._lock:
            self.games[game.id] = game
            for seat in seats:
                self.seats[seat.id] = seat

    def save_game(self, game: GameRecord) -> None:
        with self._lock:
            self.games[game.id] = game

    def get_game(self, game_id: str) -> GameRecord:
        with self._lock:
            return self.games[game_id]

    def get_seats(self, game_id: str) -> tuple[SeatSession, SeatSession]:
        with self._lock:
            seats = tuple(seat for seat in self.seats.values() if seat.game_id == game_id)
        black = next((seat for seat in seats if seat.color == "black"), None)
        white = next((seat for seat in seats if seat.color == "white"), None)
        if black is None or white is None:
            msg = f"expected exactly two seats for game {game_id}"
            raise ValueError(msg)
        return (black, white)

    def get_seat(self, seat_id: str) -> SeatSession:
        with self._lock:
            return self.seats[seat_id]

    def update_seat(self, seat: SeatSession) -> None:
        with self._lock:
            self.seats[seat.id] = seat

    def list_public_history(self, game_id: str) -> tuple[str, ...]:
        return tuple(item.text for item in self.list_transcripts(game_id, "public"))

    def list_private_history(self, seat_session_id: str) -> tuple[str, ...]:
        with self._lock:
            return tuple(
                item.text for item in self.transcripts if item.seat_session_id == seat_session_id
            )

    def save_turn(self, turn: TurnRecord) -> None:
        with self._lock:
            self.turns.append(turn)

    def save_agent_call(self, call: AgentCallRecord) -> None:
        with self._lock:
            self.calls.append(call)

    def save_transcript(self, transcript: TranscriptRecord) -> None:
        with self._lock:
            self.transcripts.append(transcript)

    def save_event(self, event: GameEvent) -> None:
        with self._lock:
            self.events.append(event)

    def list_turns(self, game_id: str) -> tuple[TurnRecord, ...]:
        with self._lock:
            return tuple(turn for turn in self.turns if turn.game_id == game_id)

    def get_turn(self, game_id: str, turn_index: int) -> TurnRecord:
        for turn in self.list_turns(game_id):
            if turn.turn_index == turn_index:
                return turn
        msg = f"turn {turn_index} not found for game {game_id}"
        raise KeyError(msg)

    def list_transcripts(self, game_id: str, view: TranscriptView) -> tuple[TranscriptRecord, ...]:
        with self._lock:
            if view == "debug":
                return tuple(item for item in self.transcripts if item.game_id == game_id)
            return tuple(
                item
                for item in self.transcripts
                if item.game_id == game_id and item.view == view
            )

    def list_events(self, game_id: str) -> tuple[GameEvent, ...]:
        with self._lock:
            return tuple(event for event in self.events if event.game_id == game_id)
