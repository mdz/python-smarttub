from unittest.mock import create_autospec

import pytest

import smarttub
from smarttub import SpaPump

pytestmark = pytest.mark.asyncio


@pytest.fixture
def spa():
    spa = create_autospec(smarttub.Spa, instance=True)
    return spa


@pytest.fixture
def pumps(spa):
    pumps = [
        SpaPump(
            spa,
            **{
                "id": "pid1",
                "speed": "speed1",
                "state": "OFF"
                if pump_type == SpaPump.PumpType.CIRCULATION
                else SpaPump.PumpState.HIGH.name,
                "type": pump_type.name,
            },
        )
        for i, pump_type in enumerate(SpaPump.PumpType)
    ]
    return pumps


async def test_pump(spa, pumps):
    circ = pumps[0]
    assert circ.speed == "speed1"
    assert circ.state == SpaPump.PumpState.OFF
    assert circ.type == SpaPump.PumpType.CIRCULATION
    await circ.toggle()
    spa.request.assert_called_with("POST", f"pumps/{circ.id}/toggle")
