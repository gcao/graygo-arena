# Gray Go Arena

Backend-owned Gray Go arena for running isolated AI, human-vs-computer, and human-vs-human matches with replay, transcript, export, and guardrail checks.

## Run Locally

Backend:

```sh
cd backend
PYTHONPATH=src uv run uvicorn graygo_arena.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```sh
cd frontend
npm run dev
```

The backend listens on `0.0.0.0:8000`. The frontend dev server is configured in `frontend/vite.config.ts` to bind to `0.0.0.0:5174` and proxy `/api` to the backend on the same host.

The backend persists games in SQLite at `GRAYGO_DATABASE_PATH` or `.runtime/graygo.db`. The frontend stores the active game id, latest game snapshot, new-game settings, transcript view, and board display toggles in browser `localStorage`, then rehydrates the game from the backend when the browser opens again.

New games default to a 9x9 board, matching the trained GrayGoNet checkpoint shape.

## Human Seats

Choose `human` as a seat provider to play from the shared board. In human-vs-human games, each side seals a move on the same screen; the move stays hidden until both sides have sealed and the backend resolves the turn. In human-vs-computer games, the computer seat starts thinking as soon as the turn is running, and the board resolves once the human move and computer move are both ready.

## Local Trained GrayGoNet

Choose `graygo_trained` as a seat provider to play against the latest champion model in `~/proj/graygo`. By default the backend resolves `GRAYGO_MODEL_REPO` to the sibling `graygo` checkout, prefers the newest fresh `checkpoints/champion_traced.pt`, and falls back to the highest-numbered `champion_iter_*.pt` checkpoint when the traced export is stale or missing.

Optional overrides:

```sh
GRAYGO_MODEL_REPO=~/proj/graygo
GRAYGO_MODEL_PATH=latest
GRAYGO_MODEL_PYTHON=~/proj/graygo/.venv/bin/python
GRAYGO_MODEL_DEVICE=cpu
GRAYGO_MODEL_BOARD_SIZE=9
```

The arena backend does not need PyTorch installed in its own Python environment. If PyTorch is unavailable there, the provider runs inference through `GRAYGO_MODEL_PYTHON`, which should point at the training repo environment.

For trained-model seats, turn 0 is randomized from legal placements so same-model matches do not start from identical deterministic policy choices. From turn 1 onward, moves come from the model policy.

## Experimental NFSP 9x9 demo

The new provider is graygo_nfsp_experimental, model avg-9x9-diagnostic-32k.
It uses an actual 32,768-record 9x9 self-play checkpoint (228 Q updates, 58
supervised updates) from a hardware-profile run. Playing strength is unvalidated;
this is not a promoted champion or a completed 8M/80M training run.

Set GRAYGO_NFSP_MODEL_PATH to the exported inference bundle, and point
GRAYGO_MODEL_REPO at its compatible training source and GRAYGO_MODEL_PYTHON
at the training environment. The provider uses the full 30 spatial channels and
14 globals, including both completed rule-history slots and current restrictions.
Only public state reaches the inference worker. It samples the legal average
policy, including PASS, with separate deterministic per-seat draws.

Choose a 9x9 board and 200-turn limit, Black human, and White
graygo_nfsp_experimental. Create the game, press Start, select an empty point
to seal the move. The backend resolves it after the computer move is ready.

The arena's existing rules are retained: its single-mutual-pass ending,
capture restrictions and lack of the training engine's two-round ko differ
from the checkpoint's training rules. This demo tests the interface and allows
experimental play; its results are not training-engine strength measurements.

## OpenAI Credentials

Create a repo-root `.env` file. The backend also accepts `backend/.env`, or a custom path through `GRAYGO_ENV_FILE`. `.env` files are ignored by git in this repo.

Recommended API-key setup:

```sh
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.1-codex-max
OPENAI_REASONING_EFFORT=high
OPENAI_MAX_OUTPUT_TOKENS=4096
```

Codex CLI API-key setup:

```sh
OPENAI_CODEX_API_KEY=sk-...
OPENAI_MODEL=gpt-5.1-codex-max
OPENAI_REASONING_EFFORT=xhigh
OPENAI_MAX_OUTPUT_TOKENS=4096
```

`OPENAI_API_KEY` takes precedence over `OPENAI_CODEX_API_KEY`.

Codex OAuth token setup:

```sh
OPENAI_CODEX_TOKEN=eyJ...
OPENAI_MODEL=gpt-5.5
OPENAI_REASONING_EFFORT=xhigh
```

The OAuth token mode uses the same ChatGPT Codex backend pattern as GSD-2: it calls `https://chatgpt.com/backend-api/codex/responses`, extracts `chatgpt_account_id` from the JWT, and sends that value as `chatgpt-account-id`. It does not send the OAuth token to `api.openai.com/v1/responses`.

