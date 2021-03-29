import pytest

import smarttub

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="account")
def account(mock_api):
    return smarttub.Account(mock_api, id="id1", email="email1")


async def test_account(account):
    assert str(account)


async def test_get_spas(mock_api, account):
    mock_api.request.side_effect = [
        {"content": [{"id": "sid1"}]},
        {"id": "sid1", "brand": "brand1", "model": "model1"},
    ]
    spas = await account.get_spas()
    assert len(spas) == 1
    spa = spas[0]
    assert spa.id == "sid1"
