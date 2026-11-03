import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from graygo_arena.application.models import ProviderMoveRequest, PublicRuleRound, SeatSession
from graygo_arena.engine.moves import SeatColor
from graygo_arena.providers.direct import ProviderServiceError
from graygo_arena.providers.nfsp_model import ExperimentalNfspProvider, rule_state


def seat(color: SeatColor = "black") -> SeatSession:
    return SeatSession(
        "seat-" + color,
        "game",
        color,
        "graygo_nfsp_experimental",
        "avg-9x9-diagnostic-32k",
        "local",
    )


def request() -> ProviderMoveRequest:
    rows = tuple("+" * 9 for _ in range(9))
    return ProviderMoveRequest(
        "game",
        "seat-black",
        "black",
        "avg-9x9-diagnostic-32k",
        "/".join(rows),
        rows,
        ("a1", "b2", "PASS"),
        (),
        (),
        0,
    )


def provider(scores: Sequence[float]) -> ExperimentalNfspProvider:
    return ExperimentalNfspProvider(
        checkpoint=Path("/unused"),
        repo=Path("/unused"),
        python=Path("/unused"),
        runner=lambda state, player: scores,
    )


def test_actual_policy_controls_opening_and_pass_remains_selectable() -> None:
    scores = [-1000.0] * 82
    scores[81] = 1000.0
    result = provider(scores).request_move(request(), seat())
    assert result.move == "PASS"
    assert json.loads(result.raw_response)["strength_validated"] is False


def test_authoritative_legal_mask_excludes_occupied_or_forbidden_points() -> None:
    scores = [0.0] * 82
    scores[80] = 1000.0
    scores[0] = 999.0
    incoming = replace(request(), legal_moves=("b2",))
    assert provider(scores).request_move(incoming, seat()).move == "b2"


def test_retry_is_deterministic_and_only_public_state_reaches_the_runner() -> None:
    seen: list[tuple[dict[str, object], int]] = []

    def infer(state: dict[str, object], player: int) -> list[float]:
        seen.append((state, player))
        return [0.0] * 82

    model = ExperimentalNfspProvider(
        checkpoint=Path("/unused"), repo=Path("/unused"), python=Path("/unused"), runner=infer
    )
    incoming = replace(request(), private_history=("private sentinel",))
    one = model.request_move(incoming, seat())
    two = model.request_move(incoming, seat())
    assert one.move == two.move
    assert "private sentinel" not in json.dumps(seen)
    assert seen[0][1] == 1


def test_both_completed_history_slots_and_white_perspective_restrictions_are_preserved() -> None:
    incoming = request()
    history = (
        PublicRuleRound(incoming.board_rows, "a1", "b2"),
        PublicRuleRound(incoming.board_rows, "c3", "PASS"),
    )
    incoming = replace(
        incoming,
        seat_session_id="seat-white",
        color="white",
        turn_index=2,
        rule_history=history,
        own_forbidden=("d4",),
        opponent_forbidden=("e5",),
    )
    state = rule_state(incoming, seat("white"))
    assert state["forbidden_white"] == [30]
    assert state["forbidden_black"] == [40]
    history_rows = cast(list[dict[str, object]], state["history"])
    assert history_rows[0]["black"] == 0
    assert history_rows[1]["white"] == 81
    assert state["rounds_played"] == 2


def test_missing_history_or_wrong_shape_limit_and_nonfinite_logits_fail() -> None:
    with pytest.raises(ProviderServiceError):
        provider([0.0] * 82).request_move(replace(request(), turn_index=1), seat())
    with pytest.raises(ProviderServiceError):
        provider([0.0] * 82).request_move(replace(request(), max_turns=100), seat())
    with pytest.raises(ProviderServiceError):
        provider([0.0] * 82).request_move(replace(request(), board_rows=("+++",) * 3), seat())
    with pytest.raises(ProviderServiceError):
        provider([float("nan")] * 82).request_move(request(), seat())
    with pytest.raises(ProviderServiceError):
        provider([0.0] * 6).request_move(request(), seat())
