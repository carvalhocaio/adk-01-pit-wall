import asyncio
from typing import Annotated, Protocol

from pydantic import Field

from .f1 import (
    DriverPace,
    DriverStanding,
    InvalidStintSelectorError,
    Lap,
    NoLapsError,
    Pace,
    Race,
    RaceResult,
    Stint,
    StintScope,
    StintSelector,
    fastest,
    measure_pace,
    split_stints,
)
from .models import (
    DriverStints,
    LapComparison,
    RaceResultsReport,
    RaceSummary,
    ResultEntry,
    StandingEntry,
    StandingsReport,
    StintPace,
)

FIRST_CHAMPIONSHIP = 1950
MAX_COMPARED_DRIVERS = 4

Season = Annotated[
    int,
    Field(description="Championship year, for example 2024.", ge=FIRST_CHAMPIONSHIP),
]
Round = Annotated[
    int | None,
    Field(
        description=(
            "Round number within the season. Provide either round or circuit_id, "
            "never both."
        ),
        ge=1,
    ),
]
CircuitId = Annotated[
    str | None,
    Field(
        description=(
            "Ergast circuit id, for example interlagos, monza, silverstone or "
            "red_bull_ring. Provide either round or circuit_id, never both,"
        )
    ),
]


class InvalidToolArgsError(ValueError):
    pass


class RaceDataSource(Protocol):
    async def find_race(self, season: int, circuit_id: str) -> Race: ...

    async def race_results(
        self, season: int, round_: int
    ) -> tuple[Race, list[RaceResult]]: ...

    async def driver_standings(
        self, season: int, after_round: int | None = None
    ) -> tuple[int, list[DriverStanding]]: ...

    async def driver_laps(
        self, season: int, round_: int, driver_id: str
    ) -> list[Lap]: ...

    async def driver_pit_laps(
        self, season: int, round_: int, driver_id: str
    ) -> list[int]: ...


