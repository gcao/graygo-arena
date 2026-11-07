from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from graygo_arena.api.routes import create_services
from graygo_arena.engine import Board
from graygo_arena.main import create_app


def client_for(path: Path) -> TestClient:
    return TestClient(create_app(create_services(database_path=path)))


def test_capture_point_can_join_gray_groups_after_api_and_database_reload(tmp_path: Path) -> None:
    path = tmp_path / "bridge.db"
    client = client_for(path)
    game = client.post(
        "/api/games",
        json={"board_size": 9, "black": {"provider": "human"}, "white": {"provider": "human"}},
    ).json()
    prefix = f"/api/games/{game['id']}"
    client.post(prefix + "/start")
    for black, white in [
        ("i8", "PASS"),
        ("a8", "a8"),
        ("PASS", "i7"),
        ("PASS", "i9"),
        ("h8", "h8"),
    ]:
        assert client.post(prefix + "/human-moves/black", json={"move": black}).status_code == 200
        assert client.post(prefix + "/human-moves/white", json={"move": white}).status_code == 200
    reloaded = client_for(path)
    assert reloaded.post(prefix + "/human-moves/black", json={"move": "i8"}).status_code == 200
    joined = reloaded.post(prefix + "/human-moves/white", json={"move": "i8"})
    assert joined.status_code == 200
    board = joined.json()["game"]["board"]
    assert [board[row][7] for row in (0, 7, 8)] == ["G", "G", "G"]
    assert joined.json()["turn"]["captures"] == []
    assert client_for(path).get(prefix).json()["board"] == board


def test_short_repetition_is_forbidden_after_reload_without_reverting_capture(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ko.db"
    services = create_services(database_path=path)
    client = TestClient(create_app(services))
    game = client.post(
        "/api/games",
        json={"board_size": 5, "black": {"provider": "human"}, "white": {"provider": "human"}},
    ).json()
    prefix = f"/api/games/{game['id']}"
    key = "++W++/+WBW+/+B+B+/++B++/+++++"
    services.repository.save_game(
        replace(services.repository.get_game(game["id"]), board=Board.from_key(key))
    )
    client.post(prefix + "/start")
    assert client.post(prefix + "/human-moves/black", json={"move": "PASS"}).status_code == 200
    assert client.post(prefix + "/human-moves/white", json={"move": "c3"}).status_code == 200
    reloaded = client_for(path)
    assert reloaded.post(prefix + "/human-moves/black", json={"move": "b3"}).status_code == 200
    returned = reloaded.post(prefix + "/human-moves/white", json={"move": "PASS"})
    assert returned.status_code == 200 and returned.json()["game"]["board_key"] == key
    again = client_for(path)
    assert again.post(prefix + "/human-moves/white", json={"move": "c3"}).status_code == 409
    assert again.get(prefix).json()["board_key"] == key
