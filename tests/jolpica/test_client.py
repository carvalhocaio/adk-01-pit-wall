import asyncio
from datetime import date, timedelta

import httpx
import pytest

from adk_01_pit_wall.f1 import (
    Constructor,
    Driver,
    FastestLap,
    Lap,
    NoLapsError,
    Race,
    RaceResult,
)
from adk_01_pit_wall.jolpica import (
    MalformedResponseError,
    RaceNotFoundError,
    RateLimitedError,
    UnexpectedStatusError,
)

from .support import ClientFactory, CountingLimiter, fixture_routes

INTERLAGOS_2024 = Race(
    season=2024,
    round=21,
    name="São Paulo Grand Prix",
    circuit_id="interlagos",
    circuit="Autódromo José Carlos Pace",
    date=date(2024, 11, 3),
)


async def test_find_race(make_client: ClientFactory):
    client = make_client(
        fixture_routes({"2024/circuits/interlagos/races/?offset=0": "find_race.json"})
    )

    assert await client.find_race(2024, "interlagos") == INTERLAGOS_2024


async def test_find_race_not_found(make_client: ClientFactory):
    client = make_client(
        fixture_routes(
            {"2024/circuits/monza_street/races/?offset=0": "find_race_empty.json"}
        )
    )

    with pytest.raises(RaceNotFoundError):
        await client.find_race(2024, "monza_street")


async def test_race_results(make_client: ClientFactory):
    client = make_client(fixture_routes({"2024/21/results/?offset=0": "results.json"}))

    race, results = await client.race_results(2024, 21)

    assert race == INTERLAGOS_2024
    assert len(results) == 2
    assert results[0] == RaceResult(
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
    ("after_round", "route"),
    [
        pytest.param(21, "2024/21/driverstandings/?offset=0", id="after round"),
        pytest.param(None, "2024/driverstandings/?offset=0", id="latest"),
    ],
)
async def test_driver_standings(make_client: ClientFactory, after_round, route):
    client = make_client(fixture_routes({route: "standings.json"}))

    round_, standings = await client.driver_standings(2024, after_round)

    leader = standings[0]
    assert round_ == 21
    assert (leader.driver.id, leader.points, leader.wins) == ("max_verstappen", 393, 8)


async def test_driver_laps_follow_pagination(
    make_client: ClientFactory, limiter: CountingLimiter
):
    client = make_client(
        fixture_routes(
            {
                "2024/21/drivers/norris/laps/?offset=0": "laps_norris_page1.json",
                "2024/21/drivers/norris/laps/?offset=2": "laps_norris_page2.json",
            }
        )
    )

    laps = await client.driver_laps(2024, 21, "norris")

    assert laps == [
        Lap(number=1, position=2, time=timedelta(milliseconds=91803)),
        Lap(number=2, position=2, time=timedelta(milliseconds=86207)),
        Lap(number=3, position=1, time=timedelta(milliseconds=85918)),
    ]
    assert limiter.acquired == 2


async def test_driver_laps_without_data(make_client: ClientFactory):
    client = make_client(
        fixture_routes(
            {"2024/21/drivers/norris/laps/?offset=0": "find_race_empty.json"}
        )
    )

    with pytest.raises(NoLapsError):
        await client.driver_laps(2024, 21, "norris")


async def test_driver_pit_laps(make_client: ClientFactory):
    client = make_client(
        fixture_routes(
            {"2024/21/drivers/norris/pitstops/?offset=0": "pitstops_norris.json"}
        )
    )

    assert await client.driver_pit_laps(2024, 21, "norris") == [28, 32]


@pytest.mark.parametrize(
    ("response", "error"),
    [
        pytest.param(httpx.Response(429), RateLimitedError, id="rate limited"),
        pytest.param(httpx.Response(502), UnexpectedStatusError, id="server error"),
        pytest.param(
            httpx.Response(200, json={"unexpected": True}),
            MalformedResponseError,
            id="malformed payload",
        ),
    ],
)
async def test_response_errors(make_client: ClientFactory, response, error):
    client = make_client(lambda _: response)

    with pytest.raises(error):
        await client.race_results(2024, 21)


async def test_path_segments_are_escaped(make_client: ClientFactory):
    seen: list[str] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.raw_path.decode().split("?", 1)[0])
        return httpx.Response(404)

    client = make_client(record)

    with pytest.raises(UnexpectedStatusError):
        await client.driver_laps(2024, 21, "norris/../../results")

    assert seen == ["/ergast/f1/2024/21/drivers/norris%2F..%2F..%2Fresults/laps/"]


async def test_client_serves_concurrent_tool_calls(
    make_client: ClientFactory, limiter: CountingLimiter
):
    client = make_client(
        fixture_routes(
            {
                "2024/21/results/?offset=0": "results.json",
                "2024/21/driverstandings/?offset=0": "standings.json",
                "2024/21/drivers/norris/pitstops/?offset=0": "pitstops_norris.json",
            }
        )
    )

    await asyncio.gather(
        client.race_results(2024, 21),
        client.driver_standings(2024, 21),
        client.driver_pit_laps(2024, 21, "norris"),
    )

    assert limiter.acquired == 3
