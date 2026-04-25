from graygo_arena.application.models import ProviderMoveRequest, SeatSession
from graygo_arena.providers.fake import FakeRandomProvider, ScriptedSequenceProvider
from graygo_arena.providers.registry import ProviderCatalog


def request(turn_index: int = 0) -> ProviderMoveRequest:
    return ProviderMoveRequest(
        game_id="game_1",
        seat_session_id="seat_1",
        color="black",
        model="default",
        board_key="+++/+++/+++",
        board_rows=("+++", "+++", "+++"),
        legal_moves=("a1", "a2", "b2", "PASS"),
        public_history=(),
        private_history=(),
        turn_index=turn_index,
    )


def seat(seat_id: str, script: tuple[str, ...] = ()) -> SeatSession:
    return SeatSession(
        id=seat_id,
        game_id="game_1",
        color="black",
        provider="scripted_sequence",
        model="default",
        credential_ref="fake",
        script=script,
    )


def test_provider_catalog_lists_safe_metadata_without_secrets() -> None:
    catalog = ProviderCatalog()

    providers = catalog.list_providers()

    assert {provider.id for provider in providers} >= {
        "fake_random",
        "scripted_center",
        "scripted_pass",
        "scripted_sequence",
    }
    fake_providers = [provider for provider in providers if provider.id.startswith("scripted")]
    fake_providers.append(next(provider for provider in providers if provider.id == "fake_random"))
    assert all(provider.auth_type == "none" for provider in fake_providers)
    assert "secret" not in repr(providers).lower()
    assert "token" not in repr(providers).lower()


def test_provider_health_test_uses_fake_adapter_without_network() -> None:
    result = ProviderCatalog().test_provider("scripted_center", "default")

    assert result.ok is True
    assert result.provider == "scripted_center"


def test_fake_random_is_deterministic_per_seat_and_turn() -> None:
    provider = FakeRandomProvider(seed=42)
    first = provider.request_move(request(turn_index=1), seat("seat_black"))
    second = provider.request_move(request(turn_index=1), seat("seat_black"))
    other_turn = provider.request_move(request(turn_index=2), seat("seat_black"))

    assert first == second
    assert first.move in request().legal_moves
    assert other_turn.move in request().legal_moves


def test_scripted_sequence_uses_seat_local_state() -> None:
    provider = ScriptedSequenceProvider()
    black = seat("seat_black", ("a1", "a2"))
    white = seat("seat_white", ("b2", "PASS"))

    assert provider.request_move(request(), black).move == "a1"
    assert provider.request_move(request(), white).move == "b2"
    assert provider.request_move(request(turn_index=1), black).move == "a2"
    assert provider.request_move(request(turn_index=1), white).move == "PASS"


def test_scripted_sequence_falls_back_when_scripted_move_is_illegal() -> None:
    provider = ScriptedSequenceProvider()

    response = provider.request_move(request(), seat("seat_black", ("z9",)))

    assert response.move == "PASS"
