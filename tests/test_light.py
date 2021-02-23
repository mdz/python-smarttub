from unittest.mock import create_autospec

import pytest

import smarttub
from smarttub import SpaLight

pytestmark = pytest.mark.asyncio


@pytest.fixture
def lights(mock_api):
    spa = create_autospec(smarttub.Spa, instance=True)
    spa.request = mock_api.request
    lights = [
        SpaLight(
            spa,
            **{
                "color": {"blue": 0, "green": 0, "red": 0, "white": 0},
                "intensity": 0 if mode == SpaLight.LightMode.OFF else 50,
                "mode": mode.name,
                "zone": i + 1,
            }
        )
        for i, mode in enumerate(SpaLight.LightMode)
    ]
    return lights


async def test_light(lights):
    pass
