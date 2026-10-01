from dataclasses import dataclass, field
from datetime import date, timedelta

from adk_01_pit_wall.f1 import DriverStanding, Lap, NoLapsError, Race, RaceResult

INTERLAGOS_2024 = Race(
    season=2024,
    round=21,
    name="São Paulo Grand Prix",
    circuit_id="interlagos",
    circuit="Autódromo José Carlos Pace",
    date=date(2024, 11, 3),
)


def laps_from_millis(*millis: int) -> list[Lap]:
    return [
        Lap(number=n, position=1, time=timedelta(milliseconds=ms))
        for n, ms in enumerate(millis, start=1)
    ]


@dataclass(frozen=True)
class DriverRace:
    laps: list[Lap]
    pit_laps: list[int]


@dataclass
class FakeRaceData:
    results: list[RaceResult] = field(default_factory=list)
    standings: list[DriverStanding] = field(default_factory=list)
    drivers: dict[str, DriverRace] = field(default_factory=dict)
    failure: Exception | None = None
    lookups: list[tuple[int, str]] = field(default_factory=list)
    standings_rounds: list[int | None] = field(default_factory=list)

    async def find_race(self, season: int, circuit_id: str) -> Race:
        self.lookups.append((season, circuit_id))
        return INTERLAGOS_2024

    async def race_results(
        self, season: int, round_: int
    ) -> tuple[Race, list[RaceResult]]:
        return INTERLAGOS_2024, self.results

    async def driver_standings(
        self, season: int, after_round: int | None = None
    ) -> tuple[int, list[DriverStanding]]:
        self.standings_rounds.append(after_round)
        return 21, self.standings

    async def driver_laps(self, season: int, round_: int, driver_id: str) -> list[Lap]:
        if self.failure is not None:
            raise self.failure
        if driver_id not in self.drivers:
            raise NoLapsError(f"no laps for {driver_id}")
        return self.drivers[driver_id].laps

    async def driver_pit_laps(
        self, season: int, round_: int, driver_id: str
    ) -> list[int]:
        return self.drivers[driver_id].pit_laps


def grid() -> FakeRaceData:
    return FakeRaceData(
        drivers={
            "norris": DriverRace(
                laps=laps_from_millis(
                    80000, 72000, 72100, 90000, 95000, 71500, 71600, 71700
                ),
                pit_laps=[4],
            ),
            "max_verstappen": DriverRace(
                laps=laps_from_millis(
                    81000, 72500, 89000, 94000, 71200, 71400, 71300, 72000
                ),
                pit_laps=[3],
            ),
            "hamilton": DriverRace(
                laps=laps_from_millis(80000, 88000, 93000, 72000, 72100),
                pit_laps=[2, 3],
            ),
        }
    )
