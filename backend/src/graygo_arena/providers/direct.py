"""Direct OpenAI and Anthropic provider adapters."""

from __future__ import annotations

import base64
import json
from typing import Any, NoReturn, cast

import httpx

from graygo_arena.application.models import (
    ProviderMoveRequest,
    ProviderMoveResponse,
    SeatSession,
)
from graygo_arena.core.config import OpenAIReasoningEffort

MOVE_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["board_key", "move", "strategic_summary"],
    "properties": {
        "board_key": {"type": "string"},
        "move": {"type": "string"},
        "strategic_summary": {"type": "string"},
    },
}


class ProviderCredentialError(RuntimeError):
    pass


class ProviderServiceError(RuntimeError):
    pass


class OpenAIResponsesProvider:
    def __init__(
        self,
        *,
        auth_token: str | None,
        default_model: str,
        reasoning_effort: OpenAIReasoningEffort,
        max_output_tokens: int,
        client: httpx.Client | None = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._auth_token = auth_token
        self._default_model = default_model
        self._reasoning_effort: OpenAIReasoningEffort = reasoning_effort
        self._max_output_tokens = max_output_tokens
        self._client = client or httpx.Client(timeout=30)
        self._base_url = base_url

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        if not self._auth_token:
            raise ProviderCredentialError(
                "OPENAI_API_KEY or OPENAI_CODEX_API_KEY is not configured"
            )
        payload: dict[str, object] = {
            "model": seat.model or self._default_model,
            "max_output_tokens": self._max_output_tokens,
            "reasoning": {"effort": self._reasoning_effort},
            "input": [
                {
                    "role": "user",
                    "content": _move_prompt(request, seat),
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "graygo_move",
                    "schema": MOVE_SCHEMA,
                    "strict": True,
                }
            },
        }
        response = _post_provider_json(
            provider="OpenAI",
            client=self._client,
            url=f"{self._base_url}/responses",
            headers={
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json",
            },
            payload=payload,
        )
        data = cast(dict[str, object], response.json())
        parsed = _parse_move_payload(_extract_openai_text(data))
        return ProviderMoveResponse(
            board_key=parsed["board_key"],
            move=parsed["move"],
            raw_response=json.dumps(data),
            strategic_summary=parsed["strategic_summary"],
            metadata={"provider_response_id": str(data.get("id", ""))},
        )


class OpenAICodexResponsesProvider:
    def __init__(
        self,
        *,
        auth_token: str | None,
        default_model: str,
        reasoning_effort: OpenAIReasoningEffort,
        client: httpx.Client | None = None,
        base_url: str = "https://chatgpt.com/backend-api",
        originator: str = "pi",
    ) -> None:
        self._auth_token = auth_token
        self._default_model = default_model
        self._reasoning_effort: OpenAIReasoningEffort = reasoning_effort
        self._client = client or httpx.Client(timeout=60)
        self._base_url = base_url
        self._originator = originator

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        if not self._auth_token:
            raise ProviderCredentialError("OPENAI_CODEX_TOKEN is not configured")
        model = seat.model or self._default_model
        account_id = _extract_codex_account_id(self._auth_token)
        payload: dict[str, object] = {
            "model": model,
            "store": False,
            "stream": True,
            "instructions": (
                "Choose exactly one legal Gray Go move. Return only a JSON object "
                "with board_key, move, and strategic_summary."
            ),
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": _move_prompt(request, seat)}],
                }
            ],
            "text": {"verbosity": "medium"},
            "include": ["reasoning.encrypted_content"],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        }
        effort = _clamp_codex_reasoning_effort(model, self._reasoning_effort)
        if effort != "none":
            payload["reasoning"] = {"effort": effort, "summary": "auto"}

        response = _post_provider_json(
            provider="OpenAI Codex",
            client=self._client,
            url=_resolve_codex_responses_url(self._base_url),
            headers={
                "Authorization": f"Bearer {self._auth_token}",
                "chatgpt-account-id": account_id,
                "OpenAI-Beta": "responses=experimental",
                "originator": self._originator,
                "User-Agent": "graygo-arena",
                "accept": "text/event-stream",
                "content-type": "application/json",
            },
            payload=payload,
        )
        text, response_id = _extract_codex_sse_text(response.text)
        parsed = _parse_move_payload(text)
        return ProviderMoveResponse(
            board_key=parsed["board_key"],
            move=parsed["move"],
            raw_response=response.text,
            strategic_summary=parsed["strategic_summary"],
            metadata={"provider_response_id": response_id},
        )


class AnthropicMessagesProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        default_model: str,
        client: httpx.Client | None = None,
        base_url: str = "https://api.anthropic.com/v1",
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._client = client or httpx.Client(timeout=30)
        self._base_url = base_url

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        if not self._api_key:
            raise ProviderCredentialError("ANTHROPIC_API_KEY is not configured")
        response = _post_provider_json(
            provider="Anthropic",
            client=self._client,
            url=f"{self._base_url}/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            payload={
                "model": seat.model or self._default_model,
                "max_tokens": 512,
                "system": "Choose exactly one legal Gray Go move using the provided tool.",
                "messages": [{"role": "user", "content": _move_prompt(request, seat)}],
                "tools": [
                    {
                        "name": "choose_graygo_move",
                        "description": "Return the chosen Gray Go move for this seat.",
                        "input_schema": MOVE_SCHEMA,
                    }
                ],
                "tool_choice": {"type": "tool", "name": "choose_graygo_move"},
            },
        )
        data = cast(dict[str, object], response.json())
        parsed = _extract_anthropic_tool_payload(data)
        return ProviderMoveResponse(
            board_key=parsed["board_key"],
            move=parsed["move"],
            raw_response=json.dumps(data),
            strategic_summary=parsed["strategic_summary"],
            metadata={"provider_response_id": str(data.get("id", ""))},
        )


def _move_prompt(request: ProviderMoveRequest, seat: SeatSession) -> str:
    return "\n".join(
        (
            f"You are playing Gray Go as {seat.color}.",
            "Choose exactly one legal move from the current resolved board.",
            "Do not update the board yourself.",
            f"BoardKey: {request.board_key}",
            "Board:",
            *request.board_rows,
            f"Legal moves: {', '.join(request.legal_moves)}",
            (
                "Return only JSON with board_key, move, and a concise strategic_summary. "
                "Do not wrap it in Markdown."
            ),
        )
    )


def _post_provider_json(
    *,
    provider: str,
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
) -> httpx.Response:
    try:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _raise_provider_status_error(provider, exc)
    except httpx.HTTPError as exc:
        msg = f"{provider} request failed before a response was received: {type(exc).__name__}"
        raise ProviderServiceError(msg) from exc
    return response


def _raise_provider_status_error(provider: str, exc: httpx.HTTPStatusError) -> NoReturn:
    status = exc.response.status_code
    details = _provider_error_details(exc.response)
    if status in {401, 403}:
        msg = f"{provider} authentication failed ({status}). Check provider credentials. {details}"
        raise ProviderCredentialError(msg) from exc
    msg = f"{provider} request failed ({status}). {details}"
    raise ProviderServiceError(msg) from exc


def _provider_error_details(response: httpx.Response) -> str:
    body = response.text.strip().replace("\n", " ")
    if not body:
        return "Provider response did not include details."
    if len(body) > 240:
        body = f"{body[:237]}..."
    return f"Provider response: {body}"


def _parse_move_payload(value: str) -> dict[str, str]:
    parsed_obj = json.loads(_json_object_text(value))
    if not isinstance(parsed_obj, dict):
        msg = "provider response JSON was not an object"
        raise ValueError(msg)
    parsed = cast(dict[str, object], parsed_obj)
    board_key = parsed.get("board_key")
    move = parsed.get("move")
    strategic_summary = parsed.get("strategic_summary")
    if not isinstance(board_key, str) or not isinstance(move, str):
        msg = "provider response did not contain board_key and move strings"
        raise ValueError(msg)
    return {
        "board_key": board_key,
        "move": move,
        "strategic_summary": strategic_summary if isinstance(strategic_summary, str) else "",
    }


def _json_object_text(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1]).strip()
            if stripped.startswith("json"):
                stripped = stripped.removeprefix("json").strip()
    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        candidate = stripped[start : end + 1]
        json.loads(candidate)
        return candidate


