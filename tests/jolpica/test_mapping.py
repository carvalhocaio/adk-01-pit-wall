from datetime import timedelta

import pytest

from adk_01_pit_wall.jolpica import MalformedResponseError
from adk_01_pit_wall.jolpica.mapping import parse_lap_time


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1:31.803", timedelta(minutes=1, seconds=31.803)),
        ("59.123", timedelta(seconds=59.123)),
        ("2:00.000", timedelta(minutes=2)),
    ],
)
def test_parse_lap_time(raw, expected):
    assert parse_lap_time(raw) == expected


@pytest.mark.parametrize("raw", ["", "1:xx.000", "fast"])
def test_parse_lap_time_rejects_garbage(raw):
    with pytest.raises(MalformedResponseError):
        parse_lap_time(raw)
