import json
from typing import cast

import httpx

from graygo_arena.application.models import ProviderMoveRequest, SeatSession
from graygo_arena.core.config import Settings
from graygo_arena.providers.direct import AnthropicMessagesProvider, OpenAIResponsesProvider
from graygo_arena.providers.registry import ProviderCatalog


def move_request() -> ProviderMoveRequest:
    return ProviderMoveRequest(
        game_id="game_1",
        seat_session_id="seat_black",
        color="black",
        model="model_from_seat",
        board_key="+++/+++/+++",
        board_rows=("+++", "+++", "+++"),
        legal_moves=("a1", "b2", "PASS"),
        public_history=(),
        private_history=(),
        turn_index=0,
    )


def seat(provider: str) -> SeatSession:
    return SeatSession(
        id="seat_black",
        game_id="game_1",
        color="black",
        provider=provider,
        model="model_from_seat",
        credential_ref=f"{provider}_ref",
    )


def test_openai_adapter_uses_responses_json_schema_and_parses_output() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "id": "resp_123",
                "output_text": json.dumps(
                    {
                        "board_key": "+++/+++/+++",
                        "move": "a1",
                        "strategic_summary": "Take the first corner.",
                    }
                ),
            },
        )

    provider = OpenAIResponsesProvider(
        auth_token="codex-test-token",
        default_model="gpt-5.1-codex-max",
        reasoning_effort="xhigh",
        max_output_tokens=4096,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://api.openai.test/v1",
    )

    response = provider.request_move(move_request(), seat("openai_default"))

    payload = captured["payload"]
    assert isinstance(payload, dict)
    payload_dict = cast(dict[str, object], payload)
    text = payload_dict["text"]
    assert isinstance(text, dict)
    text_dict = cast(dict[str, object], text)
    text_format = text_dict["format"]
    assert isinstance(text_format, dict)
    format_dict = cast(dict[str, object], text_format)
    assert captured["authorization"] == "Bearer codex-test-token"
    assert payload_dict["model"] == "model_from_seat"
    assert payload_dict["reasoning"] == {"effort": "xhigh"}
    assert payload_dict["max_output_tokens"] == 4096
    assert format_dict["type"] == "json_schema"
    assert response.move == "a1"
    assert response.metadata["provider_response_id"] == "resp_123"


def test_anthropic_adapter_uses_messages_tool_choice_and_parses_tool_use() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["api_key"] = request.headers["x-api-key"]
        captured["version"] = request.headers["anthropic-version"]
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "id": "msg_123",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "choose_graygo_move",
                        "input": {
                            "board_key": "+++/+++/+++",
                            "move": "b2",
                            "strategic_summary": "Claim the center.",
                        },
                    }
                ],
            },
        )

    provider = AnthropicMessagesProvider(
        api_key="sk-ant-test",
        default_model="claude-sonnet-4-20250514",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://api.anthropic.test/v1",
    )

    response = provider.request_move(move_request(), seat("anthropic_default"))

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert captured["api_key"] == "sk-ant-test"
    assert captured["version"] == "2023-06-01"
    assert payload["tool_choice"] == {"type": "tool", "name": "choose_graygo_move"}
    assert response.move == "b2"
    assert response.metadata["provider_response_id"] == "msg_123"


def test_provider_catalog_exposes_real_aliases_without_secret_values() -> None:
    settings = Settings(
        openai_auth_token="codex-test-token",
        openai_auth_source="codex_token",
        openai_model="gpt-5.1-codex-max",
        openai_reasoning_effort="high",
        anthropic_api_key="sk-ant-test",
        anthropic_model="claude-sonnet-4-20250514",
    )

    providers = ProviderCatalog(settings=settings).list_providers()
    by_id = {provider.id: provider for provider in providers}

    assert by_id["openai_default"].configured is True
    assert by_id["openai_default"].auth_type == "codex"
    assert by_id["anthropic_default"].configured is True
    assert "codex-test-token" not in repr(providers)
    assert "sk-ant-test" not in repr(providers)


def test_provider_catalog_reports_missing_keys_without_network() -> None:
    catalog = ProviderCatalog(settings=Settings())

    openai_result = catalog.test_provider("openai_default", "gpt-5.1-codex-max")
    anthropic_result = catalog.test_provider("anthropic_default", "claude-sonnet-4-20250514")

    assert openai_result.ok is False
    assert anthropic_result.ok is False
    assert openai_result.message == "not configured"
    assert anthropic_result.message == "not configured"