class PitWallTools:
    def __init__(self, source: RaceDataSource) -> None:
        self._source = source

    async def get_race_results(
        self,
        season: Season,
        round: Round = None,
        circuit_id: CircuitId = None,
    ) -> RaceResultsReport:
        """Returns the official classification of a Formula 1 Grand Prix.

        Each entry has the finishing position, driver id, team, grid slot, laps
        completed, status and points. A grid of 0 means a pit lane start. Call
        it first whenever you need driver ids for compare_lap_times or need to
        know who finished where.
        """
        round_ = await self._resolve_round(season, round, circuit_id)
        race, results = await self._source.race_results(season, round_)
        return RaceResultsReport(
            race=RaceSummary.of(race),
            results=[_result_entry(result) for result in results],
        )

    async def get_driver_standings(
        self,
        season: Season,
        after_round: Annotated[
            int | None,
            Field(
                description=(
                    "Return the standings as they were after this round. Omit it "
                    "for the latest standings of the season."
                ),
                ge=1,
            ),
        ] = None,
    ) -> StandingsReport:
        """Returns the Formula 1 driver's championship standings for a season.

        Use it for questions about championship points, positions or number of
        wins, either for the latest standings or as they stood after a round.
        A position of 0 means the driver is unclassified.
        """
        _require_season(season)
        round_, standings = await self._source.driver_standings(season, after_round)
        return StandingsReport(
            season=season,
            round=round_,
            standings=[_standing_entry(standing) for standing in standings],
        )

    async def compare_lap_times(
        self,
        season: Season,
        drivers: Annotated[
            list[str],
            Field(
                description=(
                    "Ergast driver ids to compare, between 1 and 4, for example "
                    "max_verstappen, norris or hamilton. Use get_race_results to "
                    "discover them."
                )
            ),
        ],
        round: Round = None,
        circuit_id: CircuitId = None,
        stint: Annotated[
            str,
            Field(
                description=(
                    "Which stint to analyse: final (default), all, or a stint "
                    "number such as 2."
                )
            ),
        ] = StintScope.FINAL,
    ) -> LapComparison:
        """Compares race pace between drivers in a single Grand Prix.

        Laps are split into stints at pit stop laps; red flag stoppages can show
        up as pit stops. Pace only uses clean laps, excluding pit in-laps and
        out-laps, and the median clean lap decides the fastest driver because
        it resists safety car laps. When clean_laps is 0 the pace fields are
        ommited. fastest_driver_id is ommited when stint is all. Race laps only,
        never qualifying or practice.
        """
        driver_ids = _normalize_drivers(drivers)
        try:
            selector = StintSelector.parse(stint)
        except InvalidStintSelectorError as exc:
            raise InvalidToolArgsError(str(exc)) from exc
        round_ = await self._resolve_round(season, round, circuit_id)

        try:
            async with asyncio.TaskGroup() as group:
                tasks = [
                    group.create_task(self._driver_stints(season, round_, driver_id))
                    for driver_id in driver_ids
                ]
        except ExceptionGroup as failures:
            raise failures.exceptions[0] from failures

        compared: list[DriverStints] = []
        candidates: list[DriverPace] = []
        for driver_id, task in zip(driver_ids, tasks, strict=True):
            stints, pit_laps = task.result()
            selected = selector.select(stints)
            paces = [(s, _measure(s)) for s in selected]
            compared.append(
                DriverStints(
                    driver_id=driver_id,
                    pit_laps=pit_laps,
                    stints=[StintPace.of(s, pace) for s, pace in paces],
                )
            )
            candidates.extend(
                DriverPace(driver_id=driver_id, stint=s, pace=pace)
                for s, pace in paces
                if pace is not None
            )

        leader = fastest(candidates) if selector.scope != StintScope.ALL else None
        return LapComparison(
            season=season,
            round=round_,
            stint=_selector_label(selector),
            drivers=compared,
            fastest_driver_id=leader.driver_id if leader else None,
        )

    async def _resolve_round(
        self, season: int, round_: int | None, circuit_id: str | None
    ) -> int:
        _require_season(season)
        circuit = (circuit_id or "").strip()
        if (round_ is None) == (not circuit):
            raise InvalidToolArgsError("provide exactly one of round or circuit_id")
        if round_ is not None:
            if round_ < 1:
                raise InvalidToolArgsError(f"round must be positive, got {round_}")
            return round_
        race = await self._source.find_race(season, circuit)
        return race.round

    async def _driver_stints(
        self, season: int, round_: int, driver_id: str
    ) -> tuple[tuple[Stint, ...], list[int]]:
        laps = await self._source.driver_laps(season, round_, driver_id)
        pit_laps = await self._source.driver_pit_laps(season, round_, driver_id)
        return split_stints(laps, pit_laps), pit_laps


def _require_season(season: int) -> None:
    if season < FIRST_CHAMPIONSHIP:
        raise InvalidToolArgsError(
            f"season {season} is before the first championship ({FIRST_CHAMPIONSHIP})"
        )


def _normalize_drivers(raw: list[str]) -> list[str]:
    drivers = list(dict.fromkeys(d.strip().lower() for d in raw if d.strip()))
    if not 1 <= len(drivers) <= MAX_COMPARED_DRIVERS:
        raise InvalidToolArgsError(
            f"compare between 1 and {MAX_COMPARED_DRIVERS} distinct drivers, "
            f"got {len(drivers)}"
        )
    return drivers


def _selector_label(selector: StintSelector) -> str:
    if selector.scope == StintScope.NUMBER:
        return str(selector.number)
    return selector.scope


def _measure(stint: Stint) -> Pace | None:
    try:
        return measure_pace(stint)
    except NoLapsError:
        return None


def _result_entry(result: RaceResult) -> ResultEntry:
    return ResultEntry(
        position=result.position,
        driver_id=result.driver.id,
        driver_code=result.driver.code,
        driver_name=result.driver.name,
        constructor=result.constructor.name,
        grid=result.grid,
        laps=result.laps,
        status=result.status,
        points=result.points,
    )


def _standing_entry(standing: DriverStanding) -> StandingEntry:
    return StandingEntry(
        position=standing.position,
        driver_id=standing.driver.id,
        driver_name=standing.driver.name,
        constructors=[c.name for c in standing.constructors],
        points=standing.points,
        wins=standing.wins,
    )
