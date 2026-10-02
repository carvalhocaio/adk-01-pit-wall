from datetime import timedelta

import pytest

from adk_01_pit_wall.f1 import Constructor, Driver, FastestLap, RaceResult
from adk_01_pit_wall.models import Duration, FastestLapEntry, ResultEntry
from adk_01_pit_wall.tools import InvalidToolArgsError, PitWallTools

from .support import FakeRaceData

VERSTAPPEN_WIN = RaceResult(
    position=1,
    driver=Driver(id="max_verstappen", code="VER", name="Max Verstappen"),
    constructor=Constructor(id="red_bull", name="Red Bull"),
    grid=17,
    laps=69,
    status="Finished",
    points=26,
    fastest_lap=FastestLap(rank=1, lap=67, time=timedelta(milliseconds=80472)),
)


@pytest.mark.parametrize(
    ("round_", "circuit_id", "expected_lookups"),
    [
        pytest.param(21, None, [], id="by round skips lookup"),
        pytest.param(None, " interlagos ", [(2024, "interlagos")], id="by circuit"),
    ],
)
async def test_get_race_results_resolves_race(round_, circuit_id, expected_lookups):
    source = FakeRaceData(results=[VERSTAPPEN_WIN])

    report = await PitWallTools(source).get_race_results(
        2024, round=round_, circuit_id=circuit_id
    )

    assert source.lookups == expected_lookups
    assert report.race.date == "2024-11-03"
    assert report.results == [
        ResultEntry(
            position=1,
            driver_id="max_verstappen",
            driver_code="VER",
            driver_name="Max Verstappen",
            constructor="Red Bull",
            grid=17,
            laps=69,
            status="Finished",
            points=26,
            fastest_lap=FastestLapEntry(
                rank=1, lap=67, time=Duration(millis=80472, display="1:20.472")
            ),
        )
    ]


@pytest.mark.parametrize(
    ("season", "round_", "circuit_id"),
    [
        pytest.param(2024, None, None, id="neither round nor circuit"),
        pytest.param(2024, 21, "interlagos", id="both round and circuit"),
        pytest.param(2024, None, "   ", id="blank circuit"),
        pytest.param(2024, 0, None, id="non-positive round"),
        pytest.param(1949, 1, None, id="season before 1950"),
    ],
)
async def test_get_race_results_rejects_invalid_race_reference(
    season, round_, circuit_id
):
    with pytest.raises(InvalidToolArgsError):
        await PitWallTools(FakeRaceData()).get_race_results(
            season, round=round_, circuit_id=circuit_id
        )


async def test_get_race_results_omits_missing_fastest_lap():
    retired = RaceResult(
        position=20,
        driver=Driver(id="albon", code="ALB", name="Alexander Albon"),
        constructor=Constructor(id="williams", name="Williams"),
        grid=0,
        laps=0,
        status="Did not start",
        points=0,
    )

    report = await PitWallTools(FakeRaceData(results=[retired])).get_race_results(
        2024, round=21
    )

    assert "fastest_lap" not in report.model_dump(exclude_none=True)["results"][0]
