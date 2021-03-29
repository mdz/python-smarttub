import pytest

from smarttub import SpaLight

pytestmark = pytest.mark.asyncio


@pytest.fixture
def lights(mock_spa):
    lights = [
        SpaLight(
            mock_spa,
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


async def test_light(mock_spa, lights):
    purple = lights[0]
    assert str(purple)
    assert purple.mode == SpaLight.LightMode.PURPLE
    await purple.set_mode(SpaLight.LightMode.RED, 50)
    mock_spa.request.assert_called_with(
        "PATCH", f"lights/{purple.zone}", {"intensity": 50, "mode": "RED"}
    )
    await purple.turn_off()
    mock_spa.request.assert_called_with(
        "PATCH", f"lights/{purple.zone}", {"intensity": 0, "mode": "OFF"}
    )
