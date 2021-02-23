import aiohttp
import time

import jwt
import pytest

import smarttub

ACCOUNT_ID = "account_id1"

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="unauthenticated_api")
async def unauthenticated_api(aresponses):
    async with aiohttp.ClientSession() as session:
        yield smarttub.SmartTub(session)


@pytest.fixture(name="api")
async def api(unauthenticated_api, aresponses):
    api = unauthenticated_api
    aresponses.add(
        response={
            "access_token": jwt.encode(
                {api.AUTH_ACCOUNT_ID_KEY: ACCOUNT_ID, "exp": time.time() + 3600},
                "secret",
            ).decode(),
            "token_type": "Bearer",
            "refresh_token": "refresh1",
        }
    )
    await api.login("username1", "password1")
    return api


async def test_login(api, aresponses):
    assert api.account_id == ACCOUNT_ID
    assert api.logged_in is True


async def test_refresh_token(api, aresponses):
    login_token_expiration = api.token_expires_at
    aresponses.add(
        response={
            "access_token": jwt.encode(
                {api.AUTH_ACCOUNT_ID_KEY: ACCOUNT_ID, "exp": time.time() + 3601},
                "secret",
            ).decode(),
        }
    )
    await api._refresh_token()
    assert api.token_expires_at > login_token_expiration


async def test_get_account(api, aresponses):
    aresponses.add(
        response={
            "id": "id1",
            "email": "email1",
        }
    )

    account = await api.get_account()
    assert account.id == "id1"
    assert account.email == "email1"
