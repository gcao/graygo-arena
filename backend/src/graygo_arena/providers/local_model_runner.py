"""Subprocess inference runner for the local GrayGoNet provider.

This module intentionally avoids importing graygo_arena so it can run under the
training repository's Python environment, where PyTorch is installed.
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        model_path = Path(str(payload["model_path"])).expanduser()
        graygo_repo = Path(str(payload["graygo_repo"])).expanduser()
        device = str(payload.get("device", "cpu"))
        planes = payload["planes"]
        logits = run_inference(model_path, graygo_repo, device, planes)
        print(json.dumps({"logits": logits}))
        return 0
    except Exception as exc:  # noqa: BLE001 - stderr is surfaced through provider error handling
        print(str(exc), file=sys.stderr)
        return 1


def run_inference(
    model_path: Path,
    graygo_repo: Path,
    device: str,
    planes: object,
) -> list[float]:
    torch = importlib.import_module("torch")
    model = load_model(torch, model_path, graygo_repo, device)
    tensor = torch.tensor([planes], dtype=torch.float32, device=device)
    with torch.no_grad():
        output = model(tensor)
    policy_logits = cast(Any, output[0] if isinstance(output, tuple) else output)
    return tensor_to_float_list(policy_logits)


def load_model(torch: Any, model_path: Path, graygo_repo: Path, device: str) -> Any:
    if not model_path.is_file():
        raise RuntimeError(f"model not found: {model_path}")
    try:
        model = torch.jit.load(str(model_path), map_location=device)
    except Exception:
        model = load_checkpoint(torch, model_path, graygo_repo, device)
    model.eval()
    return model


def load_checkpoint(torch: Any, model_path: Path, graygo_repo: Path, device: str) -> Any:
    if str(graygo_repo) not in sys.path:
        sys.path.insert(0, str(graygo_repo))
    graygo_model = importlib.import_module("model")
    graygo_net = graygo_model.GrayGoNet

    checkpoint = torch.load(str(model_path), map_location=device, weights_only=False)
    if not isinstance(checkpoint, Mapping) or "state_dict" not in checkpoint:
        raise RuntimeError("checkpoint does not contain a state_dict")
    checkpoint_mapping = cast(Mapping[str, Any], checkpoint)
    loaded_state = checkpoint_mapping["state_dict"]
    if not isinstance(loaded_state, Mapping):
        raise RuntimeError("checkpoint state_dict is not a mapping")
    state_dict = cast(Mapping[str, Any], loaded_state)

    blocks, filters, board_size = infer_model_shape(
        state_dict,
        cast(object, checkpoint_mapping.get("metadata")),
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
        raise RuntimeError("checkpoint did not match GrayGoNet parameters")
    model.load_state_dict(model_state)
    model.to(device)
    return model


def tensor_to_float_list(tensor: Any) -> list[float]:
    values = cast(list[object], tensor.detach().cpu().reshape(-1).tolist())
    numbers: list[float] = []
    for value in values:
        if not isinstance(value, int | float):
            raise RuntimeError("model returned non-numeric logits")
        numbers.append(float(value))
    return numbers


def infer_model_shape(
    state_dict: Mapping[str, Any],
    metadata: object,
) -> tuple[int, int, int]:
    filters = int(state_dict["stem_conv.conv.weight"].shape[0])
    block_indices = {
        int(str(key).split(".")[1])
        for key in state_dict
        if str(key).startswith("res_blocks.")
    }
    board_size = metadata_board_size(metadata)
    if board_size is None and "policy_fc.weight" in state_dict:
        board_size = int(round((state_dict["policy_fc.weight"].shape[0] - 1) ** 0.5))
    return len(block_indices), filters, board_size or 9


def metadata_board_size(metadata: object) -> int | None:
    if not isinstance(metadata, Mapping):
        return None
    metadata_mapping = cast(Mapping[str, object], metadata)
    config = metadata_mapping.get("config")
    if isinstance(config, Mapping) and "board_size" in config:
        config_mapping = cast(Mapping[str, object], config)
        return metadata_int(config_mapping["board_size"])
    if "board_size" in metadata_mapping:
        return metadata_int(metadata_mapping["board_size"])
    return None


def metadata_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError("metadata board_size must be an integer")


if __name__ == "__main__":
    raise SystemExit(main())
