import pytest

from smarttub import SpaPump

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pumps(mock_spa):
    pumps = [
        SpaPump(
            mock_spa,
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


async def test_pump(mock_spa, pumps):
    circ = pumps[1]
    assert str(circ)
    assert circ.speed == "speed1"
    assert circ.state == SpaPump.PumpState.OFF
    assert circ.type == SpaPump.PumpType.CIRCULATION
    await circ.toggle()
    mock_spa.request.assert_called_with("POST", f"pumps/{circ.id}/toggle")
