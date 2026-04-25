"""Direct OpenAI and Anthropic provider adapters."""

from __future__ import annotations

import json
from typing import Any, cast

import httpx

from graygo_arena.application.models import (
    ProviderMoveRequest,
    ProviderMoveResponse,
    SeatSession,
)

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


class OpenAIResponsesProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        default_model: str,
        client: httpx.Client | None = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._client = client or httpx.Client(timeout=30)
        self._base_url = base_url

    def request_move(self, request: ProviderMoveRequest, seat: SeatSession) -> ProviderMoveResponse:
        if not self._api_key:
            raise ProviderCredentialError("OPENAI_API_KEY is not configured")
        response = self._client.post(
            f"{self._base_url}/responses",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": seat.model or self._default_model,
                "max_output_tokens": 512,
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
            },
        )
        response.raise_for_status()
        data = cast(dict[str, object], response.json())
        parsed = _parse_move_payload(_extract_openai_text(data))
        return ProviderMoveResponse(
            board_key=parsed["board_key"],
            move=parsed["move"],
            raw_response=json.dumps(data),
            strategic_summary=parsed["strategic_summary"],
            metadata={"provider_response_id": str(data.get("id", ""))},
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
        response = self._client.post(
            f"{self._base_url}/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
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
        response.raise_for_status()
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
            "Return board_key, move, and a concise strategic_summary.",
        )
    )


def _parse_move_payload(value: str) -> dict[str, str]:
    parsed = cast(dict[str, object], json.loads(value))
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
