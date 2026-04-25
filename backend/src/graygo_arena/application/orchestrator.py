"""Backend-owned game orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from threading import RLock
from uuid import uuid4

from graygo_arena.application.models import (
    AgentCallRecord,
    CreateGameCommand,
    GameEvent,
    GameRecord,
    GameRepository,
    GameStatus,
    ProviderMoveRequest,
    ProviderMoveResponse,
    ProviderRegistry,
    SeatConfig,
    SeatSession,
    StepResult,
    TranscriptRecord,
    TurnRecord,
)
from graygo_arena.application.prompt_builder import build_move_request
from graygo_arena.engine import Board, ForbiddenState, GameState, PassMove, legal_moves, parse_move
from graygo_arena.engine.moves import MoveLike, SeatColor
from graygo_arena.engine.resolution import resolve_turn

type IdFactory = Callable[[str], str]


class GameOrchestrator:
    def __init__(
        self,
        *,
        repository: GameRepository,
        providers: ProviderRegistry,
        id_factory: IdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._providers = providers
        self._id_factory = id_factory or _default_id
        self._locks: dict[str, RLock] = {}

    def create_game(self, command: CreateGameCommand) -> GameRecord:
        board = Board.empty(command.board_size)
        game_id = self._id_factory("game")
        black = _seat_from_config(self._id_factory("seat"), game_id, "black", command.black)
        white = _seat_from_config(self._id_factory("seat"), game_id, "white", command.white)
        game = GameRecord(
            id=game_id,
            board_size=command.board_size,
            ruleset=command.ruleset,
            status="running" if command.auto_run else "created",
            current_turn=0,
            board=board,
            forbidden=ForbiddenState(),
            double_pass_count=0,
            black_seat_id=black.id,
            white_seat_id=white.id,
            max_turns=command.max_turns,
            invalid_move_policy=command.invalid_move_policy,
            show_private_summaries_in_ui=command.show_private_summaries_in_ui,
        )
        self._repository.create_game(game, (black, white))
        self._emit(game.id, "game.created", {"status": game.status})
        return game

    def start_game(self, game_id: str) -> GameRecord:
        return self._set_status(game_id, "running")

    def pause_game(self, game_id: str) -> GameRecord:
        return self._set_status(game_id, "paused")

    def resume_game(self, game_id: str) -> GameRecord:
        return self._set_status(game_id, "running")

    def stop_game(self, game_id: str) -> GameRecord:
        return self._set_status(game_id, "stopped")

    def step_game(self, game_id: str) -> StepResult:
        with self._lock_for(game_id):
            game = self._repository.get_game(game_id)
            if game.status not in {"created", "running"}:
                msg = f"cannot step game in status {game.status}"
                raise ValueError(msg)

            black, white = self._repository.get_seats(game_id)
            pre_board = game.board
            public_history = self._repository.list_public_history(game_id)
            black_request = build_move_request(
                game_id=game_id,
                seat=black,
                board=pre_board,
                forbidden=game.forbidden,
                public_history=public_history,
                private_history=self._repository.list_private_history(black.id),
                turn_index=game.current_turn,
            )
            white_request = build_move_request(
                game_id=game_id,
                seat=white,
                board=pre_board,
                forbidden=game.forbidden,
                public_history=public_history,
                private_history=self._repository.list_private_history(white.id),
                turn_index=game.current_turn,
            )
            black_move, black_call = self._request_valid_move(game, black, black_request)
            white_move, white_call = self._request_valid_move(game, white, white_request)
            resolution = resolve_turn(
                GameState(
                    board=game.board,
                    forbidden=game.forbidden,
                    double_pass_count=game.double_pass_count,
                    turn_index=game.current_turn,
                    ruleset=game.ruleset,
                ),
                black_move,
                white_move,
            )
            status: GameStatus = (
                "finished"
                if resolution.game_finished or game.current_turn + 1 >= game.max_turns
                else "running"
            )
            updated_game = replace(
                game,
                status=status,
                current_turn=game.current_turn + 1,
                board=resolution.post_state.board,
                forbidden=resolution.post_state.forbidden,
                double_pass_count=resolution.double_pass_count,
            )
            turn = TurnRecord(
                id=self._id_factory("turn"),
                game_id=game.id,
                turn_index=game.current_turn,
                pre_board_key=resolution.pre_board_key,
                post_board_key=resolution.post_board_key,
                black_move=resolution.black_move,
                white_move=resolution.white_move,
                resolution=resolution,
                status="finished" if status == "finished" else "resolved",
            )
            self._repository.save_agent_call(black_call)
            self._repository.save_agent_call(white_call)
            self._repository.save_turn(turn)
            self._save_transcripts(
                game.id,
                turn.turn_index,
                black,
                white,
                black_call,
                white_call,
                turn,
            )
            self._repository.save_game(updated_game)
            event = self._emit(
                game.id,
                "turn.resolved",
                {
                    "turn_index": str(turn.turn_index),
                    "black_move": turn.black_move,
                    "white_move": turn.white_move,
                    "post_board_key": turn.post_board_key,
                },
            )
            if status == "finished":
                finished_event = self._emit(
                    game.id,
                    "game.finished",
                    {"turn_index": str(turn.turn_index)},
                )
                events = (event, finished_event)
            else:
                events = (event,)
            return StepResult(
                game=updated_game,
                turn=turn,
                black_call=black_call,
                white_call=white_call,
                events=events,
            )

    def autorun_game(self, game_id: str) -> tuple[StepResult, ...]:
        results: list[StepResult] = []
        game = self.start_game(game_id)
        while game.status == "running" and game.current_turn < game.max_turns:
            result = self.step_game(game_id)
            results.append(result)
            game = result.game
        return tuple(results)

    def _request_valid_move(
        self,
        game: GameRecord,
        seat: SeatSession,
        request: ProviderMoveRequest,
    ) -> tuple[MoveLike, AgentCallRecord]:
        adapter = self._providers.adapter_for(seat.provider)
        last_response: ProviderMoveResponse | None = None
        last_error: str | None = None
        for attempt in (1, 2):
            response = adapter.request_move(request, seat)
            last_response = response
            try:
                move = _validate_provider_response(game, seat.color, response)
                call = self._agent_call(
                    game,
                    seat,
                    request.board_key,
                    response,
                    True,
                    None,
                    attempt,
                )
                return move, call
            except ValueError as exc:
                last_error = str(exc)

        if game.invalid_move_policy == "error":
            raise ValueError(last_error or "provider returned invalid move")
        if game.invalid_move_policy == "forfeit":
            raise ValueError(last_error or "provider forfeited after invalid move")

        fallback_response = last_response or ProviderMoveResponse(
            board_key=request.board_key,
            move="PASS",
            raw_response="forced PASS after invalid output",
        )
        forced_response = replace(fallback_response, move="PASS")
        return PassMove(), self._agent_call(
            game,
            seat,
            request.board_key,
            forced_response,
            False,
            last_error,
            2,
        )

    def _agent_call(
        self,
        game: GameRecord,
        seat: SeatSession,
        prompt_board_key: str,
        response: ProviderMoveResponse,
        valid: bool,
        error: str | None,
        attempt: int,
    ) -> AgentCallRecord:
        return AgentCallRecord(
            id=self._id_factory("call"),
            game_id=game.id,
            turn_index=game.current_turn,
            seat_session_id=seat.id,
            color=seat.color,
            provider=seat.provider,
            model=seat.model,
            prompt_board_key=prompt_board_key,
            raw_response=response.raw_response,
            parsed_move=response.move,
            valid=valid,
            error=error,
            attempt=attempt,
        )

    def _save_transcripts(
        self,
        game_id: str,
        turn_index: int,
        black: SeatSession,
        white: SeatSession,
        black_call: AgentCallRecord,
        white_call: AgentCallRecord,
        turn: TurnRecord,
    ) -> None:
        public_text = (
            f"Turn {turn_index}: B={turn.black_move} W={turn.white_move} "
            f"{turn.pre_board_key}->{turn.post_board_key}"
        )
        self._repository.save_transcript(
            TranscriptRecord(
                id=self._id_factory("transcript"),
                game_id=game_id,
                turn_index=turn_index,
                seat_session_id=None,
                view="public",
                text=public_text,
            )
        )
        self._repository.save_transcript(
            TranscriptRecord(
                id=self._id_factory("transcript"),
                game_id=game_id,
                turn_index=turn_index,
                seat_session_id=black.id,
                view="black_private",
                text=black_call.raw_response,
            )
        )
        self._repository.save_transcript(
            TranscriptRecord(
                id=self._id_factory("transcript"),
                game_id=game_id,
                turn_index=turn_index,
                seat_session_id=white.id,
                view="white_private",
                text=white_call.raw_response,
            )
        )

    def _set_status(self, game_id: str, status: GameStatus) -> GameRecord:
        game = self._repository.get_game(game_id)
        updated = replace(game, status=status)
        self._repository.save_game(updated)
        self._emit(game_id, "game.status_changed", {"status": status})
        return updated

    def _emit(self, game_id: str, event_type: str, payload: dict[str, str]) -> GameEvent:
        event = GameEvent(
            id=self._id_factory("event"),
            game_id=game_id,
            event_type=event_type,
            payload=payload,
        )
        self._repository.save_event(event)
        return event

    def _lock_for(self, game_id: str) -> RLock:
        if game_id not in self._locks:
            self._locks[game_id] = RLock()
        return self._locks[game_id]


def _seat_from_config(
    seat_id: str,
    game_id: str,
    color: SeatColor,
    config: SeatConfig,
) -> SeatSession:
    return SeatSession(
        id=seat_id,
        game_id=game_id,
        color=color,
        provider=config.provider,
        model=config.model,
        credential_ref=config.credential_ref,
        script=config.script,
    )


def _validate_provider_response(
    game: GameRecord,
    color: SeatColor,
    response: ProviderMoveResponse,
) -> MoveLike:
    if response.board_key != game.board.to_key():
        msg = "provider response BoardKey does not match pre-turn BoardKey"
        raise ValueError(msg)
    move = parse_move(response.move, game.board_size)
    if move not in legal_moves(game.board, color, game.forbidden):
        msg = f"provider returned illegal move: {response.move}"
        raise ValueError(msg)
    return move


def _default_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
