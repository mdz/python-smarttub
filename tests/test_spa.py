import datetime
from dateutil.tz import tzutc
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


async def test_spa(spa):
    assert str(spa)


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
    assert str(status)
    assert len(status.locks) == 4

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


async def test_get_status_full(mock_api, spa):
    mock_api.request.return_value = {
        "ambientTemperature": 65.6,
        "blowoutCycle": "INACTIVE",
        "cleanupCycle": "INACTIVE",
        "current": {"average": 9.5, "kwh": 0.375, "max": 9.6, "min": 9.4, "value": 9.5},
        "date": "2021-03-07",
        "demoMode": "DISABLED",
        "dipSwitches": 8,
        "displayTemperatureFormat": "FAHRENHEIT",
        "error": {"code": 0, "description": None, "title": "All Clear"},
        "errorCode": 0,
        "fieldsLastUpdated": {
            "cfstEvent": "2021-03-07T08:36:52.908Z",
            "errEvent": "2021-03-07T08:00:29.813Z",
            "heatMode": "2021-02-22T07:21:26.598Z",
            "locEvent": "2021-03-07T01:20:34.262Z",
            "online": "2021-03-07T22:04:13.477Z",
            "rpstEvent": "2021-03-07T22:05:21.288Z",
            "setTemperature": "2021-02-26T05:00:27.580Z",
            "sp2stEvent": "2021-03-07T08:36:54.867Z",
            "spstEvent": "2021-03-07T21:39:11.540Z",
            "uv": "2021-03-07T20:01:23.870Z",
            "uvOnDemand": "2021-02-13T04:36:06.268Z",
            "wcstEvent": "2021-03-07T21:59:14.378Z",
        },
        "flowSwitch": "OPEN",
        "heatMode": "AUTO",
        "heater": "OFF",
        "highTemperatureLimit": 38.9,
        "lastUpdated": "2021-03-07T22:05:21.440Z",
        "lights": [
            {
                "color": {"blue": 0, "green": 0, "red": 0, "white": 0},
                "cycleSpeed": 0,
                "intensity": 0,
                "mode": "OFF",
                "zone": 1,
            }
        ],
        "location": {"accuracy": 1053.0, "latitude": 27.129, "longitude": -27.906},
        "locks": {
            "access": "UNLOCKED",
            "maintenance": "UNLOCKED",
            "spa": "LOCKED",
            "temperature": "UNLOCKED",
        },
        "online": True,
        "ozone": "OFF",
        "primaryFiltration": {
            "cycle": 1,
            "duration": 4,
            "lastUpdated": "2021-02-24T02:55:47.180Z",
            "mode": "NORMAL",
            "startHour": 2,
            "status": "INACTIVE",
        },
        "pumps": [
            {
                "current": None,
                "id": "P2",
                "speed": "ONE_SPEED",
                "state": "OFF",
                "type": "JET",
            },
            {
                "current": None,
                "id": "P1",
                "speed": "ONE_SPEED",
                "state": "OFF",
                "type": "JET",
            },
            {
                "current": None,
                "id": "CP",
                "speed": "ONE_SPEED",
                "state": "OFF",
                "type": "CIRCULATION",
            },
        ],
        "secondaryFiltration": {
            "lastUpdated": "2021-03-04T16:47:29.882Z",
            "mode": "AWAY",
            "status": "INACTIVE",
        },
        "setTemperature": 38.3,
        "state": "NORMAL",
        "time": "14:05:00",
        "timeFormat": "HOURS_12",
        "timeSet": None,
        "timezone": None,
        "uv": "OFF",
        "uvOnDemand": "OFF",
        "versions": {"balboa": "1.06", "controller": "1.28", "jacuzziLink": "53"},
        "water": {
            "oxidationReductionPotential": 604,
            "ph": 7.01,
            "temperature": 38.9,
            "temperatureLastUpdated": "2021-03-07T22:04:15.686Z",
            "turbidity": 0.01,
        },
        "watercare": None,
    }

    status = await spa.get_status_full()
    assert len(status.pumps) == 3
    for pump in status.pumps:
        assert isinstance(pump, smarttub.SpaPump)
    assert len(status.lights) == 1
    for light in status.lights:
        assert isinstance(light, smarttub.SpaLight)

    assert status.spa == spa
    assert len(status.locks) == 4

    await status.locks["access"].lock()
    mock_api.request.assert_called_with(
        "POST", "spas/id1/lock", {"type": "ACCESS", "code": "0772"}
    )

    await status.locks["spa"].unlock()
    mock_api.request.assert_called_with(
        "POST", "spas/id1/unlock", {"type": "SPA", "code": "0772"}
    )


