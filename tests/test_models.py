from datetime import timedelta

import pytest

from adk_01_pit_wall.models import Duration


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (timedelta(milliseconds=71200), Duration(millis=71200, display="1:11.200")),
        (timedelta(microseconds=72333333), Duration(millis=72333, display="1:12.333")),
        (timedelta(seconds=59.9996), Duration(millis=60000, display="1:00.000")),
        (timedelta(milliseconds=9050), Duration(millis=9050, display="0:09.050")),
    ],
)
def test_duration_of(value, expected):
    assert Duration.of(value) == expected
