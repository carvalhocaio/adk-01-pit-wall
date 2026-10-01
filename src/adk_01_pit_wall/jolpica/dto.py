from pydantic import BaseModel, ConfigDict, Field


class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True)


class CircuitDTO(_Payload):
    circuit_id: str = Field(alias="circuitId")
    circuit_name: str = Field(alias="circuitName")


class DriverDTO(_Payload):
    driver_id: str = Field(alias="driverId")
    code: str = ""
    given_name: str = Field(alias="givenName")
    family_name: str = Field(alias="familyName")


class ConstructorDTO(_Payload):
    constructor_id: str = Field(alias="constructorId")
    name: str


class ResultDTO(_Payload):
    position: int
    points: float
    grid: int
    laps: int
    status: str
    driver: DriverDTO = Field(alias="Driver")
    constructor: ConstructorDTO = Field(alias="Constructor")


class TimingDTO(_Payload):
    driver_id: str = Field(alias="driverId")
    position: int
    time: str


class LapDTO(_Payload):
    number: int
    timings: tuple[TimingDTO, ...] = Field(alias="Timings")


class PitStopDTO(_Payload):
    driver_id: str = Field(alias="driverId")
    lap: int


class RaceDTO(_Payload):
    season: int
    round: int
    race_name: str = Field(alias="raceName")
    date: str
    circuit: CircuitDTO = Field(alias="Circuit")
    results: tuple[ResultDTO, ...] = Field(default=(), alias="Results")
    laps: tuple[LapDTO, ...] = Field(default=(), alias="Laps")
    pit_stops: tuple[PitStopDTO, ...] = Field(default=(), alias="PitStops")


class RaceTableDTO(_Payload):
    races: tuple[RaceDTO, ...] = Field(default=(), alias="Races")


class DriverStandingsDTO(_Payload):
    position: int | None = None
    points: float
    wins: int
    driver: DriverDTO = Field(alias="Driver")
    constructors: tuple[ConstructorDTO, ...] = Field(alias="Constructors")


class StandingsListDTO(_Payload):
    round: int
    driver_standings: tuple[DriverStandingsDTO, ...] = Field(alias="DriverStandings")


class StandingsTableDTO(_Payload):
    standings_lists: tuple[StandingsListDTO, ...] = Field(
        default=(), alias="StandingsLists"
    )


class PageDTO(_Payload):
    limit: int
    offset: int
    total: int
    race_table: RaceTableDTO = Field(default=RaceTableDTO(), alias="RaceTable")
    standings_table: StandingsTableDTO = Field(
        default=StandingsTableDTO(), alias="StandingsTable"
    )

    @property
    def next_offset(self) -> int | None:
        following = self.offset + self.limit
        if self.limit <= 0 or following >= self.total:
            return None
        return following


class EnvelopeDTO(_Payload):
    page: PageDTO = Field(alias="MRData")
