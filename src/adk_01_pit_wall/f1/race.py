from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Race:
    season: int
    round: int
    name: str
    circuit_id: str
    circuit: str
    date: date


@dataclass(frozen=True, slots=True)
class Driver:
    id: str
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class Constructor:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class RaceResult:
    position: int
    driver: Driver
    constructor: Constructor
    grid: int
    laps: int
    status: str
    points: float


@dataclass(frozen=True, slots=True)
class DriverStanding:
    position: int
    driver: Driver
    constructors: tuple[Constructor, ...]
    points: float
    wins: int
