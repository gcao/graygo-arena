"""Local trained GrayGoNet provider adapter."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from graygo_arena.application.models import (
    ProviderMoveRequest,
    ProviderMoveResponse,
    SeatSession,
)
from graygo_arena.engine.coordinates import Coordinate
from graygo_arena.providers.direct import ProviderServiceError

type LogitsRunner = Callable[[ProviderMoveRequest, SeatSession], Sequence[float]]


class GrayGoTrainedProvider:
    """Select moves with a local TorchScript GrayGoNet checkpoint."""

    def __init__(
        self,
        *,
        model_path: Path,
        graygo_repo: Path | None = None,
        python_path: Path | None = None,
        board_size: int = 9,
        device: str = "cpu",
        runner: LogitsRunner | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._model_path = model_path.expanduser()
        self._graygo_repo = (graygo_repo or self._model_path.parent.parent).expanduser()
        self._python_path = (python_path or Path(sys.executable)).expanduser()
        self._board_size = board_size
        self._device = device
        self._runner = runner
        self._timeout_seconds = timeout_seconds
        self._model: Any | None = None

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def board_size(self) -> int:
        return self._board_size

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        if len(request.board_rows) != self._board_size:
            raise ProviderServiceError(
                f"graygo_trained supports {self._board_size}x{self._board_size} boards, "
                f"got {len(request.board_rows)}x{len(request.board_rows)}"
            )
        if self._runner is None and not self._model_path.is_file():
            raise ProviderServiceError(f"graygo_trained model not found: {self._model_path}")
        if request.turn_index == 0:
            return self._opening_move(request, seat)
        if self._runner:
            logits = tuple(self._runner(request, seat))
        else:
            logits = tuple(self._run_model(request, seat))
        expected_logits = self._board_size * self._board_size + 1
        if len(logits) != expected_logits:
            raise ProviderServiceError(
                f"graygo_trained model returned {len(logits)} policy logits, "
                f"expected {expected_logits}"
            )
        selection = _select_legal_move(logits, request, seat, self._board_size)
        raw = {
            "provider": "graygo_trained",
            "model_path": str(self._model_path),
            "board_key": request.board_key,
            "move": selection.move,
            "policy_logit": selection.score,
            "policy_tie_count": selection.tie_count,
        }
        return ProviderMoveResponse(
            board_key=request.board_key,
            move=selection.move,
            raw_response=json.dumps(raw, sort_keys=True),
            strategic_summary=(
                "Selected the highest-logit legal placement from the trained GrayGoNet policy."
            ),
            metadata={
                "model_path": str(self._model_path),
                "graygo_repo": str(self._graygo_repo),
                "board_size": str(self._board_size),
            },
        )

    def _opening_move(
        self,
        request: ProviderMoveRequest,
        seat: SeatSession,
    ) -> ProviderMoveResponse:
        candidates = tuple(move for move in request.legal_moves if move != "PASS")
        move = _choose_seeded_move(
            candidates or ("PASS",),
            (
                "opening",
                request.game_id,
                request.board_key,
            ),
            seat.color,
        )
        raw = {
            "provider": "graygo_trained",
            "model_path": str(self._model_path),
            "board_key": request.board_key,
            "move": move,
            "opening_randomized": True,
            "opening_pool_count": len(candidates),
        }
        return ProviderMoveResponse(
            board_key=request.board_key,
            move=move,
            raw_response=json.dumps(raw, sort_keys=True),
            strategic_summary="Randomized the trained model's first move.",
            metadata={
                "model_path": str(self._model_path),
                "graygo_repo": str(self._graygo_repo),
                "board_size": str(self._board_size),
                "selection": "opening_randomized",
            },
        )

    def _run_model(self, request: ProviderMoveRequest, seat: SeatSession) -> Sequence[float]:
        try:
            torch = _torch()
        except ProviderServiceError:
            return self._run_subprocess(request, seat)
        return self._run_in_process(torch, request, seat)

    def _run_in_process(
        self,
        torch: Any,
        request: ProviderMoveRequest,
        seat: SeatSession,
    ) -> Sequence[float]:
        model = self._load_model(torch)
        planes = encode_request_planes(request, seat, self._board_size)
        tensor = torch.tensor([planes], dtype=torch.float32, device=self._device)
        with torch.no_grad():
            output = model(tensor)
        policy_logits = cast(Any, output[0] if isinstance(output, tuple) else output)
        return _tensor_to_float_list(policy_logits)

    def _run_subprocess(
        self,
        request: ProviderMoveRequest,
        seat: SeatSession,
    ) -> Sequence[float]:
        if not self._python_path.is_file():
            raise ProviderServiceError(
                f"graygo_trained Python interpreter not found: {self._python_path}"
            )
        runner_path = Path(__file__).with_name("local_model_runner.py")
        payload = {
            "model_path": str(self._model_path),
            "graygo_repo": str(self._graygo_repo),
            "device": self._device,
            "planes": encode_request_planes(request, seat, self._board_size),
        }
        try:
            completed = subprocess.run(
                [str(self._python_path), str(runner_path)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
                timeout=self._timeout_seconds,
                env=_runner_env(self._graygo_repo),
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderServiceError("graygo_trained inference timed out") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise ProviderServiceError(f"graygo_trained inference failed: {detail}")
        try:
            data = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderServiceError("graygo_trained inference returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise ProviderServiceError("graygo_trained inference returned invalid JSON")
        response_data = cast(dict[str, object], data)
        logits = response_data.get("logits")
        if not isinstance(logits, list):
            raise ProviderServiceError("graygo_trained inference returned non-list logits")
        return _objects_to_float_list(cast(list[object], logits), "graygo_trained inference")

    def _load_model(self, torch: Any) -> Any:
        if self._model is not None:
            return self._model
        if not self._model_path.is_file():
            raise ProviderServiceError(f"graygo_trained model not found: {self._model_path}")
        try:
            model = torch.jit.load(str(self._model_path), map_location=self._device)
        except Exception as jit_exc:  # noqa: BLE001 - raw checkpoints are a supported fallback
            model = self._load_checkpoint(torch, jit_exc)
        try:
            model.eval()
        except AttributeError as exc:
            raise ProviderServiceError("graygo_trained model does not support eval()") from exc
        self._model = model
        return model

    def _load_checkpoint(self, torch: Any, jit_exc: Exception) -> Any:
        try:
            graygo_model = _graygo_model_module(self._graygo_repo)
            graygo_net = graygo_model.GrayGoNet
            checkpoint = torch.load(
                str(self._model_path),
                map_location=self._device,
                weights_only=False,
            )
            if not isinstance(checkpoint, Mapping) or "state_dict" not in checkpoint:
                raise ProviderServiceError("checkpoint does not contain a state_dict")
            checkpoint_mapping = cast(Mapping[str, Any], checkpoint)
            loaded_state = checkpoint_mapping["state_dict"]
            if not isinstance(loaded_state, Mapping):
                raise ProviderServiceError("checkpoint state_dict is not a mapping")
            state_dict = cast(Mapping[str, Any], loaded_state)
            blocks, filters, board_size = _infer_model_shape(
                state_dict,
                cast(object, checkpoint_mapping.get("metadata")),
            )
            if board_size != self._board_size:
                raise ProviderServiceError(
                    f"graygo_trained checkpoint is {board_size}x{board_size}, "
                    f"but provider is configured for {self._board_size}x{self._board_size}"
                )
            model = graygo_net(board_size=board_size, blocks=blocks, filters=filters)
            model_state = model.state_dict()
            loaded = 0
            for key, value in state_dict.items():
                model_value = model_state.get(key, None)
                checkpoint_value = value
                if model_value is not None and model_value.shape == checkpoint_value.shape:
                    model_state[key] = value
                    loaded += 1
            if loaded == 0:
                raise ProviderServiceError("checkpoint did not match GrayGoNet parameters")
            model.load_state_dict(model_state)
            model.to(self._device)
            return model
        except ProviderServiceError:
            raise
        except Exception as checkpoint_exc:  # noqa: BLE001 - provider boundary must convert failures
            raise ProviderServiceError(
                "failed to load graygo_trained model as TorchScript or checkpoint: "
                f"torchscript={jit_exc}; checkpoint={checkpoint_exc}"
            ) from checkpoint_exc


def _torch() -> Any:
    try:
        return importlib.import_module("torch")
    except ModuleNotFoundError as exc:
        raise ProviderServiceError(
            "PyTorch is required for graygo_trained. Run the arena backend in an "
            "environment that can import torch, or choose another provider."
        ) from exc


def encode_request_planes(
    request: ProviderMoveRequest,
    seat: SeatSession,
    board_size: int,
) -> list[list[list[float]]]:
    planes = [
        [[0.0 for _ in range(board_size)] for _ in range(board_size)] for _ in range(6)
    ]
    own_cell = "B" if seat.color == "black" else "W"
    opponent_cell = "W" if seat.color == "black" else "B"

    for row_index, row in enumerate(request.board_rows):
        if len(row) != board_size:
            raise ProviderServiceError(
                f"graygo_trained requires square {board_size}x{board_size} board rows"
            )
        for col_index, cell in enumerate(row):
            plane = _plane_for_cell(cell, own_cell, opponent_cell)
            planes[plane][row_index][col_index] = 1.0

    for label in request.own_forbidden:
        coordinate = Coordinate.parse(label, board_size)
        planes[4][coordinate.row][coordinate.col] = 1.0
    for label in request.opponent_forbidden:
        coordinate = Coordinate.parse(label, board_size)
        planes[5][coordinate.row][coordinate.col] = 1.0
    return planes


def _plane_for_cell(cell: str, own_cell: str, opponent_cell: str) -> int:
    if cell == own_cell:
        return 0
    if cell == opponent_cell:
        return 1
    if cell == "G":
        return 2
    if cell == "+":
        return 3
    raise ProviderServiceError(f"unsupported board cell for graygo_trained: {cell}")


class MoveSelection:
    def __init__(self, *, move: str, score: float, tie_count: int) -> None:
        self.move = move
        self.score = score
        self.tie_count = tie_count


def _select_legal_move(
    logits: Sequence[float],
    request: ProviderMoveRequest,
    seat: SeatSession,
    board_size: int,
) -> MoveSelection:
    legal_moves = tuple(move for move in request.legal_moves if move != "PASS")
    if not legal_moves and "PASS" in request.legal_moves:
        legal_moves = ("PASS",)
    if not legal_moves:
        return MoveSelection(move="PASS", score=float("-inf"), tie_count=0)

    scored = tuple((_action_logit(logits, move, board_size), move) for move in legal_moves)
    best_score = max(score for score, _move in scored)
    best_moves = tuple(move for score, move in scored if score == best_score)
    return MoveSelection(
        move=_choose_tied_move(best_moves, request, seat),
        score=float(best_score),
        tie_count=len(best_moves),
    )


def _choose_tied_move(
    moves: tuple[str, ...],
    request: ProviderMoveRequest,
    seat: SeatSession,
) -> str:
    if len(moves) == 1:
        return moves[0]
    return _choose_seeded_move(
        moves,
        (
            "tie",
            request.game_id,
            str(request.turn_index),
            request.board_key,
        ),
        seat.color,
    )


def _choose_seeded_move(
    moves: tuple[str, ...],
    seed_parts: tuple[str, ...],
    color: str,
) -> str:
    seed = "|".join(seed_parts)
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(moves)
    if color == "white" and len(moves) > 1:
        index = (index + max(1, len(moves) // 2)) % len(moves)
    return moves[index]


def _action_logit(logits: Sequence[float], move: str, board_size: int) -> float:
    if move == "PASS":
        return float(logits[board_size * board_size])
    coordinate = Coordinate.parse(move, board_size)
    return float(logits[coordinate.row * board_size + coordinate.col])


def _runner_env(graygo_repo: Path) -> dict[str, str]:
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    entries = [str(graygo_repo)]
    if existing_pythonpath:
        entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    return env


def _graygo_model_module(graygo_repo: Path) -> Any:
    repo = str(graygo_repo)
    if repo not in sys.path:
        sys.path.insert(0, repo)
    return importlib.import_module("model")


def _tensor_to_float_list(tensor: Any) -> list[float]:
    values = cast(list[object], tensor.detach().cpu().reshape(-1).tolist())
    return _objects_to_float_list(values, "graygo_trained model")


def _objects_to_float_list(values: Sequence[object], source: str) -> list[float]:
    numbers: list[float] = []
    for value in values:
        if not isinstance(value, int | float):
            raise ProviderServiceError(f"{source} returned non-numeric logits")
        numbers.append(float(value))
    return numbers


def _infer_model_shape(
    state_dict: Mapping[str, Any],
    metadata: object,
) -> tuple[int, int, int]:
    stem_weight = state_dict["stem_conv.conv.weight"]
    filters = int(stem_weight.shape[0])
    block_indices = {
        int(str(key).split(".")[1])
        for key in state_dict
        if str(key).startswith("res_blocks.")
    }
    blocks = len(block_indices)
    board_size = _metadata_board_size(metadata)
    if board_size is None and "policy_fc.weight" in state_dict:
        board_size = int(round((state_dict["policy_fc.weight"].shape[0] - 1) ** 0.5))
    return blocks, filters, board_size or 9


def _metadata_board_size(metadata: object) -> int | None:
    if not isinstance(metadata, Mapping):
        return None
    metadata_mapping = cast(Mapping[str, object], metadata)
    config = metadata_mapping.get("config")
    if isinstance(config, Mapping) and "board_size" in config:
        config_mapping = cast(Mapping[str, object], config)
        return _metadata_int(config_mapping["board_size"])
    if "board_size" in metadata_mapping:
        return _metadata_int(metadata_mapping["board_size"])
    return None


def _metadata_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError("metadata board_size must be an integer")
