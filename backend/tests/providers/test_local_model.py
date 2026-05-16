import os
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from graygo_arena.application.models import ProviderMoveRequest, SeatSession
from graygo_arena.core.config import load_settings
from graygo_arena.engine.moves import SeatColor
from graygo_arena.providers.direct import ProviderServiceError
from graygo_arena.providers.local_model import GrayGoTrainedProvider, encode_request_planes


def request9(
    *,
    board_rows: tuple[str, ...] | None = None,
    legal_moves: tuple[str, ...] = ("a1", "e5", "PASS"),
) -> ProviderMoveRequest:
    rows = board_rows or tuple("+" * 9 for _ in range(9))
    return ProviderMoveRequest(
        game_id="game_1",
        seat_session_id="seat_black",
        color="black",
        model="champion",
        board_key="/".join(rows),
        board_rows=rows,
        legal_moves=legal_moves,
        public_history=(),
        private_history=(),
        turn_index=0,
    )


def seat(color: str = "black") -> SeatSession:
    return SeatSession(
        id=f"seat_{color}",
        game_id="game_1",
        color=cast(SeatColor, color),
        provider="graygo_trained",
        model="champion",
        credential_ref="local_file",
    )


def test_graygo_trained_selects_highest_logit_legal_move() -> None:
    logits = [0.0] * 82
    logits[0] = 1.0
    logits[40] = 3.0
    logits[81] = 2.0
    provider = GrayGoTrainedProvider(
        model_path=Path("/missing/champion_traced.pt"),
        runner=lambda _request, _seat: logits,
    )

    response = provider.request_move(request9(), seat())

    assert response.move == "e5"
    assert response.board_key == request9().board_key
    assert "graygo_trained" in response.raw_response


def test_graygo_trained_ignores_illegal_high_logits() -> None:
    logits = [0.0] * 82
    logits[80] = 99.0
    logits[81] = 1.0
    provider = GrayGoTrainedProvider(
        model_path=Path("/missing/champion_traced.pt"),
        runner=lambda _request, _seat: logits,
    )

    response = provider.request_move(request9(legal_moves=("a1", "PASS")), seat())

    assert response.move == "PASS"


def test_graygo_trained_encodes_player_relative_planes_and_forbidden_points() -> None:
    rows = (
        "BWG++++++",
        "+++++++++",
        "+++++++++",
        "+++++++++",
        "+++++++++",
        "+++++++++",
        "+++++++++",
        "+++++++++",
        "+++++++++",
    )
    request = request9(board_rows=rows)
    request = replace(request, own_forbidden=("a1",), opponent_forbidden=("b2",))

    black_planes = encode_request_planes(request, seat("black"), 9)
    white_planes = encode_request_planes(request, seat("white"), 9)

    assert black_planes[0][0][0] == 1.0
    assert black_planes[1][0][1] == 1.0
    assert black_planes[2][0][2] == 1.0
    assert black_planes[3][0][3] == 1.0
    assert black_planes[4][0][0] == 1.0
    assert black_planes[5][1][1] == 1.0
    assert white_planes[0][0][1] == 1.0
    assert white_planes[1][0][0] == 1.0


def test_graygo_trained_rejects_non_matching_board_size() -> None:
    provider = GrayGoTrainedProvider(
        model_path=Path("/missing/champion_traced.pt"),
        runner=lambda _request, _seat: [0.0] * 82,
    )

    with pytest.raises(ProviderServiceError, match="supports 9x9"):
        provider.request_move(
            ProviderMoveRequest(
                game_id="game_1",
                seat_session_id="seat_black",
                color="black",
                model="champion",
                board_key="+++/+++/+++",
                board_rows=("+++", "+++", "+++"),
                legal_moves=("a1", "PASS"),
                public_history=(),
                private_history=(),
                turn_index=0,
            ),
            seat(),
        )


def test_settings_resolves_latest_graygo_champion_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "graygo"
    checkpoints = repo / "checkpoints"
    checkpoints.mkdir(parents=True)
    traced = checkpoints / "champion_traced.pt"
    champion_2 = checkpoints / "champion_iter_0002.pt"
    champion_10 = checkpoints / "champion_iter_0010.pt"
    for path in (traced, champion_2, champion_10):
        path.write_text("checkpoint", encoding="utf-8")
    os.utime(traced, (1, 1))
    os.utime(champion_2, (2, 2))
    os.utime(champion_10, (3, 3))
    env_file = tmp_path / ".env"
    env_file.write_text(f"GRAYGO_MODEL_REPO={repo}\n", encoding="utf-8")
    monkeypatch.setenv("GRAYGO_ENV_FILE", str(env_file))

    settings = load_settings()

    assert settings.graygo_model_path == champion_10
    os.utime(traced, (4, 4))
    settings = load_settings()
    assert settings.graygo_model_path == traced
    assert settings.graygo_model_repo == repo
    assert settings.graygo_model_board_size == 9
