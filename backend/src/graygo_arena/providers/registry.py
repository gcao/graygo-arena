"""Safe provider discovery and adapter lookup."""

from __future__ import annotations

import httpx

from graygo_arena.application.models import ProviderAdapter, ProviderMoveRequest, SeatSession
from graygo_arena.core.config import Settings, load_settings
from graygo_arena.providers.base import ProviderInfo, ProviderTestResult
from graygo_arena.providers.direct import (
    AnthropicMessagesProvider,
    OpenAICodexResponsesProvider,
    OpenAIResponsesProvider,
    ProviderCredentialError,
    ProviderServiceError,
)
from graygo_arena.providers.fake import (
    FakeRandomProvider,
    ScriptedCenterProvider,
    ScriptedPassProvider,
    ScriptedSequenceProvider,
)


class ProviderCatalog:
    def __init__(
        self,
        *,
        seed: int = 0,
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._adapters: dict[str, ProviderAdapter] = {
            "fake_random": FakeRandomProvider(seed=seed),
            "scripted_center": ScriptedCenterProvider(),
            "scripted_pass": ScriptedPassProvider(),
            "scripted_sequence": ScriptedSequenceProvider(),
        }
        if self._settings.openai_auth_token:
            if self._settings.openai_auth_source == "codex_oauth":
                self._adapters["openai_default"] = OpenAICodexResponsesProvider(
                    auth_token=self._settings.openai_auth_token,
                    default_model=self._settings.openai_model,
                    reasoning_effort=self._settings.openai_reasoning_effort,
                    client=http_client,
                    base_url=self._settings.openai_codex_base_url,
                    originator=self._settings.openai_codex_originator,
                )
            else:
                self._adapters["openai_default"] = OpenAIResponsesProvider(
                    auth_token=self._settings.openai_auth_token,
                    default_model=self._settings.openai_model,
                    reasoning_effort=self._settings.openai_reasoning_effort,
                    max_output_tokens=self._settings.openai_max_output_tokens,
                    client=http_client,
                )
        if self._settings.anthropic_api_key:
            self._adapters["anthropic_default"] = AnthropicMessagesProvider(
                api_key=self._settings.anthropic_api_key,
                default_model=self._settings.anthropic_model,
                client=http_client,
            )

    def adapter_for(self, provider: str) -> ProviderAdapter:
        try:
            return self._adapters[provider]
        except KeyError as exc:
            msg = f"unknown provider alias: {provider}"
            raise ValueError(msg) from exc

    def list_providers(self) -> tuple[ProviderInfo, ...]:
        return (
            ProviderInfo(
                id="fake_random",
                provider="fake_random",
                auth_type="none",
                configured=True,
                models=("deterministic",),
            ),
            ProviderInfo(
                id="scripted_center",
                provider="scripted_center",
                auth_type="none",
                configured=True,
                models=("default",),
            ),
            ProviderInfo(
                id="scripted_pass",
                provider="scripted_pass",
                auth_type="none",
                configured=True,
                models=("default",),
            ),
            ProviderInfo(
                id="openai_default",
                provider="openai_default",
                auth_type=(
                    "api_key"
                    if self._settings.openai_auth_source == "api_key"
                    else "codex_api_key"
                    if self._settings.openai_auth_source == "codex_api_key"
                    else "codex_oauth"
                    if self._settings.openai_auth_source == "codex_oauth"
                    else "api_key_or_codex_oauth"
                ),
                configured=self._settings.openai_auth_token is not None,
                models=(self._settings.openai_model,),
            ),
            ProviderInfo(
                id="anthropic_default",
                provider="anthropic_default",
                auth_type="api_key",
                configured=self._settings.anthropic_api_key is not None,
                models=(self._settings.anthropic_model,),
            ),
            ProviderInfo(
                id="scripted_sequence",
                provider="scripted_sequence",
                auth_type="none",
                configured=True,
                models=("default",),
            ),
        )

    def test_provider(self, provider: str, model: str) -> ProviderTestResult:
        if provider == "openai_default" and self._settings.openai_auth_token is None:
            return ProviderTestResult(
                provider=provider,
                model=model,
                ok=False,
                message=self._settings.openai_auth_error or "not configured",
            )
        if provider == "anthropic_default" and self._settings.anthropic_api_key is None:
            return ProviderTestResult(
                provider=provider,
                model=model,
                ok=False,
                message="not configured",
            )
        adapter = self.adapter_for(provider)
        request = ProviderMoveRequest(
            game_id="provider_test",
            seat_session_id="seat_test",
            color="black",
            model=model,
            board_key="+++/+++/+++",
            board_rows=("+++", "+++", "+++"),
            legal_moves=("a1", "b2", "PASS"),
            public_history=(),
            private_history=(),
            turn_index=0,
        )
        seat = SeatSession(
            id="seat_test",
            game_id="provider_test",
            color="black",
            provider=provider,
            model=model,
            credential_ref="fake",
        )
        try:
            response = adapter.request_move(request, seat)
        except (ProviderCredentialError, ProviderServiceError) as exc:
            return ProviderTestResult(
                provider=provider,
                model=model,
                ok=False,
                message=str(exc),
            )
        return ProviderTestResult(
            provider=provider,
            model=model,
            ok=response.board_key == request.board_key and response.move in request.legal_moves,
            message="provider completed test request",
        )