To get the Codex OAuth access token from a local Codex login:

```sh
codex login
node <<'NODE'
const fs = require("fs");
const path = `${process.env.HOME}/.codex/auth.json`;
const auth = JSON.parse(fs.readFileSync(path, "utf8"));
const token = auth.tokens?.access_token || auth.OPENAI_CODEX_TOKEN || "";
if (!token || !token.startsWith("eyJ")) {
  throw new Error("No Codex OAuth access token found in ~/.codex/auth.json");
}
console.log(token);
NODE
```

Add the printed value to repo-root `.env` as `OPENAI_CODEX_TOKEN=...`. Optional Codex OAuth overrides are:

```sh
OPENAI_CODEX_BASE_URL=https://chatgpt.com/backend-api
OPENAI_CODEX_ORIGINATOR=pi
```

Credential precedence is `OPENAI_API_KEY`, then `OPENAI_CODEX_API_KEY`, then `OPENAI_CODEX_TOKEN` or `CODEX_TOKEN`.

Codex CLI sign-in may create a separate auto-generated API key. If your local auth file stores that key, this prints only an API-key-shaped value:

```sh
codex --login
node <<'NODE'
const fs = require("fs");
const path = `${process.env.HOME}/.codex/auth.json`;
const auth = JSON.parse(fs.readFileSync(path, "utf8"));

function apiKeyFrom(value) {
  if (typeof value === "string" && value.startsWith("sk-")) return value;
  if (!value || typeof value !== "object") return "";
  for (const key of ["api_key", "apiKey", "key", "OPENAI_API_KEY", "value"]) {
    const nested = apiKeyFrom(value[key]);
    if (nested) return nested;
  }
  return "";
}

const key = apiKeyFrom(auth.OPENAI_API_KEY);
if (!key) {
  throw new Error("No local Codex API key found. Use an API key from the OpenAI dashboard.");
}
console.log(key);
NODE
```

Paste the printed value into `.env` as `OPENAI_CODEX_API_KEY=...`. If the script does not find an `sk-...` value, create or copy an API key from the OpenAI API dashboard and use `OPENAI_API_KEY=...`.

Treat `.env` and API keys as secrets. Do not commit them.

Before creating an OpenAI-backed game, test the configured credential:

```sh
curl -s http://127.0.0.1:8000/api/providers/test \
  -H 'Content-Type: application/json' \
  -d '{"provider":"openai_default","model":"gpt-5.5"}'
```

If the response has `"ok": false`, fix `.env` before starting a match. The step API reports rejected provider credentials as `502` responses instead of server errors.

## Model And Reasoning

`OPENAI_MODEL` can be any model name your account can use with the selected OpenAI mode. The frontend model field also accepts typed model names per seat, so you can override the advertised default when creating a game.

`OPENAI_REASONING_EFFORT` is sent as `reasoning.effort` on OpenAI requests. Supported values are:

```text
none
minimal
low
medium
high
xhigh
```

Use `high` if a selected model rejects `xhigh`. `OPENAI_MAX_OUTPUT_TOKENS` is sent only for public Responses API-key requests; Codex OAuth follows the ChatGPT backend streaming request shape.

## Anthropic Credentials

```sh
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```
