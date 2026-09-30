from datetime import timedelta

import pytest

from adk_01_pit_wall.f1 import (
    DriverPace,
    Lap,
    NoLapsError,
    Pace,
    Stint,
    fastest,
    measure_pace,
)

from .factories import timed_laps


def test_measure_pace_ignores_in_and_out_laps():
    stint = Stint(
        number=2,
        laps=timed_laps(95000, 72300, 72100, 72600, 90000),
        in_lap=True,
        out_lap=True,
    )

    assert measure_pace(stint) == Pace(
        lap_count=5,
        clean_laps=3,
        best=stint.laps[2],
        median=timedelta(milliseconds=72300),
        mean=timedelta(microseconds=72333333),
    )


def test_measure_pace_even_count_median():
    pace = measure_pace(Stint(number=1, laps=timed_laps(72000, 73000, 74000, 71000)))

    assert pace.median == timedelta(milliseconds=72500)


def test_measure_pace_without_clean_laps():
    stint = Stint(number=2, laps=timed_laps(95000, 90000), in_lap=True, out_lap=True)

    with pytest.raises(NoLapsError):
        measure_pace(stint)


def driver_pace(driver_id: str, median_ms: int, best_ms: int) -> DriverPace:
    best = Lap(number=1, position=1, time=timedelta(milliseconds=best_ms))
    return DriverPace(
        driver_id=driver_id,
        stint=Stint(number=1, laps=(best,)),
        pace=Pace(
            lap_count=1,
            clean_laps=1,
            best=best,
            median=timedelta(milliseconds=median_ms),
            mean=timedelta(milliseconds=median_ms),
        ),
    )


def test_fastest_uses_median_pace():
    paces = [
        driver_pace("norris", median_ms=72400, best_ms=71000),
        driver_pace("max_verstappen", median_ms=72100, best_ms=71900),
    ]

    result = fastest(paces)

    assert result is not None
    assert result.driver_id == "max_verstappen"


def test_fastest_without_drivers():
    assert fastest([]) is None
