from contextlib import AbstractAsyncContextManager
from urllib.parse import quote

import httpx
from aiolimiter import AsyncLimiter
from pydantic import ValidationError

from adk_01_pit_wall.f1 import DriverStanding, Lap, NoLapsError, Race, RaceResult

from .dto import EnvelopeDTO, PageDTO, RaceDTO
from .errors import (
    MalformedResponseError,
    RaceNotFoundError,
    RateLimitedError,
    UnexpectedStatusError,
)
from .mapping import (
    to_driver_standing,
    to_laps,
    to_pit_laps,
    to_race,
    to_race_result,
)

DEFAULT_BASE_URL = "https://api.jolpi.ca/ergast/f1/"
MAX_PAGE_SIZE = 100
REQUESTS_PER_SECOND = 4


def create_http_client(base_url: str = DEFAULT_BASE_URL) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(10.0),
        headers={"Accept": "application/json"},
    )


class JolpicaClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        limiter: AbstractAsyncContextManager[object] | None = None,
    ) -> None:
        self._http = http
        self._limiter = limiter or AsyncLimiter(REQUESTS_PER_SECOND, time_period=1)

    async def find_race(self, season: int, circuit_id: str) -> Race:
        races = await self._races(str(season), "circuits", circuit_id, "races")
        if not races:
            raise RaceNotFoundError(f"no race in season {season} at {circuit_id!r}")
        return to_race(races[0])

    async def race_results(
        self, season: int, round_: int
    ) -> tuple[Race, list[RaceResult]]:
        races = await self._races(str(season), str(round_), "results")
        if not races:
            raise RaceNotFoundError(f"no race for season {season} round {round_}")
        results = [to_race_result(r) for race in races for r in race.results]
        return to_race(races[0]), results

    async def driver_standings(
        self, season: int, after_round: int | None = None
    ) -> tuple[int, list[DriverStanding]]:
        segments = [str(season), "driverstandings"]
        if after_round:
            segments.insert(1, str(after_round))
        pages = await self._fetch_all(*segments)
        lists = [lst for page in pages for lst in page.standings_table.standings_lists]
        standings = [
            to_driver_standing(s) for lst in lists for s in lst.driver_standings
        ]
        if not standings:
            raise RaceNotFoundError(
                f"no standings for season {season} after round {after_round}"
            )
        return lists[-1].round, standings

    async def driver_laps(self, season: int, round_: int, driver_id: str) -> list[Lap]:
        races = await self._races(
            str(season), str(round_), "drivers", driver_id, "laps"
        )
        laps = [lap for race in races for lap in to_laps(race.laps, driver_id)]
        if not laps:
            raise NoLapsError(
                f"no laps for driver {driver_id!r} in season {season} round {round_}"
            )
        return laps

    async def driver_pit_laps(
        self, season: int, round_: int, driver_id: str
    ) -> list[int]:
        races = await self._races(
            str(season), str(round_), "drivers", driver_id, "pitstops"
        )
        return [lap for race in races for lap in to_pit_laps(race.pit_stops, driver_id)]

    async def _races(self, *segments: str) -> list[RaceDTO]:
        pages = await self._fetch_all(*segments)
        return [race for page in pages for race in page.race_table.races]

    async def _fetch_all(self, *segments: str) -> list[PageDTO]:
        path = "/".join(quote(segment, safe="") for segment in segments) + "/"
        pages: list[PageDTO] = []
        offset: int | None = 0
        while offset is not None:
            page = await self._fetch_page(path, offset)
            pages.append(page)
            offset = page.next_offset
        return pages

    async def _fetch_page(self, path: str, offset: int) -> PageDTO:
        async with self._limiter:
            response = await self._http.get(
                path, params={"limit": MAX_PAGE_SIZE, "offset": offset}
            )
        if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            raise RateLimitedError(f"jolpica rate limit exceeded for {path}")
        if response.status_code != httpx.codes.OK:
            raise UnexpectedStatusError(
                f"jolpica returned {response.status_code} for {path}"
            )
        try:
            return EnvelopeDTO.model_validate_json(response.content).page
        except ValidationError as exc:
            raise MalformedResponseError(f"unexpected payload for {path}") from exc
