from datetime import date, timedelta

from adk_01_pit_wall.f1 import (
    Constructor,
    Driver,
    DriverStanding,
    FastestLap,
    Lap,
    Race,
    RaceResult,
)

from .dto import (
    ConstructorDTO,
    DriverDTO,
    DriverStandingsDTO,
    FastestLapDTO,
    LapDTO,
    PitStopDTO,
    RaceDTO,
    ResultDTO,
)
from .errors import MalformedResponseError


def parse_lap_time(raw: str) -> timedelta:
    minutes, _, seconds = raw.rpartition(":")
    try:
        return timedelta(minutes=int(minutes or 0), seconds=float(seconds))
    except ValueError as exc:
        raise MalformedResponseError(f"invalid lap time {raw!r}") from exc


def to_race(dto: RaceDTO) -> Race:
    try:
        race_date = date.fromisoformat(dto.date)
    except ValueError as exc:
        raise MalformedResponseError(f"invalid race date {dto.date!r}") from exc
    return Race(
        season=dto.season,
        round=dto.round,
        name=dto.race_name,
        circuit_id=dto.circuit.circuit_id,
        circuit=dto.circuit.circuit_name,
        date=race_date,
    )


def to_driver(dto: DriverDTO) -> Driver:
    return Driver(
        id=dto.driver_id,
        code=dto.code,
        name=f"{dto.given_name} {dto.family_name}".strip(),
    )


def to_constructor(dto: ConstructorDTO) -> Constructor:
    return Constructor(id=dto.constructor_id, name=dto.name)


def to_fastest_lap(dto: FastestLapDTO | None) -> FastestLap | None:
    if dto is None:
        return None
    return FastestLap(rank=dto.rank, lap=dto.lap, time=parse_lap_time(dto.time.time))


def to_race_result(dto: ResultDTO) -> RaceResult:
    return RaceResult(
        position=dto.position,
        driver=to_driver(dto.driver),
        constructor=to_constructor(dto.constructor),
        grid=dto.grid,
        laps=dto.laps,
        status=dto.status,
        points=dto.points,
        fastest_lap=to_fastest_lap(dto.fastest_lap),
    )


def to_driver_standing(dto: DriverStandingsDTO) -> DriverStanding:
    return DriverStanding(
        position=dto.position or 0,
        driver=to_driver(dto.driver),
        constructors=tuple(to_constructor(c) for c in dto.constructors),
        points=dto.points,
        wins=dto.wins,
    )


def to_laps(dtos: tuple[LapDTO, ...], driver_id: str) -> list[Lap]:
    return [
        Lap(
            number=lap.number,
            position=timing.position,
            time=parse_lap_time(timing.time),
        )
        for lap in dtos
        for timing in lap.timings
        if timing.driver_id == driver_id
    ]


def to_pit_laps(dtos: tuple[PitStopDTO, ...], driver_id: str) -> list[int]:
    return [stop.lap for stop in dtos if stop.driver_id == driver_id]
