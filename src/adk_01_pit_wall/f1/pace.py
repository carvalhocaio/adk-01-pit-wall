import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from .errors import NoLapsError
from .stint import Lap, Stint


@dataclass(frozen=True, slots=True)
class Pace:
    lap_count: int
    clean_laps: int
    best: Lap
    median: timedelta
    mean: timedelta


@dataclass(frozen=True, slots=True)
class DriverPace:
    driver_id: str
    stint: Stint
    pace: Pace


def measure_pace(stint: Stint) -> Pace:
    clean = stint.clean_laps
    if not clean:
        raise NoLapsError(f"stint {stint.number} has no clean laps")
    times = [lap.time for lap in clean]
    return Pace(
        lap_count=len(stint.laps),
        clean_laps=len(clean),
        best=min(clean, key=lambda lap: lap.time),
        median=statistics.median(times),
        mean=sum(times, timedelta()) / len(times),
    )


def fastest(paces: Sequence[DriverPace]) -> DriverPace | None:
    return min(paces, key=lambda driver: driver.pace.median, default=None)
