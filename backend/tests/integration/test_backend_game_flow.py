from pathlib import Path

from fastapi.testclient import TestClient

from graygo_arena.api.routes import create_services
from graygo_arena.main import create_app


def test_api_game_flow_persists_to_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "graygo.db"
    client = TestClient(create_app(create_services(database_path=database_path)))
    create_response = client.post(
        "/api/games",
        json={
            "black": {"provider": "scripted_center", "model": "default", "credential_ref": "fake"},
            "white": {"provider": "scripted_pass", "model": "default", "credential_ref": "fake"},
            "max_turns": 3,
        },
    )
    game_id = create_response.json()["id"]

    assert client.post(f"/api/games/{game_id}/start").json()["status"] == "running"
    step = client.post(f"/api/games/{game_id}/step")
    current = client.get(f"/api/games/{game_id}")
    turns = client.get(f"/api/games/{game_id}/turns")
    debug = client.get(f"/api/games/{game_id}/transcript?view=debug")

    assert step.status_code == 200
    assert current.json()["current_turn"] == 1
    assert len(turns.json()) == 1
    assert len(debug.json()["entries"]) == 3
    assert database_path.exists()
