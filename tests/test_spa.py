import pytest

import smarttub


@pytest.fixture(name='spa')
def spa(mock_api, mock_account):
    spa = smarttub.Spa(mock_api, mock_account, id='id1', brand='brand1', model='model1')
    return spa


@pytest.mark.asyncio
async def test_get_status(mock_api, spa):
    mock_api.request.return_value = 'status1'
    status = await spa.get_status()
    assert status == 'status1'


@pytest.mark.asyncio
async def test_get_pumps(mock_api, spa):
    mock_api.request.return_value = {
        'pumps': [{
            'id': 'pid1',
            'speed': 'speed1',
            'state': 'state1',
            'type': 'type1',
        }]
    }
    pumps = await spa.get_pumps()
    assert len(pumps) == 1
    pump = pumps[0]
    assert pump.id == 'pid1'


@pytest.mark.asyncio
async def test_get_lights(mock_api, spa):
    mock_api.request.return_value = {
        'lights': [{
            'color': {'blue': 0, 'green': 0, 'red': 0},
            'intensity': 0,
            'mode': 'OFF',
            'zone': 1,
        }]
    }
    lights = await spa.get_lights()
    assert len(lights) == 1
    light = lights[0]
    assert light.zone == 1


@pytest.mark.asyncio
async def test_get_errors(mock_api, spa):
    mock_api.request.return_value = {'content': []}
    errors = await spa.get_errors()
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_get_reminders(mock_api, spa):
    mock_api.request.return_value = {
        'reminders': [{
            "id": "id1",
            "lastUpdated": "2020-07-09T06:42:53.857Z",
            "name": "name1",
            "remainingDuration": 23,
            "snoozed": False,
            "state": "INACTIVE"
        }]
    }
    reminders = await spa.get_reminders()
    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder.id == 'id1'
    assert reminder.name == "name1"
