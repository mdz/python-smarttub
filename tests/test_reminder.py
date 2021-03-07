from unittest.mock import create_autospec

import pytest

import smarttub
from smarttub import SpaReminder

pytestmark = pytest.mark.asyncio


@pytest.fixture
def reminders(mock_api):
    spa = create_autospec(smarttub.Spa, instance=True)
    spa.request = mock_api.request
    reminders = [
        SpaReminder(
            spa,
            **{
                "id": "WATER",
                "lastUpdated": "2021-03-04T08:00:45.330Z",
                "name": "Refresh Water",
                "remainingDuration": 0,
                "snoozed": False,
                "state": "INACTIVE",
            }
        )
    ]
    return reminders


async def test_reminders(reminders, mock_api):
    reminder = reminders[0]
    assert reminder.id == "WATER"
    await reminder.snooze(5)
    mock_api.request.assert_called_with(
        "PATCH", "reminders/WATER", {"remainingDuration": 5}
    )
    mock_api.reset_mock()
    await reminder.reset(365)
    mock_api.request.assert_called_with(
        "PATCH", "reminders/WATER", {"remainingDuration": 365, "reset": True}
    )
