from unittest.mock import create_autospec

import pytest

import smarttub

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="mock_account")
def mock_account(mock_api):
    account = create_autospec(smarttub.Account, instance=True)
    return account


@pytest.fixture(name="spa")
def spa(mock_api, mock_account):
    spa = smarttub.Spa(mock_api, mock_account, id="id1", brand="brand1", model="model1")
    return spa


async def test_get_status(mock_api, spa):
    mock_api.request.return_value = {
        "ambientTemperature": 65.6,
        "blowoutCycle": "INACTIVE",
        "cleanupCycle": "INACTIVE",
        "current": {"average": 0.0, "kwh": 0.213, "max": 0.0, "min": 0.0, "value": 0.0},
        "date": "2021-02-21",
        "demoMode": "DISABLED",
        "dipSwitches": 8,
        "displayTemperatureFormat": "FAHRENHEIT",
        "error": {"code": 0, "description": None, "title": "All Clear"},
        "errorCode": 0,
        "fieldsLastUpdated": {
            "cfstEvent": None,
            "errEvent": "2021-02-17T09:10:31.059Z",
            "heatMode": "2020-07-09T19:40:01.883Z",
            "locEvent": "2021-02-21T01:20:41.956Z",
            "online": "2021-02-21T21:28:41.791Z",
            "rpstEvent": "2021-02-21T21:32:36.053Z",
            "setTemperature": "2021-02-20T03:10:00.525Z",
            "sp2stEvent": "2021-02-21T07:24:08.119Z",
            "spstEvent": "2021-02-21T20:40:09.330Z",
            "uv": "2021-02-21T18:48:34.699Z",
            "uvOnDemand": "2021-02-13T04:36:06.268Z",
            "wcstEvent": "2021-02-21T21:30:15.089Z",
        },
        "flowSwitch": "OPEN",
        "heatMode": "AUTO",
        "heater": "OFF",
        "highTemperatureLimit": 36.1,
        "lastUpdated": "2021-02-21T21:32:36.215Z",
        "lights": None,
        "locks": {
            "access": "UNLOCKED",
            "maintenance": "UNLOCKED",
            "spa": "UNLOCKED",
            "temperature": "UNLOCKED",
        },
        "online": True,
        "ozone": "OFF",
        "primaryFiltration": {
            "cycle": 1,
            "duration": 4,
            "lastUpdated": "2021-01-20T11:38:57.014Z",
            "mode": "NORMAL",
            "startHour": 2,
            "status": "INACTIVE",
        },
        "pumps": None,
        "secondaryFiltration": {
            "lastUpdated": "2020-07-09T19:39:52.961Z",
            "mode": "AWAY",
            "status": "INACTIVE",
        },
        "setTemperature": 38.3,
        "state": "NORMAL",
        "time": "14:45:00",
        "timeFormat": "HOURS_12",
        "timeSet": None,
        "timezone": None,
        "uv": "OFF",
        "uvOnDemand": "OFF",
        "versions": {"balboa": "1.06", "controller": "1.28", "jacuzziLink": "53"},
        "water": {
            "oxidationReductionPotential": 604,
            "ph": 7.01,
            "temperature": 38.3,
            "temperatureLastUpdated": "2021-02-21T16:40:10.054Z",
            "turbidity": 0.01,
        },
        "watercare": None,
    }

    status = await spa.get_status()
    assert status.state == "NORMAL"

    pf = status.primary_filtration
    assert pf.mode == status.primary_filtration.PrimaryFiltrationMode.NORMAL
    assert pf.duration == 4
    assert pf.start_hour == 2
    assert pf.status == status.CycleStatus.INACTIVE

    await pf.set(start_hour=5)
    mock_api.request.assert_called_with(
        "PATCH",
        f"spas/{spa.id}/config",
        body={
            "primaryFiltrationConfig": {
                "cycle": pf.cycle,
                "duration": pf.duration,
                "mode": pf.mode.name,
                "startHour": 5,
            }
        },
    )


async def test_get_pumps(mock_api, spa):
    mock_api.request.return_value = {
        "pumps": [
            {
                "id": "pid1",
                "speed": "speed1",
                "state": "OFF",
                "type": "CIRCULATION",
            }
        ]
    }
    pumps = await spa.get_pumps()
    assert len(pumps) == 1
    pump = pumps[0]
    assert pump.id == "pid1"


async def test_get_lights(mock_api, spa):
    mock_api.request.return_value = {
        "lights": [
            {
                "color": {"blue": 0, "green": 0, "red": 0, "white": 0},
                "intensity": 0,
                "mode": "OFF",
                "zone": 1,
            }
        ]
    }
    lights = await spa.get_lights()
    assert len(lights) == 1
    light = lights[0]
    assert light.zone == 1


async def test_get_errors(mock_api, spa):
    mock_api.request.return_value = {
        "content": [
            {
                "code": 11,
                "title": "Flow Switch Stuck Open",
                "description": None,
                "createdAt": "2019-12-11T18:51:10.123Z",
                "updatedAt": "2020-07-14T19:00:50.705Z",
                "active": True,
                "errorType": "TUB_ERROR",
            }
        ],
        "pageable": {
            "sort": {"sorted": True, "unsorted": False, "empty": False},
            "pageSize": 10,
            "pageNumber": 0,
            "offset": 0,
            "paged": True,
            "unpaged": False,
        },
        "last": True,
        "totalPages": 1,
        "totalElements": 1,
        "first": True,
        "sort": {"sorted": True, "unsorted": False, "empty": False},
        "numberOfElements": 1,
        "size": 10,
        "number": 0,
        "empty": False,
    }
    errors = await spa.get_errors()
    assert len(errors) == 1
    error = errors[0]
    assert error.title == "Flow Switch Stuck Open"


async def test_get_reminders(mock_api, spa):
    mock_api.request.return_value = {
        "reminders": [
            {
                "id": "id1",
                "lastUpdated": "2020-07-09T06:42:53.857Z",
                "name": "name1",
                "remainingDuration": 23,
                "snoozed": False,
                "state": "INACTIVE",
            }
        ]
    }
    reminders = await spa.get_reminders()
    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder.id == "id1"
    assert reminder.name == "name1"
