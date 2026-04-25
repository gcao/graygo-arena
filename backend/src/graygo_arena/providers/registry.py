"""Safe provider discovery and adapter lookup."""

from __future__ import annotations

from graygo_arena.application.models import ProviderAdapter, ProviderMoveRequest, SeatSession
from graygo_arena.providers.base import ProviderInfo, ProviderTestResult
from graygo_arena.providers.fake import (
    FakeRandomProvider,
    ScriptedCenterProvider,
    ScriptedPassProvider,
    ScriptedSequenceProvider,
)


class ProviderCatalog:
    def __init__(self, *, seed: int = 0) -> None:
        self._adapters: dict[str, ProviderAdapter] = {
            "fake_random": FakeRandomProvider(seed=seed),
            "scripted_center": ScriptedCenterProvider(),
            "scripted_pass": ScriptedPassProvider(),
            "scripted_sequence": ScriptedSequenceProvider(),
        }

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
                id="scripted_sequence",
                provider="scripted_sequence",
                auth_type="none",
                configured=True,
                models=("default",),
            ),
        )

    def test_provider(self, provider: str, model: str) -> ProviderTestResult:
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
        response = adapter.request_move(request, seat)
        return ProviderTestResult(
            provider=provider,
            model=model,
            ok=response.board_key == request.board_key and response.move in request.legal_moves,
            message="fake provider completed test request",
        )
