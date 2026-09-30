from datetime import timedelta

from adk_01_pit_wall.f1 import Lap


def laps_of(count: int) -> list[Lap]:
    return [
        Lap(number=n, position=1, time=timedelta(seconds=72))
        for n in range(1, count + 1)
    ]


def timed_laps(*millis: int) -> tuple[Lap, ...]:
    return tuple(
        Lap(number=n, position=1, time=timedelta(milliseconds=ms))
        for n, ms in enumerate(millis, start=1)
    )
