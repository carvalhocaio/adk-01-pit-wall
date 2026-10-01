from collections.abc import Callable
from pathlib import Path

import httpx

from adk_01_pit_wall.jolpica import JolpicaClient

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://jolpica.test/ergast/f1/"

Handler = Callable[[httpx.Request], httpx.Response]
ClientFactory = Callable[[Handler], JolpicaClient]


class CountingLimiter:
    def __init__(self) -> None:
        self.acquired = 0

    async def __aenter__(self) -> None:
        self.acquired += 1

    async def __aexit__(self, *exc_info: object) -> None:
        return None


def fixture_routes(routes: dict[str, str]) -> Handler:
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode().split("?", 1)[0]
        key = (
            f"{path.removeprefix('/ergast/f1/')}?offset={request.url.params['offset']}"
        )
        if key not in routes:
            return httpx.Response(404)
        return httpx.Response(200, content=(FIXTURES / routes[key]).read_bytes())

    return handle
