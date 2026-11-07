"""Repository implementations."""

from __future__ import annotations

import json
import sqlite3
from threading import RLock
from typing import Literal, cast

from graygo_arena.application.models import (
    AgentCallRecord,
    GameEvent,
    GameRecord,
    GameStatus,
    InvalidMovePolicy,
    MoveSource,
    PendingMove,
    SeatSession,
    TranscriptRecord,
    TranscriptView,
    TurnRecord,
)
from graygo_arena.engine import (
    Board,
    CaptureByColor,
    CapturedColor,
    CaptureEvent,
    Coordinate,
    ForbiddenState,
    ForbiddenUpdate,
    GameState,
    PlacementEvent,
    RoundHistory,
    TurnResolution,
)
from graygo_arena.engine.moves import SeatColor
from graygo_arena.persistence.database import SQLiteDatabase


class InMemoryRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.games: dict[str, GameRecord] = {}
        self.seats: dict[str, SeatSession] = {}
        self.turns: list[TurnRecord] = []
        self.pending_moves: list[PendingMove] = []
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

    def save_pending_move(self, move: PendingMove) -> None:
        with self._lock:
            self.pending_moves = [
                item
                for item in self.pending_moves
                if not (
                    item.game_id == move.game_id
                    and item.turn_index == move.turn_index
                    and item.color == move.color
                )
            ]
            self.pending_moves.append(move)

    def get_pending_moves(self, game_id: str, turn_index: int) -> tuple[PendingMove, ...]:
        with self._lock:
            return tuple(
                item
                for item in self.pending_moves
                if item.game_id == game_id and item.turn_index == turn_index
            )

    def delete_pending_moves(self, game_id: str, turn_index: int) -> None:
        with self._lock:
            self.pending_moves = [
                item
                for item in self.pending_moves
                if not (item.game_id == game_id and item.turn_index == turn_index)
            ]

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
                item for item in self.transcripts if item.game_id == game_id and item.view == view
            )

    def list_events(self, game_id: str) -> tuple[GameEvent, ...]:
        with self._lock:
            return tuple(event for event in self.events if event.game_id == game_id)

    def list_agent_calls(self, game_id: str) -> tuple[AgentCallRecord, ...]:
        with self._lock:
            return tuple(call for call in self.calls if call.game_id == game_id)


class SQLiteRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def create_game(self, game: GameRecord, seats: tuple[SeatSession, SeatSession]) -> None:
        self.save_game(game)
        for seat in seats:
            self._save_seat(seat)

    def save_game(self, game: GameRecord) -> None:
        self._database.execute(
            """
            INSERT INTO games (
              id, board_size, ruleset, status, current_turn, board_key,
              forbidden_black_json, forbidden_white_json, double_pass_count,
              black_seat_id, white_seat_id, max_turns, invalid_move_policy,
              show_private_summaries_in_ui
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              status=excluded.status,
              current_turn=excluded.current_turn,
              board_key=excluded.board_key,
              forbidden_black_json=excluded.forbidden_black_json,
              forbidden_white_json=excluded.forbidden_white_json,
              double_pass_count=excluded.double_pass_count
            """,
            (
                game.id,
                game.board_size,
                game.ruleset,
                game.status,
                game.current_turn,
                game.board.to_key(),
                _coordinate_json(game.forbidden.black),
                _coordinate_json(game.forbidden.white),
                game.double_pass_count,
                game.black_seat_id,
                game.white_seat_id,
                game.max_turns,
                game.invalid_move_policy,
                int(game.show_private_summaries_in_ui),
            ),
        )

    def get_game(self, game_id: str) -> GameRecord:
        row = self._database.fetch_one("SELECT * FROM games WHERE id = ?", (game_id,))
        return GameRecord(
            id=cast(str, row["id"]),
            board_size=cast(int, row["board_size"]),
            ruleset="graygo-v1",
            status=cast(GameStatus, row["status"]),
            current_turn=cast(int, row["current_turn"]),
            board=Board.from_key(cast(str, row["board_key"])),
            forbidden=ForbiddenState(
                black=_coordinates_from_json(cast(str, row["forbidden_black_json"])),
                white=_coordinates_from_json(cast(str, row["forbidden_white_json"])),
            ),
            double_pass_count=cast(int, row["double_pass_count"]),
            black_seat_id=cast(str, row["black_seat_id"]),
            white_seat_id=cast(str, row["white_seat_id"]),
            max_turns=cast(int, row["max_turns"]),
            invalid_move_policy=cast(InvalidMovePolicy, row["invalid_move_policy"]),
            show_private_summaries_in_ui=bool(row["show_private_summaries_in_ui"]),
        )

    def get_seats(self, game_id: str) -> tuple[SeatSession, SeatSession]:
        rows = self._database.fetch_all(
            "SELECT * FROM seat_sessions WHERE game_id = ? ORDER BY color",
            (game_id,),
        )
        seats = tuple(_seat_from_row(row) for row in rows)
        black = next((seat for seat in seats if seat.color == "black"), None)
        white = next((seat for seat in seats if seat.color == "white"), None)
        if black is None or white is None:
            msg = f"expected exactly two seats for game {game_id}"
            raise ValueError(msg)
        return (black, white)

    def get_seat(self, seat_id: str) -> SeatSession:
        return _seat_from_row(
            self._database.fetch_one("SELECT * FROM seat_sessions WHERE id = ?", (seat_id,))
        )

    def update_seat(self, seat: SeatSession) -> None:
        self._save_seat(seat)

    def list_public_history(self, game_id: str) -> tuple[str, ...]:
        return tuple(item.text for item in self.list_transcripts(game_id, "public"))

    def list_private_history(self, seat_session_id: str) -> tuple[str, ...]:
        rows = self._database.fetch_all(
            "SELECT text FROM seat_transcripts WHERE seat_session_id = ? ORDER BY turn_index, id",
            (seat_session_id,),
        )
        return tuple(cast(str, row["text"]) for row in rows)

    def save_pending_move(self, move: PendingMove) -> None:
        self._database.execute(
            """
            INSERT INTO pending_moves (
              id, game_id, turn_index, seat_session_id, color, move, source,
              raw_response, valid, error, attempt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_id, turn_index, color) DO UPDATE SET
              id=excluded.id,
              seat_session_id=excluded.seat_session_id,
              move=excluded.move,
              source=excluded.source,
              raw_response=excluded.raw_response,
              valid=excluded.valid,
              error=excluded.error,
              attempt=excluded.attempt
            """,
            (
                move.id,
                move.game_id,
                move.turn_index,
                move.seat_session_id,
                move.color,
                move.move,
                move.source,
                move.raw_response,
                int(move.valid),
                move.error,
                move.attempt,
            ),
        )

    def get_pending_moves(self, game_id: str, turn_index: int) -> tuple[PendingMove, ...]:
        rows = self._database.fetch_all(
            """
            SELECT * FROM pending_moves
            WHERE game_id = ? AND turn_index = ?
            ORDER BY color
            """,
            (game_id, turn_index),
        )
        return tuple(_pending_move_from_row(row) for row in rows)

    def delete_pending_moves(self, game_id: str, turn_index: int) -> None:
        self._database.execute(
            "DELETE FROM pending_moves WHERE game_id = ? AND turn_index = ?",
            (game_id, turn_index),
        )

    def save_turn(self, turn: TurnRecord) -> None:
        self._database.execute(
            """
            INSERT INTO turns (
              id, game_id, turn_index, pre_board_key, post_board_key,
              black_move, white_move, status, resolution_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                turn.id,
                turn.game_id,
                turn.turn_index,
                turn.pre_board_key,
                turn.post_board_key,
                turn.black_move,
                turn.white_move,
                turn.status,
                _resolution_json(turn.resolution),
            ),
        )

    def save_agent_call(self, call: AgentCallRecord) -> None:
        self._database.execute(
            """
            INSERT INTO agent_calls (
              id, game_id, turn_index, seat_session_id, color, provider, model,
              prompt_board_key, raw_response, parsed_move, valid, error, attempt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call.id,
                call.game_id,
                call.turn_index,
                call.seat_session_id,
                call.color,
                call.provider,
                call.model,
                call.prompt_board_key,
                call.raw_response,
                call.parsed_move,
                int(call.valid),
                call.error,
                call.attempt,
            ),
        )

    def save_transcript(self, transcript: TranscriptRecord) -> None:
        self._database.execute(
            """
            INSERT INTO seat_transcripts (
              id, game_id, turn_index, seat_session_id, view, text
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                transcript.id,
                transcript.game_id,
                transcript.turn_index,
                transcript.seat_session_id,
                transcript.view,
                transcript.text,
            ),
        )

    def save_event(self, event: GameEvent) -> None:
        self._database.execute(
            """
            INSERT INTO events (id, game_id, event_type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (event.id, event.game_id, event.event_type, json.dumps(event.payload)),
        )

    def list_turns(self, game_id: str) -> tuple[TurnRecord, ...]:
        rows = self._database.fetch_all(
            "SELECT * FROM turns WHERE game_id = ? ORDER BY turn_index",
            (game_id,),
        )
        return tuple(_turn_from_row(row) for row in rows)

    def get_turn(self, game_id: str, turn_index: int) -> TurnRecord:
        row = self._database.fetch_one(
            "SELECT * FROM turns WHERE game_id = ? AND turn_index = ?",
            (game_id, turn_index),
        )
        return _turn_from_row(row)

    def list_transcripts(self, game_id: str, view: TranscriptView) -> tuple[TranscriptRecord, ...]:
        if view == "debug":
            rows = self._database.fetch_all(
                "SELECT * FROM seat_transcripts WHERE game_id = ? ORDER BY turn_index, id",
                (game_id,),
            )
        else:
            rows = self._database.fetch_all(
                """
                SELECT * FROM seat_transcripts
                WHERE game_id = ? AND view = ?
                ORDER BY turn_index, id
                """,
                (game_id, view),
            )
        return tuple(_transcript_from_row(row) for row in rows)

    def list_events(self, game_id: str) -> tuple[GameEvent, ...]:
        rows = self._database.fetch_all(
            "SELECT * FROM events WHERE game_id = ? ORDER BY rowid",
            (game_id,),
        )
        return tuple(_event_from_row(row) for row in rows)

    def list_agent_calls(self, game_id: str) -> tuple[AgentCallRecord, ...]:
        rows = self._database.fetch_all(
            "SELECT * FROM agent_calls WHERE game_id = ? ORDER BY turn_index, id",
            (game_id,),
        )
        return tuple(_agent_call_from_row(row) for row in rows)

    def _save_seat(self, seat: SeatSession) -> None:
        self._database.execute(
            """
            INSERT INTO seat_sessions (
              id, game_id, color, provider, model, credential_ref,
              local_history_json, provider_session_id, previous_response_id,
              script_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              local_history_json=excluded.local_history_json,
              provider_session_id=excluded.provider_session_id,
              previous_response_id=excluded.previous_response_id,
              script_json=excluded.script_json
            """,
            (
                seat.id,
                seat.game_id,
                seat.color,
                seat.provider,
                seat.model,
                seat.credential_ref,
                json.dumps(seat.local_history),
                seat.provider_session_id,
                seat.previous_response_id,
                json.dumps(seat.script),
            ),
        )


def _coordinate_json(coordinates: frozenset[Coordinate]) -> str:
    return json.dumps([coordinate.to_label() for coordinate in sorted(coordinates)])


def _coordinates_from_json(value: str) -> frozenset[Coordinate]:
    labels = cast(list[str], json.loads(value))
    return frozenset(Coordinate.parse(label, size=26) for label in labels)


def _seat_from_row(row: sqlite3.Row) -> SeatSession:
    return SeatSession(
        id=cast(str, row["id"]),
        game_id=cast(str, row["game_id"]),
        color=cast(SeatColor, row["color"]),
        provider=cast(str, row["provider"]),
        model=cast(str, row["model"]),
        credential_ref=cast(str, row["credential_ref"]),
        local_history=tuple(cast(list[str], json.loads(cast(str, row["local_history_json"])))),
        provider_session_id=cast(str | None, row["provider_session_id"]),
        previous_response_id=cast(str | None, row["previous_response_id"]),
        script=tuple(cast(list[str], json.loads(cast(str, row["script_json"])))),
    )


def _turn_from_row(row: sqlite3.Row) -> TurnRecord:
    resolution = _resolution_from_json(
        cast(str, row["resolution_json"]),
        cast(str, row["pre_board_key"]),
        cast(str, row["post_board_key"]),
        cast(str, row["black_move"]),
        cast(str, row["white_move"]),
        cast(int, row["turn_index"]),
    )
    return TurnRecord(
        id=cast(str, row["id"]),
        game_id=cast(str, row["game_id"]),
        turn_index=cast(int, row["turn_index"]),
        pre_board_key=cast(str, row["pre_board_key"]),
        post_board_key=cast(str, row["post_board_key"]),
        black_move=cast(str, row["black_move"]),
        white_move=cast(str, row["white_move"]),
        resolution=resolution,
        status=cast(Literal["resolved", "invalid", "finished"], row["status"]),
    )


def _pending_move_from_row(row: sqlite3.Row) -> PendingMove:
    return PendingMove(
        id=cast(str, row["id"]),
        game_id=cast(str, row["game_id"]),
        turn_index=cast(int, row["turn_index"]),
        seat_session_id=cast(str, row["seat_session_id"]),
        color=cast(SeatColor, row["color"]),
        move=cast(str, row["move"]),
        source=cast(MoveSource, row["source"]),
        raw_response=cast(str, row["raw_response"]),
        valid=bool(row["valid"]),
        error=cast(str | None, row["error"]),
        attempt=cast(int, row["attempt"]),
    )


def _transcript_from_row(row: sqlite3.Row) -> TranscriptRecord:
    return TranscriptRecord(
        id=cast(str, row["id"]),
        game_id=cast(str, row["game_id"]),
        turn_index=cast(int, row["turn_index"]),
        seat_session_id=cast(str | None, row["seat_session_id"]),
        view=cast(TranscriptView, row["view"]),
        text=cast(str, row["text"]),
    )


def _event_from_row(row: sqlite3.Row) -> GameEvent:
    return GameEvent(
        id=cast(str, row["id"]),
        game_id=cast(str, row["game_id"]),
        event_type=cast(str, row["event_type"]),
        payload=cast(dict[str, str], json.loads(cast(str, row["payload_json"]))),
    )


def _agent_call_from_row(row: sqlite3.Row) -> AgentCallRecord:
    return AgentCallRecord(
        id=cast(str, row["id"]),
        game_id=cast(str, row["game_id"]),
        turn_index=cast(int, row["turn_index"]),
        seat_session_id=cast(str, row["seat_session_id"]),
        color=cast(SeatColor, row["color"]),
        provider=cast(str, row["provider"]),
        model=cast(str, row["model"]),
        prompt_board_key=cast(str, row["prompt_board_key"]),
        raw_response=cast(str, row["raw_response"]),
        parsed_move=cast(str, row["parsed_move"]),
        valid=bool(cast(int, row["valid"])),
        error=cast(str | None, row["error"]),
        attempt=cast(int, row["attempt"]),
    )


def _resolution_json(resolution: TurnResolution) -> str:
    return json.dumps(
        {
            "post_forbidden": {
                "black": [
                    point.to_label() for point in sorted(resolution.post_state.forbidden.black)
                ],
                "white": [
                    point.to_label() for point in sorted(resolution.post_state.forbidden.white)
                ],
            },
            "history": [
                {
                    "pre_board_key": round_.pre_board_key,
                    "black_move": round_.black_move,
                    "white_move": round_.white_move,
                }
                for round_ in resolution.post_state.history
            ],
            "placement_events": [
                {
                    "event_type": event.event_type,
                    "coordinate": event.coordinate.to_label(),
                    "color": event.color,
                }
                for event in resolution.placement_events
            ],
            "captures": [
                {
                    "captured_color": capture.captured_color,
                    "by_color": capture.by_color,
                    "coordinates": [coordinate.to_label() for coordinate in capture.coordinates],
                }
                for capture in resolution.captures
            ],
            "forbidden_updates": [
                {
                    "color": update.color,
                    "coordinates": [coordinate.to_label() for coordinate in update.coordinates],
                }
                for update in resolution.forbidden_updates
            ],
            "double_pass_count": resolution.double_pass_count,
            "game_finished": resolution.game_finished,
            "score_estimate": resolution.score_estimate,
        }
    )


def _resolution_from_json(
    value: str,
    pre_board_key: str,
    post_board_key: str,
    black_move: str,
    white_move: str,
    turn_index: int,
) -> TurnResolution:
    payload = cast(dict[str, object], json.loads(value))
    post_board_size = Board.from_key(post_board_key).size
    placement_events = tuple(
        PlacementEvent(
            event_type=cast(Literal["placement", "collision"], event["event_type"]),
            coordinate=Coordinate.parse(cast(str, event["coordinate"]), post_board_size),
            color=cast(SeatColor | None, event["color"]),
        )
        for event in cast(list[dict[str, object]], payload["placement_events"])
    )
    captures = tuple(
        CaptureEvent(
            captured_color=cast(CapturedColor, capture["captured_color"]),
            by_color=cast(CaptureByColor, capture["by_color"]),
            coordinates=tuple(
                Coordinate.parse(label, Board.from_key(post_board_key).size)
                for label in cast(list[str], capture["coordinates"])
            ),
        )
        for capture in cast(list[dict[str, object]], payload["captures"])
    )
    forbidden_updates = tuple(
        ForbiddenUpdate(
            color=cast(SeatColor, update["color"]),
            coordinates=tuple(
                Coordinate.parse(label, Board.from_key(post_board_key).size)
                for label in cast(list[str], update["coordinates"])
            ),
        )
        for update in cast(list[dict[str, object]], payload["forbidden_updates"])
    )
    forbidden = ForbiddenState(
        black=frozenset(
            coordinate
            for update in forbidden_updates
            if update.color == "black"
            for coordinate in update.coordinates
        ),
        white=frozenset(
            coordinate
            for update in forbidden_updates
            if update.color == "white"
            for coordinate in update.coordinates
        ),
    )
    if "post_forbidden" in payload:
        full = cast(dict[str, list[str]], payload["post_forbidden"])
        forbidden = ForbiddenState(
            black=frozenset(Coordinate.parse(label, post_board_size) for label in full["black"]),
            white=frozenset(Coordinate.parse(label, post_board_size) for label in full["white"]),
        )
    history = tuple(
        RoundHistory(round_["pre_board_key"], round_["black_move"], round_["white_move"])
        for round_ in cast(list[dict[str, str]], payload.get("history", []))
    )
    post_board = Board.from_key(post_board_key)
    double_pass_count = cast(int, payload["double_pass_count"])
    return TurnResolution(
        pre_board_key=pre_board_key,
        post_board_key=post_board_key,
        black_move=black_move,
        white_move=white_move,
        placement_events=placement_events,
        captures=captures,
        forbidden_updates=forbidden_updates,
        post_state=GameState(
            board=post_board,
            forbidden=forbidden,
            double_pass_count=double_pass_count,
            turn_index=turn_index + 1,
            history=history,
        ),
        double_pass_count=double_pass_count,
        game_finished=cast(bool, payload["game_finished"]),
        score_estimate=cast(dict[str, float], payload["score_estimate"]),
    )
