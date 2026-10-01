from collections.abc import AsyncIterator

import httpx
import pytest

from adk_01_pit_wall.jolpica import JolpicaClient

from .support import BASE_URL, ClientFactory, CountingLimiter, Handler


@pytest.fixture
def limiter() -> CountingLimiter:
    return CountingLimiter()


@pytest.fixture
async def make_client(limiter: CountingLimiter) -> AsyncIterator[ClientFactory]:
    opened: list[httpx.AsyncClient] = []

    def build(handler: Handler) -> JolpicaClient:
        http = httpx.AsyncClient(
            base_url=BASE_URL, transport=httpx.MockTransport(handler)
        )
        opened.append(http)
        return JolpicaClient(http, limiter=limiter)

    yield build
    for http in opened:
        await http.aclose()