# https://github.com/home-assistant/core/issues/102339
async def test_null_blowout(mock_api, spa):
    mock_api.request.return_value = {
        "ambientTemperature": 65.6,
        "blowoutCycle": None,
        "cleanupCycle": "INACTIVE",
        "current": {"average": 9.5, "kwh": 0.375, "max": 9.6, "min": 9.4, "value": 9.5},
        "date": "2021-03-07",
        "demoMode": "DISABLED",
        "dipSwitches": 8,
        "displayTemperatureFormat": "FAHRENHEIT",
        "error": {"code": 0, "description": None, "title": "All Clear"},
        "errorCode": 0,
        "fieldsLastUpdated": {
            "cfstEvent": "2021-03-07T08:36:52.908Z",
            "errEvent": "2021-03-07T08:00:29.813Z",
            "heatMode": "2021-02-22T07:21:26.598Z",
            "locEvent": "2021-03-07T01:20:34.262Z",
            "online": "2021-03-07T22:04:13.477Z",
            "rpstEvent": "2021-03-07T22:05:21.288Z",
            "setTemperature": "2021-02-26T05:00:27.580Z",
            "sp2stEvent": "2021-03-07T08:36:54.867Z",
            "spstEvent": "2021-03-07T21:39:11.540Z",
            "uv": "2021-03-07T20:01:23.870Z",
            "uvOnDemand": "2021-02-13T04:36:06.268Z",
            "wcstEvent": "2021-03-07T21:59:14.378Z",
        },
        "flowSwitch": "OPEN",
        "heatMode": "AUTO",
        "heater": "OFF",
        "highTemperatureLimit": 38.9,
        "lastUpdated": "2021-03-07T22:05:21.440Z",
        "lights": [
            {
                "color": {"blue": 0, "green": 0, "red": 0, "white": 0},
                "cycleSpeed": 0,
                "intensity": 0,
                "mode": "OFF",
                "zone": 1,
            }
        ],
        "location": {"accuracy": 1053.0, "latitude": 27.129, "longitude": -27.906},
        "locks": {
            "access": "UNLOCKED",
            "maintenance": "UNLOCKED",
            "spa": "LOCKED",
            "temperature": "UNLOCKED",
        },
        "online": True,
        "ozone": "OFF",
        "primaryFiltration": {
            "cycle": 1,
            "duration": 4,
            "lastUpdated": "2021-02-24T02:55:47.180Z",
            "mode": "NORMAL",
            "startHour": 2,
            "status": "INACTIVE",
        },
        "pumps": [
            {
                "current": None,
                "id": "P2",
                "speed": "ONE_SPEED",
                "state": "OFF",
                "type": "JET",
            },
            {
                "current": None,
                "id": "P1",
                "speed": "ONE_SPEED",
                "state": "OFF",
                "type": "JET",
            },
            {
                "current": None,
                "id": "CP",
                "speed": "ONE_SPEED",
                "state": "OFF",
                "type": "CIRCULATION",
            },
        ],
        "secondaryFiltration": {
            "lastUpdated": "2021-03-04T16:47:29.882Z",
            "mode": "AWAY",
            "status": "INACTIVE",
        },
        "setTemperature": 38.3,
        "state": "NORMAL",
        "time": "14:05:00",
        "timeFormat": "HOURS_12",
        "timeSet": None,
        "timezone": None,
        "uv": "OFF",
        "uvOnDemand": "OFF",
        "versions": {"balboa": "1.06", "controller": "1.28", "jacuzziLink": "53"},
        "water": {
            "oxidationReductionPotential": 604,
            "ph": 7.01,
            "temperature": 38.9,
            "temperatureLastUpdated": "2021-03-07T22:04:15.686Z",
            "turbidity": 0.01,
        },
        "watercare": None,
    }
    status = await spa.get_status_full()
    assert status.blowout_cycle is None


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
    assert str(error)
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


