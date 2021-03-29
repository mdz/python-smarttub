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


async def test_login_failed(api, aresponses):
    aresponses.add(response=aresponses.Response(status=403))
    with pytest.raises(smarttub.LoginFailed):
        await api.login("username", "password")


async def test_refresh_token(api, aresponses):
    now = time.time()
    api.token_expires_at = now
    aresponses.add(
        response={
            "access_token": jwt.encode(
                {api.AUTH_ACCOUNT_ID_KEY: ACCOUNT_ID, "exp": now + 3601},
                "secret",
            ).decode(),
        }
    )
    aresponses.add(response={"status": "OK"})
    response = await api.request("GET", "/")
    assert api.token_expires_at > now
    assert response.get("status") == "OK"


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


async def test_api_error(api, aresponses):
    aresponses.add(response=aresponses.Response(status=500))
    with pytest.raises(smarttub.APIError):
        await api.get_account()


async def test_not_logged_in(unauthenticated_api, aresponses):
    with pytest.raises(RuntimeError):
        await unauthenticated_api.request("GET", "/")


async def test_request(api, aresponses):
    aresponses.add(response=aresponses.Response(text=None, status=200))
    response = await api.request("GET", "/")
    assert response is None
