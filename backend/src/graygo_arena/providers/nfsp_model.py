"""Experimental full-state NFSP policy; arena legal moves stay authoritative."""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from graygo_arena.application.models import ProviderMoveRequest, ProviderMoveResponse, SeatSession
from graygo_arena.engine.coordinates import Coordinate
from graygo_arena.providers.direct import ProviderServiceError

PROVIDER = "graygo_nfsp_experimental"
MODEL = "avg-9x9-diagnostic-32k"
type ScoresRunner = Callable[[dict[str, object], int], Sequence[float]]


def action(label: str) -> int:
    if label == "PASS":
        return 81
    point = Coordinate.parse(label, 9)
    return point.row * 9 + point.col


def colors(rows: tuple[str, ...]) -> list[int]:
    if len(rows) != 9 or any(len(row) != 9 for row in rows):
        raise ProviderServiceError("NFSP diagnostic requires a 9x9 board")
    palette = {"+": 0, "B": 1, "W": 2, "G": 3}
    try:
        return [palette[cell] for row in rows for cell in row]
    except KeyError as exc:
        raise ProviderServiceError("Unknown board symbol") from exc


def rule_state(request: ProviderMoveRequest, seat: SeatSession) -> dict[str, object]:
    if request.max_turns != 200:
        raise ProviderServiceError("This NFSP checkpoint requires the 200-turn limit")
    if len(request.rule_history) != min(request.turn_index, 2):
        raise ProviderServiceError("NFSP requires all available completed public history slots")
    mine = [action(label) for label in request.own_forbidden]
    other = [action(label) for label in request.opponent_forbidden]
    black, white = (mine, other) if seat.color == "black" else (other, mine)
    return {
        "rule_version": "graygo/1",
        "rules": {"size": 9, "max_rounds": 200, "collision": "gray"},
        "board": colors(request.board_rows),
        "forbidden_black": black,
        "forbidden_white": white,
        "history": [
            {
                "before": colors(row.before_rows),
                "black": action(row.black_move),
                "white": action(row.white_move),
            }
            for row in request.rule_history
        ],
        "pass_streak": request.mutual_pass_streak,
        "rounds_played": request.turn_index,
    }


class ExperimentalNfspProvider:
    def __init__(
        self,
        *,
        checkpoint: Path | None,
        repo: Path,
        python: Path,
        runner: ScoresRunner | None = None,
        timeout_seconds: float = 30.0,
        provider_id: str = PROVIDER,
        model_id: str = MODEL,
        training_records: int | None = 32768,
    ) -> None:
        self.checkpoint = checkpoint
        self.repo = repo
        self.python = python
        self.runner = runner
        self.timeout = timeout_seconds
        self.provider_id = provider_id
        self.model_id = model_id
        self.training_records = training_records

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        if request.color != seat.color or request.seat_session_id != seat.id:
            raise ProviderServiceError("NFSP seat/request mismatch")
        state = rule_state(request, seat)
        player = 1 if seat.color == "black" else 2
        logits = list(self.runner(state, player) if self.runner else self._infer(state, player))
        if len(logits) != 82 or any(not math.isfinite(value) for value in logits):
            raise ProviderServiceError("NFSP returned invalid policy logits")
        legal = request.legal_moves
        if not legal:
            raise ProviderServiceError("NFSP cannot select from an empty legal mask")
        scores = [float(logits[action(label)]) for label in legal]
        maximum = max(scores)
        weights = [math.exp(value - maximum) for value in scores]
        # A private deterministic stream makes retries stable without sharing
        # draws or pending moves with the opponent.
        key = "|".join(
            (request.game_id, seat.id, seat.color, str(request.turn_index), request.board_key)
        )
        seed = int.from_bytes(hashlib.sha256(key.encode()).digest(), "big")
        move = random.Random(seed).choices(legal, weights=weights, k=1)[0]
        probability = weights[legal.index(move)] / sum(weights)
        raw = {
            "provider": self.provider_id,
            "model": self.model_id,
            "board_key": request.board_key,
            "move": move,
            "policy_probability": probability,
            "training_records": self.training_records,
            "experimental": True,
            "strength_validated": False,
        }
        return ProviderMoveResponse(
            board_key=request.board_key,
            move=move,
            raw_response=json.dumps(raw, sort_keys=True),
            strategic_summary="Experimental local policy; playing strength is unvalidated.",
            metadata={
                "model": self.model_id,
                "training_records": str(self.training_records)
                if self.training_records is not None
                else "historical",
                "head": "average",
                "selection": "sampled legal policy including PASS",
                "validation": "diagnostic only",
            },
        )

    def _infer(self, state: dict[str, object], player: int) -> Sequence[float]:
        if self.checkpoint is None or not self.checkpoint.is_file():
            raise ProviderServiceError("NFSP experimental checkpoint is not configured")
        script = Path(__file__).with_name("nfsp_model_runner.py")
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
            raise ProviderServiceError("NFSP inference process failed or timed out") from exc
        if result.returncode != 0:
            raise ProviderServiceError("NFSP inference failed: " + result.stderr.strip()[-1200:])
        try:
            values = json.loads(result.stdout)["logits"]
            if not isinstance(values, list):
                raise ValueError("numeric policy required")
            numbers: list[float] = []
            for value in cast(list[object], values):
                if not isinstance(value, int | float):
                    raise ValueError("numeric policy required")
                numbers.append(float(value))
            return numbers
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderServiceError("NFSP inference returned an invalid response") from exc
