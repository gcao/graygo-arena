"""API route registration."""

# pyright: reportUnusedFunction=false

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import cast

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from graygo_arena.api.schemas import (
    CreateGameRequest,
    EventResponse,
    GameResponse,
    ProviderInfoResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    StepResponse,
    TranscriptResponse,
    TurnResponse,
    event_response,
    game_response,
    provider_info_response,
    provider_test_response,
    step_response,
    transcript_response,
    turn_response,
)
from graygo_arena.application.models import GameRecord, TranscriptView
from graygo_arena.application.orchestrator import GameOrchestrator
from graygo_arena.events.bus import sse_payloads
from graygo_arena.persistence.repositories import InMemoryRepository
from graygo_arena.providers.registry import ProviderCatalog


@dataclass(frozen=True)
class AppServices:
    repository: InMemoryRepository
    providers: ProviderCatalog
    orchestrator: GameOrchestrator


def create_services() -> AppServices:
    repository = InMemoryRepository()
    providers = ProviderCatalog()
    orchestrator = GameOrchestrator(repository=repository, providers=providers)
    return AppServices(repository=repository, providers=providers, orchestrator=orchestrator)


def build_router(services: AppServices) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/providers")
    def list_providers() -> tuple[ProviderInfoResponse, ...]:
        return tuple(provider_info_response(info) for info in services.providers.list_providers())

    @router.post("/providers/test")
    def test_provider(request: ProviderTestRequest) -> ProviderTestResponse:
        try:
            result = services.providers.test_provider(request.provider, request.model)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return provider_test_response(result)

    @router.post("/games")
    def create_game(request: CreateGameRequest) -> GameResponse:
        try:
            game = services.orchestrator.create_game(request.to_command())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return game_response(game)

    @router.get("/games/{game_id}")
    def get_game(game_id: str) -> GameResponse:
        return game_response(_get_game_or_404(services, game_id))

    @router.post("/games/{game_id}/start")
    def start_game(game_id: str) -> GameResponse:
        return game_response(services.orchestrator.start_game(game_id))

    @router.post("/games/{game_id}/pause")
    def pause_game(game_id: str) -> GameResponse:
        return game_response(services.orchestrator.pause_game(game_id))

    @router.post("/games/{game_id}/resume")
    def resume_game(game_id: str) -> GameResponse:
        return game_response(services.orchestrator.resume_game(game_id))

    @router.post("/games/{game_id}/stop")
    def stop_game(game_id: str) -> GameResponse:
        return game_response(services.orchestrator.stop_game(game_id))

    @router.post("/games/{game_id}/step")
    def step_game(game_id: str) -> StepResponse:
        try:
            return step_response(services.orchestrator.step_game(game_id))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/games/{game_id}/autorun")
    def autorun_game(game_id: str) -> tuple[StepResponse, ...]:
        return tuple(
            step_response(result) for result in services.orchestrator.autorun_game(game_id)
        )

    @router.get("/games/{game_id}/turns")
    def list_turns(game_id: str) -> tuple[TurnResponse, ...]:
        _get_game_or_404(services, game_id)
        return tuple(turn_response(turn) for turn in services.repository.list_turns(game_id))

    @router.get("/games/{game_id}/turns/{turn_index}")
    def get_turn(game_id: str, turn_index: int) -> TurnResponse:
        try:
            return turn_response(services.repository.get_turn(game_id, turn_index))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/games/{game_id}/transcript")
    def get_transcript(
        game_id: str,
        view: str = Query(default="public"),
    ) -> TranscriptResponse:
        if view not in {"public", "black_private", "white_private", "debug"}:
            raise HTTPException(status_code=400, detail="invalid transcript view")
        typed_view = cast(TranscriptView, view)
        entries = services.repository.list_transcripts(game_id, typed_view)
        return transcript_response(typed_view, entries)

    @router.get("/games/{game_id}/events", response_model=None)
    def stream_events(game_id: str) -> EventSourceResponse:
        _get_game_or_404(services, game_id)
        return EventSourceResponse(_event_stream(services, game_id))

    @router.get("/games/{game_id}/events/list")
    def list_events(game_id: str) -> tuple[EventResponse, ...]:
        _get_game_or_404(services, game_id)
        return tuple(event_response(event) for event in services.repository.list_events(game_id))

    return router


async def _event_stream(services: AppServices, game_id: str) -> AsyncIterator[dict[str, object]]:
    for payload in sse_payloads(services.repository.list_events(game_id)):
        yield payload


def _get_game_or_404(services: AppServices, game_id: str) -> GameRecord:
    try:
        return services.repository.get_game(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"game not found: {game_id}") from exc
