from fastapi.testclient import TestClient

from graygo_arena.main import create_app


def test_provider_list_and_test_endpoint() -> None:
    client = TestClient(create_app())

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


def test_create_start_step_get_turns_and_transcripts() -> None:
    client = TestClient(create_app())
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


def test_event_endpoints_include_sse_shell_headers() -> None:
    client = TestClient(create_app())
    game_id = client.post("/api/games", json={}).json()["id"]

    events = client.get(f"/api/games/{game_id}/events/list")
    stream = client.get(f"/api/games/{game_id}/events")

    assert events.status_code == 200
    assert events.json()[0]["event_type"] == "game.created"
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
