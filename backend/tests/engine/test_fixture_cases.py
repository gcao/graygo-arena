from pathlib import Path

import pytest

from graygo_arena.engine import Board, TurnResolution, resolve_turn
from graygo_arena.engine.fixtures import EngineCase, load_engine_cases

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "engine_cases.json"
ENGINE_CASES = load_engine_cases(FIXTURE_PATH)


@pytest.mark.parametrize("case", ENGINE_CASES, ids=lambda case: case.name)
def test_fixture_cases(case: EngineCase) -> None:
    assert Board.from_key(case.state.board.to_key()).to_key() == case.state.board.to_key()

    resolution = resolve_turn(case.state, case.black_move, case.white_move)

    assert resolution.post_board_key == case.post_board_key
    actual_event_types = _event_types(resolution)
    assert resolution.game_finished is ("game_finished" in case.expected_event_types)
    for event_type in case.expected_event_types:
        assert event_type in actual_event_types


def _event_types(resolution: TurnResolution) -> tuple[str, ...]:
    event_types = [event.event_type for event in resolution.placement_events]
    event_types.extend("capture" for _ in resolution.captures)
    event_types.extend("forbidden_update" for _ in resolution.forbidden_updates)
    if resolution.game_finished:
        event_types.append("game_finished")
    return tuple(event_types)
