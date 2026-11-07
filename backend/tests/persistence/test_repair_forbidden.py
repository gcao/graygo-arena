import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from graygo_arena.api.routes import create_services
from graygo_arena.engine import Board, Coordinate, ForbiddenState
from graygo_arena.engine.moves import SeatColor
from graygo_arena.main import create_app
from graygo_arena.persistence.repair_forbidden import repair


def test_repair_releases_a_captured_bridge_point_without_changing_board_or_history(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repair.db"
    services = create_services(database_path=path)
    client = TestClient(create_app(services))
    game = client.post(
        "/api/games",
        json={"board_size": 9, "black": {"provider": "human"}, "white": {"provider": "human"}},
    ).json()
    game_id = game["id"]
    prefix = f"/api/games/{game_id}"
    before = Board.from_key(
        "+++++++G+/+++++++++/+++++++++/+++++++++/+++++++++/+++++++++/+++++++++/+++++++++/++++++WBW"
    )
    services.repository.save_game(replace(services.repository.get_game(game_id), board=before))
    client.post(prefix + "/start")
    client.post(prefix + "/human-moves/black", json={"move": "h8"})
    client.post(prefix + "/human-moves/white", json={"move": "h8"})
    captured = services.repository.get_game(game_id)
    services.repository.save_game(
        replace(captured, forbidden=ForbiddenState(black=frozenset({Coordinate.parse("i8", 9)})))
    )
    assert client.post(prefix + "/human-moves/white", json={"move": "i8"}).status_code == 200
    assert client.post(prefix + "/human-moves/black", json={"move": "i8"}).status_code == 409
    original_turn = services.repository.get_turn(game_id, 0)
    assert repair(path)["games_updated"] == 1
    assert services.repository.get_game(game_id).forbidden.black
    backup = tmp_path / "private-backup.json"
    report = repair(path, apply=True, backup=backup)
    assert report["games_updated"] == 1 and report["invalid_pending_cleared"] == 0
    assert backup.stat().st_mode & 0o777 == 0o600
    assert json.loads(backup.read_text())["games"][0]["old_black"] == '["i8"]'
    assert services.repository.get_game(game_id).board == captured.board
    assert services.repository.get_turn(game_id, 0) == original_turn
    assert services.repository.get_game(game_id).forbidden == ForbiddenState()
    joined = client.post(prefix + "/human-moves/black", json={"move": "i8"})
    assert joined.status_code == 200
    board = joined.json()["game"]["board"]
    assert all(board[row][7] == "G" for row in (0, 7, 8))


def test_repair_preserves_accumulated_suicide_restrictions_after_passes(tmp_path: Path) -> None:
    path = tmp_path / "suicide.db"
    services = create_services(database_path=path)
    client = TestClient(create_app(services))
    game = client.post(
        "/api/games",
        json={"board_size": 5, "black": {"provider": "human"}, "white": {"provider": "human"}},
    ).json()
    prefix = f"/api/games/{game['id']}"
    board = Board.from_key("+++++/++W++/+W+W+/++W++/+++++")
    services.repository.save_game(replace(services.repository.get_game(game["id"]), board=board))
    client.post(prefix + "/start")
    for black in ("c3", "PASS"):
        client.post(prefix + "/human-moves/black", json={"move": black})
        client.post(prefix + "/human-moves/white", json={"move": "PASS"})
    current = services.repository.get_game(game["id"])
    assert current.forbidden.black == frozenset({Coordinate.parse("c3", 5)})
    assert repair(path)["games_updated"] == 0
    repair(path, apply=True, backup=tmp_path / "backup.json")
    assert services.repository.get_game(game["id"]).forbidden == current.forbidden


def test_repair_clears_only_pending_moves_invalidated_by_repetition(tmp_path: Path) -> None:
    from graygo_arena.application.models import PendingMove

    path = tmp_path / "pending.db"
    services = create_services(database_path=path)
    client = TestClient(create_app(services))
    game = client.post(
        "/api/games",
        json={"board_size": 5, "black": {"provider": "human"}, "white": {"provider": "human"}},
    ).json()
    prefix = f"/api/games/{game['id']}"
    board = Board.from_key("++W++/+WBW+/+B+B+/++B++/+++++")
    services.repository.save_game(replace(services.repository.get_game(game["id"]), board=board))
    client.post(prefix + "/start")
    for black, white in [("PASS", "c3"), ("b3", "PASS")]:
        client.post(prefix + "/human-moves/black", json={"move": black})
        client.post(prefix + "/human-moves/white", json={"move": white})
    current = services.repository.get_game(game["id"])
    services.repository.save_game(replace(current, forbidden=ForbiddenState()))
    pending_moves: tuple[tuple[SeatColor, str, str], ...] = (
        ("black", "PASS", current.black_seat_id),
        ("white", "c3", current.white_seat_id),
    )
    for color, label, seat_id in pending_moves:
        services.repository.save_pending_move(
            PendingMove(
                id="pending-" + color,
                game_id=game["id"],
                turn_index=current.current_turn,
                seat_session_id=seat_id,
                color=color,
                move=label,
                source="human",
                raw_response="fixture",
            )
        )
    report = repair(path, apply=True, backup=tmp_path / "pending-backup.json")
    assert report["invalid_pending_cleared"] == 1
    pending = services.repository.get_pending_moves(game["id"], current.current_turn)
    assert len(pending) == 1 and pending[0].color == "black" and pending[0].move == "PASS"
