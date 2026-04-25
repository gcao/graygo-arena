"""API route registration."""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from graygo_arena.api.schemas import (
    CreateGameRequest,
    EventResponse,
    ExportBundleResponse,
    GameResponse,
    GuardrailCheckResponse,
    ProviderInfoResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    StepResponse,
    TranscriptResponse,
    TurnResponse,
    event_response,
    export_bundle_response,
    game_response,
    guardrail_check_response,
    provider_info_response,
    provider_test_response,
    step_response,
    transcript_response,
    turn_response,
)
from graygo_arena.application.export import build_export_bundle
from graygo_arena.application.guardrails import run_guardrails
from graygo_arena.application.models import GameRecord, GameRepository, TranscriptView
from graygo_arena.application.orchestrator import GameOrchestrator
from graygo_arena.core.config import load_settings
from graygo_arena.events.bus import sse_payloads
from graygo_arena.persistence.database import SQLiteDatabase
from graygo_arena.persistence.repositories import SQLiteRepository
from graygo_arena.providers.registry import ProviderCatalog


@dataclass(frozen=True)
class AppServices:
    repository: GameRepository
    providers: ProviderCatalog
    orchestrator: GameOrchestrator


def create_services(
    *,
    repository: GameRepository | None = None,
    database_path: Path | str | None = None,
) -> AppServices:
    if repository is None:
        settings = load_settings()
        repository = SQLiteRepository(SQLiteDatabase(database_path or settings.database_path))
    providers = ProviderCatalog()
    orchestrator = GameOrchestrator(repository=repository, providers=providers)
    return AppServices(repository=repository, providers=providers, orchestrator=orchestrator)


def build_router(services: AppServices) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/providers")
    def list_providers() -> tuple[ProviderInfoResponse, ...]:
        return tuple(provider_info_response(info) for info in services.providers.list_providers())

    @router.get("/settings/providers")
    def provider_settings() -> tuple[ProviderInfoResponse, ...]:
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
    def stream_events(game_id: str, live: bool = Query(default=False)) -> EventSourceResponse:
        _get_game_or_404(services, game_id)
        if live:
            return EventSourceResponse(_event_stream(services, game_id))
        return EventSourceResponse(_event_snapshot(services, game_id))

    @router.get("/games/{game_id}/events/list")
    def list_events(game_id: str) -> tuple[EventResponse, ...]:
        _get_game_or_404(services, game_id)
        return tuple(event_response(event) for event in services.repository.list_events(game_id))

    @router.get("/games/{game_id}/export")
    def export_game(game_id: str) -> ExportBundleResponse:
        _get_game_or_404(services, game_id)
        return export_bundle_response(build_export_bundle(services.repository, game_id))

    @router.get("/games/{game_id}/guardrails")
    def guardrails(game_id: str) -> tuple[GuardrailCheckResponse, ...]:
        _get_game_or_404(services, game_id)
        return tuple(
            guardrail_check_response(check)
            for check in run_guardrails(services.repository, services.providers, game_id)
        )

    return router


async def _event_snapshot(services: AppServices, game_id: str) -> AsyncIterator[dict[str, object]]:
    for payload in sse_payloads(services.repository.list_events(game_id)):
        yield payload


async def _event_stream(services: AppServices, game_id: str) -> AsyncIterator[dict[str, object]]:
    sent_ids: set[str] = set()
    while True:
        events = services.repository.list_events(game_id)
        for event in events:
            if event.id in sent_ids:
                continue
            sent_ids.add(event.id)
            yield sse_payloads((event,))[0]
        await asyncio.sleep(0.5)


def _get_game_or_404(services: AppServices, game_id: str) -> GameRecord:
    try:
        return services.repository.get_game(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"game not found: {game_id}") from exc
