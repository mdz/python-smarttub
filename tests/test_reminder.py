import pytest

from smarttub import SpaReminder

pytestmark = pytest.mark.asyncio


@pytest.fixture
def reminders(mock_spa):
    reminders = [
        SpaReminder(
            mock_spa,
            **{
                "id": "WATER",
                "lastUpdated": "2021-03-04T08:00:45.330Z",
                "name": "Refresh Water",
                "remainingDuration": 0,
                "snoozed": False,
                "state": "INACTIVE",
            },
        ),
        SpaReminder(
            mock_spa,
            **{
                "id": "NO_LAST_UPDATED",
                # lastUpdated may be null, see
                # https://github.com/mdz/python-smarttub/issues/22
                "lastUpdated": None,
                "name": "Refresh Water",
                "remainingDuration": 0,
                "snoozed": False,
                "state": "INACTIVE",
            },
        ),
    ]
    return reminders


async def test_reminders(mock_spa, reminders):
    reminder = reminders[0]
    assert str(reminder)
    assert reminder.id == "WATER"
    await reminder.snooze(5)
    mock_spa.request.assert_called_with(
        "PATCH", "reminders/WATER", {"remainingDuration": 5}
    )
    mock_spa.reset_mock()
    await reminder.reset(365)
    mock_spa.request.assert_called_with(
        "PATCH", "reminders/WATER", {"remainingDuration": 365, "reset": True}
    )