async def test_get_debug_status(mock_api, spa):
    mock_api.request.return_value = {
        "debugStatus": {
            "battery": {"percentCharge": 82.2, "voltage": 4.04},
            "freeMemory": 45520,
            "lastResetReason": "RESET_REASON_USER",
            "powerStatus": "DC",
            "resetCount": 133,
            "signal": {"quality": 37, "strength": -89},
            "uptime": {
                "connection": 2059053,
                "system": 2059161,
                "tubController": 2059159,
            },
        }
    }

    debug_status = await spa.get_debug_status()
    assert debug_status is not None


async def test_get_energy_usage(mock_api, spa):
    mock_api.request.return_value = {"buckets": []}
    usage = await spa.get_energy_usage(
        smarttub.Spa.EnergyUsageInterval.DAY,
        datetime.date(2021, 1, 1),
        datetime.date(2021, 1, 31),
    )
    mock_api.request.assert_called_with(
        "POST",
        f"spas/{spa.id}/energyUsage",
        {"start": "2021-01-01", "end": "2021-01-31", "interval": "DAY"},
    )
    assert usage == []


async def test_set_heat_mode(mock_api, spa):
    await spa.set_heat_mode(smarttub.Spa.HeatMode.AUTO)
    mock_api.request.assert_called_with(
        "PATCH", f"spas/{spa.id}/config", {"heatMode": "AUTO"}
    )


async def test_set_temperature(mock_api, spa):
    await spa.set_temperature(38.3)
    mock_api.request.assert_called_with(
        "PATCH", f"spas/{spa.id}/config", {"setTemperature": 38.3}
    )


async def test_toggle_clearray(mock_api, spa):
    await spa.toggle_clearray()
    mock_api.request.assert_called_with("POST", f"spas/{spa.id}/clearray/toggle", None)


async def test_set_temperature_format(mock_api, spa):
    await spa.set_temperature_format(smarttub.Spa.TemperatureFormat.FAHRENHEIT)
    mock_api.request.assert_called_with(
        "POST", f"spas/{spa.id}/config", {"displayTemperatureFormat": "FAHRENHEIT"}
    )


async def test_set_date_time(mock_api, spa):
    with pytest.raises(ValueError):
        await spa.set_date_time()

    await spa.set_date_time(date=datetime.date(2021, 1, 1))
    mock_api.request.assert_called_with(
        "POST", f"spas/{spa.id}/config", {"dateTimeConfig": {"date": "2021-01-01"}}
    )
    await spa.set_date_time(time=datetime.time(12, 45))
    mock_api.request.assert_called_with(
        "POST", f"spas/{spa.id}/config", {"dateTimeConfig": {"time": "12:45"}}
    )


async def test_secondary_filtration_cycle(mock_api, spa):
    cycle = smarttub.SpaSecondaryFiltrationCycle(
        spa,
        **{
            "lastUpdated": "2020-07-09T19:39:52.961Z",
            "mode": "AWAY",
            "status": "INACTIVE",
        },
    )
    assert cycle.last_updated == datetime.datetime(
        2020, 7, 9, 19, 39, 52, 961000, tzinfo=tzutc()
    )
    assert (
        cycle.mode == smarttub.SpaSecondaryFiltrationCycle.SecondaryFiltrationMode.AWAY
    )
    assert cycle.status == smarttub.SpaSecondaryFiltrationCycle.CycleStatus.INACTIVE

    await cycle.set_mode(
        smarttub.SpaSecondaryFiltrationCycle.SecondaryFiltrationMode.FREQUENT
    )
    mock_api.request.assert_called_with(
        "PATCH", f"spas/{spa.id}/config", {"secondaryFiltrationConfig": "FREQUENT"}
    )
