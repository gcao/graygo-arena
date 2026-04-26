from pathlib import Path

from graygo_arena.application.models import CreateGameCommand, SeatConfig, TurnRecord
from graygo_arena.application.orchestrator import GameOrchestrator
from graygo_arena.engine import Board, GameState, PassMove, resolve_turn
from graygo_arena.persistence.database import SQLiteDatabase
from graygo_arena.persistence.repositories import SQLiteRepository
from graygo_arena.providers.registry import ProviderCatalog


def repository(path: Path) -> SQLiteRepository:
    return SQLiteRepository(SQLiteDatabase(path))


def test_sqlite_repository_persists_game_turn_calls_transcripts_and_events(tmp_path: Path) -> None:
    repo = repository(tmp_path / "graygo.db")
    orchestrator = GameOrchestrator(repository=repo, providers=ProviderCatalog())
    game = orchestrator.create_game(
        CreateGameCommand(
            black=SeatConfig("scripted_center", "default", "fake"),
            white=SeatConfig("scripted_pass", "default", "fake"),
            max_turns=5,
        )
    )

    result = orchestrator.step_game(game.id)
    reloaded = repository(tmp_path / "graygo.db")

    assert reloaded.get_game(game.id).current_turn == 1
    assert reloaded.get_turn(game.id, 0).post_board_key == result.turn.post_board_key
    assert len(reloaded.list_turns(game.id)) == 1
    assert len(reloaded.list_agent_calls(game.id)) == 2
    assert reloaded.list_events(game.id)[0].event_type == "game.created"
    assert reloaded.list_events(game.id)[-1].event_type == "turn.resolved"


def test_sqlite_repository_round_trips_gray_capture_metadata(tmp_path: Path) -> None:
    repo = repository(tmp_path / "graygo.db")
    orchestrator = GameOrchestrator(repository=repo, providers=ProviderCatalog())
    game = orchestrator.create_game(
        CreateGameCommand(
            black=SeatConfig("scripted_pass", "default", "fake"),
            white=SeatConfig("scripted_pass", "default", "fake"),
        )
    )
    state = GameState(
        board=Board.from_key(
            "+++++++/+WWG+++/+BWBBB+/+BGGWW+/++WBBW+/+++GBB+/+++WW++"
        )
    )
    resolution = resolve_turn(state, PassMove(), PassMove())

    repo.save_turn(
        TurnRecord(
            id="turn_gray_capture",
            game_id=game.id,
            turn_index=0,
            pre_board_key=resolution.pre_board_key,
            post_board_key=resolution.post_board_key,
            black_move=resolution.black_move,
            white_move=resolution.white_move,
            resolution=resolution,
            status="finished",
        )
    )

    reloaded = repository(tmp_path / "graygo.db").get_turn(game.id, 0)
    capture = reloaded.resolution.captures[0]
    assert capture.captured_color == "gray"
    assert capture.by_color == "neutral"
    assert tuple(coordinate.to_label() for coordinate in capture.coordinates) == (
        "d3",
        "d4",
    )


def test_sqlite_transcript_views_preserve_privacy_filters(tmp_path: Path) -> None:
    repo = repository(tmp_path / "graygo.db")
    orchestrator = GameOrchestrator(repository=repo, providers=ProviderCatalog())
    game = orchestrator.create_game(
        CreateGameCommand(
            black=SeatConfig("scripted_center", "default", "fake"),
            white=SeatConfig("scripted_pass", "default", "fake"),
        )
    )

    orchestrator.step_game(game.id)

    public_entries = repo.list_transcripts(game.id, "public")
    black_private = repo.list_transcripts(game.id, "black_private")
    white_private = repo.list_transcripts(game.id, "white_private")
    debug_entries = repo.list_transcripts(game.id, "debug")

    assert len(public_entries) == 1
    assert len(black_private) == 1
    assert len(white_private) == 1
    assert len(debug_entries) == 3
    assert "scripted_center" in black_private[0].text
    assert "scripted_pass" in white_private[0].text
