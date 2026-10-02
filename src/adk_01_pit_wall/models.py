from datetime import timedelta
from typing import Self

from pydantic import BaseModel, ConfigDict

from .f1 import Pace, Race, Stint


class _Output(BaseModel):
    model_config = ConfigDict(frozen=True)


class Duration(_Output):
    millis: int
    display: str

    @classmethod
    def of(cls, value: timedelta) -> Self:
        millis = (value // timedelta(microseconds=1) + 500) // 1000
        minutes, rest = divmod(millis, 60_000)
        seconds, fraction = divmod(rest, 1000)
        return cls(millis=millis, display=f"{minutes}:{seconds:02d}.{fraction:03d}")


class RaceSummary(_Output):
    season: int
    round: int
    name: str
    circuit_id: str
    circuit: str
    date: str

    @classmethod
    def of(cls, race: Race) -> Self:
        return cls(
            season=race.season,
            round=race.round,
            name=race.name,
            circuit_id=race.circuit_id,
            circuit=race.circuit,
            date=race.date.isoformat(),
        )


class FastestLapEntry(_Output):
    rank: int
    lap: int
    time: Duration


class ResultEntry(_Output):
    position: int
    driver_id: str
    driver_code: str
    driver_name: str
    constructor: str
    grid: int
    laps: int
    status: str
    points: float
    fastest_lap: FastestLapEntry | None = None


class RaceResultsReport(_Output):
    race: RaceSummary
    results: list[ResultEntry]


class StandingEntry(_Output):
    position: int
    driver_id: str
    driver_name: str
    constructors: list[str]
    points: float
    wins: int


class StandingsReport(_Output):
    season: int
    round: int
    standings: list[StandingEntry]


class StintPace(_Output):
    stint: int
    first_lap: int
    last_lap: int
    laps: int
    clean_laps: int
    best_lap: int | None = None
    best: Duration | None = None
    median: Duration | None = None
    mean: Duration | None = None

    @classmethod
    def of(cls, stint: Stint, pace: Pace | None) -> Self:
        base = cls(
            stint=stint.number,
            first_lap=stint.first_lap,
            last_lap=stint.last_lap,
            laps=len(stint.laps),
            clean_laps=pace.clean_laps if pace else 0,
        )
        if pace is None:
            return base
        return base.model_copy(
            update={
                "best_lap": pace.best.number,
                "best": Duration.of(pace.best.time),
                "median": Duration.of(pace.median),
                "mean": Duration.of(pace.mean),
            }
        )


class DriverStints(_Output):
    driver_id: str
    pit_laps: list[int]
    stints: list[StintPace]


class LapComparison(_Output):
    season: int
    round: int
    stint: str
    drivers: list[DriverStints]
    fastest_driver_id: str | None = None
