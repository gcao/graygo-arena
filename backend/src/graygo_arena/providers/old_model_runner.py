"""Strict legacy checkpoint inference under the training Python environment."""

import importlib
import json
import sys
from pathlib import Path
from typing import Any


def main() -> None:
    torch: Any = importlib.import_module("torch")
    torch.set_num_threads(1)
    payload: Any = json.load(sys.stdin)
    repo = Path(payload["repo"]).resolve()
    sys.path.insert(0, str(repo))
    module: Any = importlib.import_module("model")
    checkpoint = torch.load(payload["checkpoint"], weights_only=True, map_location="cpu")
    cfg = checkpoint["metadata"]["config"]
    if cfg["board_size"] != 9:
        raise ValueError("Historical checkpoint must be 9x9")
    model = module.GrayGoNet(board_size=9, blocks=cfg["blocks"], filters=cfg["filters"])
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval()
    state = payload["state"]
    player = payload["player"]
    other = 3 - player
    planes = torch.zeros(1, 6, 9, 9)
    for point, color in enumerate(state["board"]):
        channel = {player: 0, other: 1, 3: 2, 0: 3}[color]
        planes[0, channel, point // 9, point % 9] = 1
    for channel, name in (
        (4, "forbidden_black" if player == 1 else "forbidden_white"),
        (5, "forbidden_white" if player == 1 else "forbidden_black"),
    ):
        for point in state[name]:
            planes[0, channel, point // 9, point % 9] = 1
    with torch.inference_mode():
        logits = model(planes)[0][0]
    print(json.dumps({"logits": logits.tolist()}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
