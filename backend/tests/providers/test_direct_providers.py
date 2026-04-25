import base64
import json
from typing import cast

import httpx

from graygo_arena.application.models import ProviderMoveRequest, SeatSession
from graygo_arena.core.config import Settings
from graygo_arena.providers.direct import (
    AnthropicMessagesProvider,
    OpenAICodexResponsesProvider,
    OpenAIResponsesProvider,
)
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


def codex_jwt(account_id: str = "acc_test") -> str:
    def encode(value: object) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    payload = {"https://api.openai.com/auth": {"chatgpt_account_id": account_id}}
    return f"{encode({'alg': 'none'})}.{encode(payload)}.signature"


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
        auth_token="sk-codex-test",
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
    assert captured["authorization"] == "Bearer sk-codex-test"
    assert payload_dict["model"] == "model_from_seat"
    assert payload_dict["reasoning"] == {"effort": "xhigh"}
    assert payload_dict["max_output_tokens"] == 4096
    assert format_dict["type"] == "json_schema"
    assert response.move == "a1"
    assert response.metadata["provider_response_id"] == "resp_123"


def test_codex_oauth_adapter_uses_chatgpt_backend_headers_and_parses_sse() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["account_id"] = request.headers["chatgpt-account-id"]
        captured["beta"] = request.headers["openai-beta"]
        captured["originator"] = request.headers["originator"]
        captured["accept"] = request.headers["accept"]
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            text=(
                'data: {"type":"response.output_text.delta","delta":"{\\"board_key\\":'
                '\\"+++/+++/+++\\",\\"move\\":\\"b2\\",\\"strategic_summary\\":'
                '\\"Claim the center.\\"}"}\n\n'
                'data: {"type":"response.completed","response":{"id":"resp_codex",'
                '"status":"completed"}}\n\n'
                "data: [DONE]\n\n"
            ),
        )

    provider = OpenAICodexResponsesProvider(
        auth_token=codex_jwt("acc_123"),
        default_model="gpt-5.5",
        reasoning_effort="xhigh",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="https://chatgpt.test/backend-api",
        originator="pi",
    )

    response = provider.request_move(move_request(), seat("openai_default"))

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert captured["url"] == "https://chatgpt.test/backend-api/codex/responses"
    assert captured["authorization"] == f"Bearer {codex_jwt('acc_123')}"
    assert captured["account_id"] == "acc_123"
    assert captured["beta"] == "responses=experimental"
    assert captured["originator"] == "pi"
    assert captured["accept"] == "text/event-stream"
    assert payload["model"] == "model_from_seat"
    assert payload["stream"] is True
    assert payload["reasoning"] == {"effort": "xhigh", "summary": "auto"}
    assert response.move == "b2"
    assert response.metadata["provider_response_id"] == "resp_codex"


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
        openai_auth_token="sk-codex-test",
        openai_auth_source="codex_api_key",
        openai_model="gpt-5.1-codex-max",
        openai_reasoning_effort="high",
        anthropic_api_key="sk-ant-test",
        anthropic_model="claude-sonnet-4-20250514",
    )

    providers = ProviderCatalog(settings=settings).list_providers()
    by_id = {provider.id: provider for provider in providers}

    assert by_id["openai_default"].configured is True
    assert by_id["openai_default"].auth_type == "codex_api_key"
    assert by_id["anthropic_default"].configured is True
    assert "sk-codex-test" not in repr(providers)
    assert "sk-ant-test" not in repr(providers)


def test_provider_catalog_routes_codex_oauth_to_chatgpt_backend() -> None:
    settings = Settings(
        openai_auth_token=codex_jwt("acc_456"),
        openai_auth_source="codex_oauth",
        openai_model="gpt-5.5",
        openai_reasoning_effort="high",
        openai_codex_base_url="https://chatgpt.test/backend-api",
    )

    catalog = ProviderCatalog(settings=settings)
    providers = catalog.list_providers()
    by_id = {provider.id: provider for provider in providers}

    assert by_id["openai_default"].configured is True
    assert by_id["openai_default"].auth_type == "codex_oauth"
    assert "acc_456" not in repr(providers)
    assert "token" not in repr(providers).lower()


def test_provider_catalog_reports_missing_keys_without_network() -> None:
    catalog = ProviderCatalog(settings=Settings())

    openai_result = catalog.test_provider("openai_default", "gpt-5.1-codex-max")
    anthropic_result = catalog.test_provider("anthropic_default", "claude-sonnet-4-20250514")

    assert openai_result.ok is False
    assert anthropic_result.ok is False
    assert openai_result.message == "not configured"
    assert anthropic_result.message == "not configured"
