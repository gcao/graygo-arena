from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from graygo_arena.api.routes import AppServices, create_services
from graygo_arena.application.orchestrator import GameOrchestrator
from graygo_arena.core.config import Settings
from graygo_arena.main import create_app
from graygo_arena.persistence.database import SQLiteDatabase
from graygo_arena.persistence.repositories import SQLiteRepository
from graygo_arena.providers.registry import ProviderCatalog


def client_for(path: Path) -> TestClient:
    return TestClient(create_app(create_services(database_path=path)))


def test_provider_list_and_test_endpoint(tmp_path: Path) -> None:
    client = client_for(tmp_path / "api.db")

    providers = client.get("/api/providers")
    provider_test = client.post(
        "/api/providers/test",
        json={"provider": "scripted_center", "model": "default"},
    )

    assert providers.status_code == 200
    assert providers.json()[0]["configured"] is True
    assert "token" not in str(providers.json()).lower()
    assert provider_test.status_code == 200
    assert provider_test.json()["ok"] is True


def test_create_start_step_get_turns_and_transcripts(tmp_path: Path) -> None:
    client = client_for(tmp_path / "api.db")
    create_response = client.post(
        "/api/games",
        json={
            "board_size": 7,
            "black": {"provider": "scripted_center", "model": "default", "credential_ref": "fake"},
            "white": {"provider": "scripted_pass", "model": "default", "credential_ref": "fake"},
            "max_turns": 5,
        },
    )
    game_id = create_response.json()["id"]

    start_response = client.post(f"/api/games/{game_id}/start")
    step_response = client.post(f"/api/games/{game_id}/step")
    game_response = client.get(f"/api/games/{game_id}")
    turns_response = client.get(f"/api/games/{game_id}/turns")
    turn_response = client.get(f"/api/games/{game_id}/turns/0")
    transcript_response = client.get(f"/api/games/{game_id}/transcript?view=public")
    private_response = client.get(f"/api/games/{game_id}/transcript?view=black_private")

    assert create_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert step_response.status_code == 200
    assert step_response.json()["turn"]["black_move"] == "d4"
    assert game_response.json()["current_turn"] == 1
    assert len(turns_response.json()) == 1
    assert turn_response.json()["post_board_key"] == step_response.json()["turn"]["post_board_key"]
    assert transcript_response.json()["entries"]
    assert private_response.json()["entries"]


def test_event_endpoints_include_sse_shell_headers(tmp_path: Path) -> None:
    client = client_for(tmp_path / "api.db")
    game_id = client.post("/api/games", json={}).json()["id"]

    events = client.get(f"/api/games/{game_id}/events/list")
    stream = client.get(f"/api/games/{game_id}/events")

    assert events.status_code == 200
    assert events.json()[0]["event_type"] == "game.created"
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")


def test_step_reports_provider_auth_failure_without_500(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid credentials"}})

    repository = SQLiteRepository(SQLiteDatabase(tmp_path / "api.db"))
    providers = ProviderCatalog(
        settings=Settings(
            openai_auth_token="codex-test-token",
            openai_auth_source="codex_token",
            openai_model="gpt-5.5",
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client = TestClient(
        create_app(
            AppServices(
                repository=repository,
                providers=providers,
                orchestrator=GameOrchestrator(repository=repository, providers=providers),
            )
        )
    )
    game_id = client.post(
        "/api/games",
        json={
            "black": {"provider": "openai_default", "model": "gpt-5.5", "credential_ref": "env"},
            "white": {"provider": "scripted_pass", "model": "default", "credential_ref": "fake"},
        },
    ).json()["id"]

    step_response = client.post(f"/api/games/{game_id}/step")
    provider_test = client.post(
        "/api/providers/test",
        json={"provider": "openai_default", "model": "gpt-5.5"},
    )

    assert step_response.status_code == 502
    assert "OpenAI authentication failed (401)" in step_response.json()["detail"]
    assert "codex-test-token" not in step_response.text
    assert provider_test.status_code == 200
    assert provider_test.json()["ok"] is False
