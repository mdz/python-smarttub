import argparse
from unittest.mock import AsyncMock, MagicMock

from smarttub.__main__ import info_command


def _args(**overrides):
    values = dict(
        all=True,
        status=False,
        location=False,
        pumps=False,
        lights=False,
        errors=False,
        reminders=False,
        locks=False,
        sensors=False,
        energy=False,
        debug=False,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _spa():
    spa = MagicMock()
    spa.name = "Test Spa"
    spa.get_status_full_raw = AsyncMock(
        return_value={
            "heatMode": "SOME_NEW_MODE",
            "location": {"latitude": 12.5, "longitude": 34.5},
            "pumps": [{"id": "P1"}],
            "lights": [{"zone": 1}],
            "locks": {"spa": "UNLOCKED"},
            "sensors": [],
        }
    )
    spa.get_errors_raw = AsyncMock(return_value=[{"code": 7}])
    spa.get_reminders_raw = AsyncMock(return_value=[{"id": "r1"}])
    spa.get_energy_usage = AsyncMock(return_value=[])
    spa.get_debug_status = AsyncMock(return_value={"uptime": 1})
    return spa


async def test_info_all_redacts_location_and_shows_unknown_values(capsys):
    await info_command([_spa()], _args())

    out = capsys.readouterr().out
    assert "SOME_NEW_MODE" in out
    assert "12.5" not in out
    assert "'code': 7" in out


async def test_info_location_flag_shows_location(capsys):
    await info_command([_spa()], _args(all=False, location=True))

    assert "12.5" in capsys.readouterr().out


async def test_info_one_failing_section_does_not_hide_others(capsys):
    spa = _spa()
    spa.get_errors_raw.side_effect = KeyError("boom")

    await info_command([spa], _args())

    out = capsys.readouterr().out
    assert "Error: KeyError: 'boom'" in out
    assert "'id': 'r1'" in out
    assert "'uptime': 1" in out


async def test_info_status_failure_reported_in_each_dependent_section(capsys):
    spa = _spa()
    spa.get_status_full_raw.side_effect = RuntimeError("api down")

    await info_command([spa], _args())

    out = capsys.readouterr().out
    assert out.count("Error: RuntimeError: api down") >= 5
    assert "'id': 'r1'" in out
