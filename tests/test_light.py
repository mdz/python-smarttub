from unittest.mock import create_autospec

import pytest

import smarttub
from smarttub import SpaLight

pytestmark = pytest.mark.asyncio


@pytest.fixture
def spa():
    spa = create_autospec(smarttub.Spa, instance=True)
    return spa


@pytest.fixture
def lights(spa):
    lights = [
        SpaLight(
            spa,
            **{
                "color": {"blue": 0, "green": 0, "red": 0, "white": 0},
                "intensity": 0 if mode == SpaLight.LightMode.OFF else 50,
                "mode": mode.name,
                "zone": i + 1,
            },
        )
        for i, mode in enumerate(SpaLight.LightMode)
    ]
    return lights


async def test_light(spa, lights):
    purple = lights[0]
    assert purple.mode == SpaLight.LightMode.PURPLE
    await purple.set_mode(SpaLight.LightMode.RED, 50)
    purple.spa.request.assert_called_with(
        "PATCH", f"lights/{purple.zone}", {"intensity": 50, "mode": "RED"}
    )
    await purple.turn_off()
    purple.spa.request.assert_called_with(
        "PATCH", f"lights/{purple.zone}", {"intensity": 0, "mode": "OFF"}
    )
