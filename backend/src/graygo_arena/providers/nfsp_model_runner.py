"""Python 3.12-compatible worker for the training environment; no arena imports."""

import importlib
import json
import sys
from pathlib import Path
from typing import Any


def main() -> None:
    torch: Any = importlib.import_module("torch")

    payload = json.load(sys.stdin)
    repo = Path(payload["repo"]).expanduser().resolve()
    sys.path.insert(0, str(repo / "src"))
    encoding: Any = importlib.import_module("graygo.encoding")
    engine: Any = importlib.import_module("graygo.engine")
    models: Any = importlib.import_module("graygo.models")

    torch.set_num_threads(1)
    bundle = torch.load(payload["checkpoint"], map_location="cpu", weights_only=True)
    if (
        bundle["format_version"] != "graygo/arena-nfsp-average/1"
        or bundle["encoding_version"] != encoding.ENCODING_VERSION
        or bundle["board_size"] != 9
        or not isinstance(bundle["training_records"], int)
        or bundle["training_records"] < 0
        or bundle["head"] != "average"
    ):
        raise ValueError("Unsupported full-state NFSP checkpoint")
    model = models.PolicyNet(models.ModelConfig(**bundle["model_config"]))
    model.load_state_dict(bundle["state_dict"], strict=True)
    model.eval()
    state = engine.State.from_dict(payload["state"])
    observation = encoding.encode(state, payload["player"])
    with torch.inference_mode():
        logits = model(
            torch.tensor(observation.spatial[None], dtype=torch.float32),
            torch.tensor(observation.global_features[None], dtype=torch.float32),
        )
    print(json.dumps({"logits": logits[0].tolist()}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
