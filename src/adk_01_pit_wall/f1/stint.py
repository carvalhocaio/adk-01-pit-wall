from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from .errors import InvalidStintSelectorError, NoLapsError, StintNotFoundError


@dataclass(frozen=True, slots=True)
class Lap:
    number: int
    position: int
    time: timedelta


@dataclass(frozen=True, slots=True)
class Stint:
    number: int
    laps: tuple[Lap, ...]
    in_lap: bool = False
    out_lap: bool = False

    @property
    def first_lap(self) -> int:
        return self.laps[0].number

    @property
    def last_lap(self) -> int:
        return self.laps[-1].number

    @property
    def clean_laps(self) -> tuple[Lap, ...]:
        start = 1 if self.out_lap else 0
        end = len(self.laps) - 1 if self.in_lap else len(self.laps)
        return self.laps[start:end]


def split_stints(laps: Iterable[Lap], pit_laps: Iterable[int]) -> tuple[Stint, ...]:
    ordered = sorted(laps, key=lambda lap: lap.number)
    if not ordered:
        raise NoLapsError("no laps recorded")
    boundaries = frozenset(pit_laps)

    stints: list[Stint] = []
    current: list[Lap] = []
    for lap in ordered:
        current.append(lap)
        if lap.number in boundaries:
            stints.append(_stint(len(stints) + 1, current, in_lap=True))
            current = []
    if current:
        stints.append(_stint(len(stints) + 1, current, in_lap=False))
    return tuple(stints)


def _stint(number: int, laps: list[Lap], *, in_lap: bool) -> Stint:
    return Stint(number=number, laps=tuple(laps), in_lap=in_lap, out_lap=number > 1)


class StintScope(StrEnum):
    FINAL = "final"
    ALL = "all"
    NUMBER = "number"


@dataclass(frozen=True, slots=True)
class StintSelector:
    scope: StintScope
    number: int = 0

    @classmethod
    def parse(cls, raw: str | None) -> "StintSelector":
        value = (raw or "").strip().lower()
        if value in ("", StintScope.FINAL):
            return cls(StintScope.FINAL)
        if value == StintScope.ALL:
            return cls(StintScope.ALL)
        if value.isdigit() and int(value) >= 1:
            return cls(StintScope.NUMBER, int(value))
        raise InvalidStintSelectorError(
            f'invalid stint selector {raw!r}: use "final", "all" '
            "or a positive stint number"
        )

    def select(self, stints: tuple[Stint, ...]) -> tuple[Stint, ...]:
        if not stints:
            raise NoLapsError("no stints to select from")
        match self.scope:
            case StintScope.ALL:
                return stints
            case StintScope.FINAL:
                return stints[-1:]
            case StintScope.NUMBER:
                if self.number > len(stints):
                    raise StintNotFoundError(
                        f"stint {self.number} requested, driver ran {len(stints)}"
                    )
                return stints[self.number - 1 : self.number]
