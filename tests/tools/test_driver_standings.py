import pytest

from adk_01_pit_wall.f1 import Constructor, Driver, DriverStanding
from adk_01_pit_wall.tools import InvalidToolArgsError, PitWallTools

from .support import FakeRaceData


async def test_get_driver_standings():
    source = FakeRaceData(
        standings=[
            DriverStanding(
                position=1,
                driver=Driver(id="max_verstappen", code="VER", name="Max Verstappen"),
                constructors=(Constructor(id="red_bull", name="Red Bull"),),
                points=393,
                wins=8,
            )
        ]
    )

    report = await PitWallTools(source).get_driver_standings(2024, after_round=21)

    leader = report.standings[0]
    assert source.standings_rounds == [21]
    assert report.round == 21
    assert (leader.driver_id, leader.constructors, leader.points) == (
        "max_verstappen",
        ["Red Bull"],
        393,
    )


async def test_get_driver_standings_rejects_pre_championship_season():
    with pytest.raises(InvalidToolArgsError):
        await PitWallTools(FakeRaceData()).get_driver_standings(1949)
