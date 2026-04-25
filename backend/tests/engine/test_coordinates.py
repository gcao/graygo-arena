import pytest

from graygo_arena.engine import Coordinate


def test_coordinate_parse_uses_zero_based_indexes() -> None:
    assert Coordinate.parse("d4", size=7) == Coordinate(row=3, col=3)


def test_coordinate_renders_label() -> None:
    assert Coordinate(row=6, col=6).to_label() == "g7"


@pytest.mark.parametrize("value", ["", "A1", "a0", "a8", "h1", "aa", "1a"])
def test_coordinate_rejects_malformed_or_out_of_range_labels(value: str) -> None:
    with pytest.raises(ValueError):
        Coordinate.parse(value, size=7)
