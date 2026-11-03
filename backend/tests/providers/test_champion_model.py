import hashlib
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from tests.providers.test_nfsp_model import request, seat

from graygo_arena.providers.champion_model import LoopChampionProvider, SnapshotPolicyProvider
from graygo_arena.providers.direct import ProviderServiceError


def release(path: Path, checkpoint: Path) -> None:
    body = {
        "version": "graygo/champion-release/1",
        "champion": {
            "kind": "legacy",
            "repo": str(path.parent),
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            "rules": {"size": 9, "max_rounds": 200, "collision": "gray"},
        },
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    path.write_text(json.dumps({"body": body, "sha256": hashlib.sha256(raw).hexdigest()}))


def test_historical_policy_preserves_pass_and_labels_exact_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"frozen")
    model = SnapshotPolicyProvider(
        checkpoint=checkpoint,
        repo=tmp_path,
        python=Path("/unused"),
        provider_id="graygo_old_champion",
        model_id="v6-0081-raw-policy",
        family="legacy",
    )
    values = [-1000.0] * 82
    values[81] = 1000.0

    def infer(_state: dict[str, object], _player: int) -> list[float]:
        return values

    model.runner = infer
    result = model.request_move(request(), seat())
    assert result.move == "PASS"
    raw = json.loads(result.raw_response)
    assert raw["checkpoint_sha256"] == hashlib.sha256(b"frozen").hexdigest()
    assert raw["provider"] == "graygo_old_champion"
    assert raw["training_records"] is None
    assert raw["search"] == "disabled"


def test_champion_updates_apply_to_new_games_while_existing_games_keep_snapshot(
    tmp_path: Path,
) -> None:
    one = tmp_path / "one.pt"
    one.write_bytes(b"one")
    two = tmp_path / "two.pt"
    two.write_bytes(b"two")
    pointer = tmp_path / "champion.json"
    release(pointer, one)
    provider = LoopChampionProvider(manifest=pointer, repo=tmp_path, python=Path("/unused"))
    first_request = replace(request(), game_id="game-one")

    def infer(
        _self: SnapshotPolicyProvider, _state: dict[str, object], _player: int
    ) -> list[float]:
        return [0.0] * 82

    with patch.object(SnapshotPolicyProvider, "_infer", infer):
        old = provider.request_move(first_request, seat())
        release(pointer, two)
        same = provider.request_move(first_request, seat())
        new = provider.request_move(replace(first_request, game_id="game-two"), seat())
    assert old.metadata["checkpoint_sha256"] == same.metadata["checkpoint_sha256"]
    assert new.metadata["checkpoint_sha256"] != old.metadata["checkpoint_sha256"]
    two.write_bytes(b"changed")
    with pytest.raises(ProviderServiceError):
        provider.request_move(replace(first_request, game_id="game-two"), seat())


def test_corrupt_champion_pointer_is_rejected(tmp_path: Path) -> None:
    model = tmp_path / "one.pt"
    model.write_bytes(b"one")
    pointer = tmp_path / "champion.json"
    release(pointer, model)
    data = json.loads(pointer.read_text())
    data["sha256"] = "0" * 64
    pointer.write_text(json.dumps(data))
    provider = LoopChampionProvider(manifest=pointer, repo=tmp_path, python=Path("/unused"))
    with pytest.raises(ProviderServiceError):
        provider.request_move(replace(request(), game_id="new-game"), seat())
