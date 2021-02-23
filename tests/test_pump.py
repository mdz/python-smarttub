from unittest.mock import create_autospec

import pytest

import smarttub
from smarttub import SpaPump

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pumps(mock_api):
    spa = create_autospec(smarttub.Spa, instance=True)
    spa.request = mock_api.request
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
            }
        )
        for i, pump_type in enumerate(SpaPump.PumpType)
    ]
    return pumps


async def test_pump(pumps):
    pass
