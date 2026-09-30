import pytest

from adk_01_pit_wall.f1 import (
    InvalidStintSelectorError,
    NoLapsError,
    StintNotFoundError,
    StintSelector,
    split_stints,
)

from .factories import laps_of


@pytest.mark.parametrize(
    ("laps", "pit_laps", "expected"),
    [
        pytest.param(laps_of(10), [], [(1, 10)], id="no stops"),
        pytest.param(laps_of(10), [4], [(1, 4), (5, 10)], id="one stop"),
        pytest.param(
            list(reversed(laps_of(10))),
            [7, 3],
            [(1, 3), (4, 7), (8, 10)],
            id="unsorted input",
        ),
        pytest.param(laps_of(5), [5], [(1, 5)], id="stop on last lap"),
    ],
)
def test_split_stints(laps, pit_laps, expected):
    stints = split_stints(laps, pit_laps)

    assert [(s.first_lap, s.last_lap) for s in stints] == expected


def test_split_stints_without_laps():
    with pytest.raises(NoLapsError):
        split_stints([], [])


def test_clean_laps_drop_in_and_out_laps():
    stints = split_stints(laps_of(12), [4, 8])

    clean_ranges = [(s.clean_laps[0].number, s.clean_laps[-1].number) for s in stints]

    assert clean_ranges == [(1, 3), (6, 7), (10, 12)]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, [3]),
        ("", [3]),
        ("Final", [3]),
        ("all", [1, 2, 3]),
        (" 2 ", [2]),
    ],
)
def test_stint_selector_selects(raw, expected):
    stints = split_stints(laps_of(12), [4, 8])

    selected = StintSelector.parse(raw).select(stints)

    assert [s.number for s in selected] == expected


@pytest.mark.parametrize("raw", ["0", "last", "-1", "2.5"])
def test_stint_selector_rejects_invalid_input(raw):
    with pytest.raises(InvalidStintSelectorError):
        StintSelector.parse(raw)


def test_stint_selector_reports_missing_stint():
    stints = split_stints(laps_of(12), [4, 8])

    with pytest.raises(StintNotFoundError, match="driver ran 3"):
        StintSelector.parse("4").select(stints)
