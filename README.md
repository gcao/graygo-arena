# Gray Go Arena

Backend-owned Gray Go arena for running isolated AI-vs-AI matches with replay, transcript, export, and guardrail checks.

## Run Locally

Backend:

```sh
cd backend
PYTHONPATH=src uv run uvicorn graygo_arena.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```sh
cd frontend
npm run dev
```

The frontend dev server is configured in `frontend/vite.config.ts` to bind to `0.0.0.0:5174` and proxy `/api` to the backend on `127.0.0.1:8000`.

## OpenAI Credentials

Create a repo-root `.env` file. The backend also accepts `backend/.env`, or a custom path through `GRAYGO_ENV_FILE`. `.env` files are ignored by git in this repo.

Recommended API-key setup:

```sh
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.1-codex-max
OPENAI_REASONING_EFFORT=high
OPENAI_MAX_OUTPUT_TOKENS=4096
```

Codex-token setup:

```sh
OPENAI_CODEX_TOKEN=...
OPENAI_MODEL=gpt-5.1-codex-max
OPENAI_REASONING_EFFORT=xhigh
OPENAI_MAX_OUTPUT_TOKENS=4096
```

`OPENAI_API_KEY` takes precedence over `OPENAI_CODEX_TOKEN`. `CODEX_TOKEN` is also accepted as a fallback alias.

To get a local Codex token after signing in with Codex CLI, run:

```sh
codex --login
node <<'NODE'
const fs = require("fs");
const path = `${process.env.HOME}/.codex/auth.json`;
const auth = JSON.parse(fs.readFileSync(path, "utf8"));

function tokenFrom(value) {
  if (typeof value === "string" && value) return value;
  if (!value || typeof value !== "object") return "";
  for (const key of ["api_key", "key", "token", "access_token", "value"]) {
    const nested = tokenFrom(value[key]);
    if (nested) return nested;
  }
  return "";
}

const token = tokenFrom(auth.OPENAI_API_KEY) || tokenFrom(auth.tokens?.access_token);
if (!token) {
  throw new Error("No Codex token found in ~/.codex/auth.json");
}
console.log(token);
NODE
```

Paste the printed value into `.env` as `OPENAI_CODEX_TOKEN=...`.

Treat `.env` and Codex tokens as secrets. Do not commit them. If the OpenAI API rejects a Codex token for your account or organization, use `OPENAI_API_KEY` from the API dashboard instead.

Before creating an OpenAI-backed game, test the configured credential:

```sh
curl -s http://127.0.0.1:8000/api/providers/test \
  -H 'Content-Type: application/json' \
  -d '{"provider":"openai_default","model":"gpt-5.5"}'
```

If the response has `"ok": false`, fix `.env` before starting a match. The step API reports rejected provider credentials as `502` responses instead of server errors.

## Model And Reasoning

`OPENAI_MODEL` can be any model name your account can use with the Responses API. The frontend model field also accepts typed model names per seat, so you can override the advertised default when creating a game.

`OPENAI_REASONING_EFFORT` is sent as `reasoning.effort` on OpenAI Responses requests. Supported values are:

```text
none
minimal
low
medium
high
xhigh
```

OpenAI documents `xhigh` support for models after `gpt-5.1-codex-max`; use `high` if a selected model rejects `xhigh`.

## Anthropic Credentials

```sh
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```
