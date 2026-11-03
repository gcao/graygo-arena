"""Frozen historical and accepted-loop model snapshots for independent seats."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from threading import Lock
from typing import Any, cast

from graygo_arena.application.models import ProviderMoveRequest, ProviderMoveResponse, SeatSession
from graygo_arena.providers.direct import ProviderServiceError
from graygo_arena.providers.nfsp_model import ExperimentalNfspProvider


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SnapshotPolicyProvider(ExperimentalNfspProvider):
    def __init__(
        self,
        *,
        checkpoint: Path,
        repo: Path,
        python: Path,
        provider_id: str,
        model_id: str,
        family: str,
        training_records: int | None = None,
    ) -> None:
        super().__init__(
            checkpoint=checkpoint,
            repo=repo,
            python=python,
            provider_id=provider_id,
            model_id=model_id,
            training_records=training_records,
        )
        self.family = family
        self.checksum = sha(checkpoint)

    def _infer(self, state: dict[str, object], player: int) -> list[float]:
        if self.checkpoint is None or sha(self.checkpoint) != self.checksum:
            raise ProviderServiceError("Frozen model snapshot changed during the game")
        if self.family == "average":
            return list(super()._infer(state, player))
        script = Path(__file__).with_name("old_model_runner.py")
        payload = {
            "checkpoint": str(self.checkpoint),
            "repo": str(self.repo),
            "state": state,
            "player": player,
        }
        env = dict(os.environ)
        env.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
        try:
            result = subprocess.run(
                [str(self.python), str(script)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                timeout=self.timeout,
                env=env,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderServiceError("Historical policy inference failed or timed out") from exc
        if result.returncode:
            raise ProviderServiceError(
                "Historical policy inference failed: " + result.stderr[-1200:]
            )
        data: Any = json.loads(result.stdout)
        return [float(x) for x in data["logits"]]

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        response = super().request_move(request, seat)
        metadata = dict(
            response.metadata, checkpoint_sha256=self.checksum, head=self.family, search="disabled"
        )
        raw = json.loads(response.raw_response)
        raw.update(checkpoint_sha256=self.checksum, head=self.family, search="disabled")
        return ProviderMoveResponse(
            response.board_key,
            response.move,
            json.dumps(raw, sort_keys=True),
            "Frozen raw local policy; independent seat sampling, including PASS.",
            metadata,
        )


class LoopChampionProvider:
    """Resolve an atomic champion pointer once per game, never mid-episode."""

    def __init__(self, *, manifest: Path | None, repo: Path, python: Path) -> None:
        self.manifest = manifest
        self.repo = repo
        self.python = python
        self.games: dict[str, SnapshotPolicyProvider] = {}
        self.lock = Lock()

    def _resolve(self, game_id: str) -> SnapshotPolicyProvider:
        with self.lock:
            if game_id in self.games:
                return self.games[game_id]
            if self.manifest is None or not self.manifest.is_file():
                raise ProviderServiceError("The champion loop has no configured release")
            wrapper: Any = json.loads(self.manifest.read_text())
            body = wrapper["body"]
            canonical = json.dumps(
                body, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
            if (
                hashlib.sha256(canonical).hexdigest() != wrapper["sha256"]
                or body["version"] != "graygo/champion-release/1"
            ):
                raise ProviderServiceError("Invalid champion release manifest")
            descriptor = body["champion"]
            if descriptor["rules"] != {"size": 9, "max_rounds": 200, "collision": "gray"}:
                raise ProviderServiceError("Arena loop releases require 9x9/200-round gray rules")
            family = "legacy" if descriptor["kind"] == "legacy" else "average"
            path = Path(descriptor["checkpoint"] if family == "legacy" else descriptor["bundle"])
            expected = (
                descriptor["checkpoint_sha256"]
                if family == "legacy"
                else descriptor["bundle_sha256"]
            )
            if sha(path) != expected:
                raise ProviderServiceError("Champion release payload changed")
            provider = SnapshotPolicyProvider(
                checkpoint=path,
                repo=Path(descriptor["repo"]) if family == "legacy" else self.repo,
                python=self.python,
                provider_id="graygo_loop_champion",
                model_id="latest",
                family=family,
                training_records=cast(int | None, descriptor.get("records")),
            )
            self.games[game_id] = provider
            return provider

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        return self._resolve(request.game_id).request_move(request, seat)
