from pathlib import Path

from fastapi.testclient import TestClient

from graygo_arena.api.routes import create_services
from graygo_arena.main import create_app


def client_for(path: Path) -> TestClient:
    return TestClient(create_app(create_services(database_path=path)))


def test_export_bundle_contains_replay_data_without_secret_values(tmp_path: Path) -> None:
    client = client_for(tmp_path / "graygo.db")
    game_id = client.post(
        "/api/games",
        json={
            "black": {"provider": "scripted_center", "model": "default", "credential_ref": "fake"},
            "white": {"provider": "scripted_pass", "model": "default", "credential_ref": "fake"},
        },
    ).json()["id"]
    client.post(f"/api/games/{game_id}/step")

    bundle = client.get(f"/api/games/{game_id}/export").json()
    serialized = str(bundle)

    assert bundle["version"] == "graygo-arena-export-v1"
    assert bundle["game"]["id"] == game_id
    assert len(bundle["turns"]) == 1
    assert len(bundle["agent_calls"]) == 2
    assert len(bundle["transcripts"]) == 3
    assert "sk-test" not in serialized
    assert "sk-ant-test" not in serialized


def test_guardrails_and_settings_expose_safe_status_only(tmp_path: Path) -> None:
    client = client_for(tmp_path / "graygo.db")
    game_id = client.post("/api/games", json={}).json()["id"]
    client.post(f"/api/games/{game_id}/step")

    guardrails = client.get(f"/api/games/{game_id}/guardrails").json()
    settings = client.get("/api/settings/providers").json()

    assert {check["name"] for check in guardrails} == {
        "secret_values_absent",
        "credential_refs_only",
        "transcript_views_separated",
        "provider_settings_safe",
    }
    assert all(check["ok"] is True for check in guardrails)
    assert all("models" in provider for provider in settings)
    assert "sk-" not in str(settings)