def _extract_openai_text(data: dict[str, object]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text
    output = data.get("output")
    if isinstance(output, list):
        for item_obj in cast(list[object], output):
            if not isinstance(item_obj, dict):
                continue
            item = cast(dict[str, object], item_obj)
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block_obj in cast(list[object], content):
                if not isinstance(block_obj, dict):
                    continue
                block = cast(dict[str, object], block_obj)
                if isinstance(block.get("text"), str):
                    return cast(str, block["text"])
    msg = "OpenAI response did not contain output text"
    raise ValueError(msg)


def _try_extract_openai_text(data: dict[str, object]) -> str | None:
    try:
        return _extract_openai_text(data)
    except ValueError:
        return None


def _extract_anthropic_tool_payload(data: dict[str, object]) -> dict[str, str]:
    content = data.get("content")
    if not isinstance(content, list):
        msg = "Anthropic response did not contain content blocks"
        raise ValueError(msg)
    for block_obj in cast(list[object], content):
        if not isinstance(block_obj, dict):
            continue
        block = cast(dict[str, object], block_obj)
        if block.get("type") == "tool_use" and block.get("name") == "choose_graygo_move":
            payload = block.get("input")
            if not isinstance(payload, dict):
                break
            return _coerce_tool_payload(cast(dict[str, Any], payload))
    msg = "Anthropic response did not contain choose_graygo_move tool output"
    raise ValueError(msg)


def _coerce_tool_payload(payload: dict[str, Any]) -> dict[str, str]:
    return _parse_move_payload(json.dumps(payload))


def _resolve_codex_responses_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/codex/responses"):
        return normalized
    if normalized.endswith("/codex"):
        return f"{normalized}/responses"
    return f"{normalized}/codex/responses"


def _extract_codex_account_id(token: str) -> str:
    payload = _decode_jwt_payload(token)
    auth_claim = _object_dict(payload.get("https://api.openai.com/auth"))
    if auth_claim is None:
        raise ProviderCredentialError(
            "OPENAI_CODEX_TOKEN does not include the ChatGPT account claim"
        )
    account_id = auth_claim.get("chatgpt_account_id")
    if not isinstance(account_id, str) or not account_id:
        raise ProviderCredentialError("OPENAI_CODEX_TOKEN does not include chatgpt_account_id")
    return account_id


def _decode_jwt_payload(token: str) -> dict[str, object]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ProviderCredentialError("OPENAI_CODEX_TOKEN is not a JWT access token")
    payload = parts[1]
    padded_payload = f"{payload}{'=' * ((4 - len(payload) % 4) % 4)}"
    try:
        decoded = base64.urlsafe_b64decode(padded_payload.encode("ascii")).decode("utf-8")
        parsed = json.loads(decoded)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProviderCredentialError("OPENAI_CODEX_TOKEN payload could not be decoded") from exc
    if not isinstance(parsed, dict):
        raise ProviderCredentialError("OPENAI_CODEX_TOKEN payload is not an object")
    return cast(dict[str, object], parsed)


def _clamp_codex_reasoning_effort(model: str, effort: OpenAIReasoningEffort) -> str:
    model_id = model.rsplit("/", 1)[-1]
    if model_id.startswith(("gpt-5.2", "gpt-5.3", "gpt-5.4")) and effort == "minimal":
        return "low"
    if model_id == "gpt-5.1" and effort == "xhigh":
        return "high"
    if model_id == "gpt-5.1-codex-mini":
        return "high" if effort in {"high", "xhigh"} else "medium"
    return effort


def _extract_codex_sse_text(raw: str) -> tuple[str, str]:
    events = _parse_sse_events(raw)
    if not events:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI Codex response JSON was not an object")
        data = cast(dict[str, object], parsed)
        return _extract_openai_text(data), str(data.get("id", ""))

    delta_text: list[str] = []
    done_text: str | None = None
    completed_text: str | None = None
    response_id = ""

    for event in events:
        event_type = event.get("type")
        if event_type == "error":
            error = _object_dict(event.get("error"))
            if error is not None and isinstance(error.get("message"), str):
                raise ProviderServiceError(f"OpenAI Codex error: {error['message']}")
            raise ProviderServiceError(f"OpenAI Codex error: {json.dumps(event)}")
        if event_type == "response.failed":
            response = _object_dict(event.get("response"))
            if response is not None:
                error = _object_dict(response.get("error"))
                if error is not None and isinstance(error.get("message"), str):
                    raise ProviderServiceError(f"OpenAI Codex response failed: {error['message']}")
            raise ProviderServiceError("OpenAI Codex response failed")
        if event_type == "response.output_text.delta" and isinstance(event.get("delta"), str):
            delta_text.append(cast(str, event["delta"]))
            continue
        if event_type == "response.output_item.done":
            item = event.get("item")
            item_text = _extract_codex_item_text(item)
            if item_text:
                done_text = item_text
            continue
        if event_type in {"response.completed", "response.done"}:
            response = _object_dict(event.get("response"))
            if response is not None:
                if isinstance(response.get("id"), str):
                    response_id = cast(str, response["id"])
                completed_text = _try_extract_openai_text(response)

    text = done_text or completed_text or "".join(delta_text)
    if not text:
        raise ValueError("OpenAI Codex response did not contain output text")
    return text, response_id


def _parse_sse_events(raw: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    normalized = raw.replace("\r\n", "\n")
    for chunk in normalized.split("\n\n"):
        data_lines = [
            line.removeprefix("data:").strip()
            for line in chunk.split("\n")
            if line.startswith("data:")
        ]
        if not data_lines:
            continue
        data = "\n".join(data_lines).strip()
        if not data or data == "[DONE]":
            continue
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            events.append(cast(dict[str, object], parsed))
    return events


def _extract_codex_item_text(item: object) -> str | None:
    item_dict = _object_dict(item)
    if item_dict is None:
        return None
    if item_dict.get("type") != "message":
        return None
    content = item_dict.get("content")
    if not isinstance(content, list):
        return None
    parts: list[str] = []
    for block_obj in cast(list[object], content):
        block = _object_dict(block_obj)
        if block is None:
            continue
        if block.get("type") == "output_text" and isinstance(block.get("text"), str):
            parts.append(cast(str, block["text"]))
        elif block.get("type") == "refusal" and isinstance(block.get("refusal"), str):
            parts.append(cast(str, block["refusal"]))
    return "".join(parts) or None


def _object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)
