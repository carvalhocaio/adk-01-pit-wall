import pytest

from adk_01_pit_wall.f1 import StintNotFoundError
from adk_01_pit_wall.models import Duration, StintPace
from adk_01_pit_wall.tools import InvalidToolArgsError, PitWallTools

from .support import FakeRaceData, grid


async def compare(source: FakeRaceData, *drivers: str, stint: str = "final"):
    return await PitWallTools(source).compare_lap_times(
        2024, list(drivers), circuit_id="interlagos", stint=stint
    )


async def test_compare_final_stint():
    comparison = await compare(grid(), "norris", "max_verstappen")

    assert (comparison.round, comparison.stint, comparison.fastest_driver_id) == (
        21,
        "final",
        "max_verstappen",
    )
    assert comparison.drivers[1].stints == [
        StintPace(
            stint=2,
            first_lap=4,
            last_lap=8,
            laps=5,
            clean_laps=4,
            best_lap=5,
            best=Duration(millis=71200, display="1:11.200"),
            median=Duration(millis=71350, display="1:11.350"),
            mean=Duration(millis=71475, display="1:11.475"),
        )
    ]


async def test_compare_all_stints_has_no_fastest_driver():
    comparison = await compare(grid(), "norris", "max_verstappen", stint="all")

    assert comparison.fastest_driver_id is None
    assert [len(driver.stints) for driver in comparison.drivers] == [2, 2]


async def test_compare_stint_without_clean_laps_omits_pace():
    comparison = await compare(grid(), "hamilton", stint="2")

    payload = comparison.model_dump(exclude_none=True)

    assert payload["stint"] == "2"
    assert payload["drivers"][0]["stints"] == [
        {"stint": 2, "first_lap": 3, "last_lap": 3, "laps": 1, "clean_laps": 0}
    ]
    assert "fastest_driver_id" not in payload


async def test_compare_normalizes_drivers():
    comparison = await compare(grid(), " Norris ", "norris", "", "MAX_VERSTAPPEN")

    assert [driver.driver_id for driver in comparison.drivers] == [
        "norris",
        "max_verstappen",
    ]


@pytest.mark.parametrize(
    ("drivers", "stint"),
    [
        pytest.param([], "final", id="no drivers"),
        pytest.param(
            ["norris", "piastri", "leclerc", "sainz", "russell"],
            "final",
            id="too many drivers",
        ),
        pytest.param(["norris"], "last", id="unknown stint selector"),
    ],
)
async def test_compare_rejects_invalid_args(drivers, stint):
    with pytest.raises(InvalidToolArgsError):
        await compare(grid(), *drivers, stint=stint)


async def test_compare_surfaces_missing_stint():
    with pytest.raises(StintNotFoundError):
        await compare(grid(), "norris", stint="3")


async def test_compare_surfaces_source_failure_without_exception_group():
    source = grid()
    source.failure = ConnectionError("jolpica unavailable")

    with pytest.raises(ConnectionError, match="jolpica unavailable"):
        await compare(source, "norris", "max_verstappen")
