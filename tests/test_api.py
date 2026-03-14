import base64
import datetime
import json

import aiohttp
import pytest

import smarttub

ACCOUNT_ID = "account_id1"

pytestmark = pytest.mark.asyncio


def make_id_token(account_id: str) -> str:
    """Create a mock ID token with the account_id claim."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(
        b"="
    )
    payload = base64.urlsafe_b64encode(
        json.dumps({"custom:account_id": account_id}).encode()
    ).rstrip(b"=")
    signature = base64.urlsafe_b64encode(b"fakesignature").rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.{signature.decode()}"


def make_login_response(account_id: str, expires_in: int = 86400) -> dict:
    """Create a mock login response."""
    return {
        "token": {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "id_token": make_id_token(account_id),
            "expires_in": expires_in,
        }
    }


@pytest.fixture(name="unauthenticated_api")
async def unauthenticated_api():
    async with aiohttp.ClientSession() as session:
        yield smarttub.SmartTub(session)


@pytest.fixture(name="api")
async def api(unauthenticated_api, aresponses):
    api = unauthenticated_api
    aresponses.add(
        response=aresponses.Response(
            body=json.dumps(make_login_response(ACCOUNT_ID)),
            status=201,
            content_type="application/json",
        )
    )
    await api.login("username1", "password1")
    return api


async def test_login(api):
    assert api.account_id == ACCOUNT_ID
    assert api._access_token == "access_token_123"
    assert api._username == "username1"
    assert api._password == "password1"


async def test_login_failed_400(unauthenticated_api, aresponses):
    aresponses.add(
        response=aresponses.Response(
            body=json.dumps({"message": "Invalid credentials"}),
            status=400,
            content_type="application/json",
        )
    )
    with pytest.raises(smarttub.LoginFailed):
        await unauthenticated_api.login("username", "password")


async def test_login_failed_401(unauthenticated_api, aresponses):
    aresponses.add(
        response=aresponses.Response(
            body=json.dumps([{"description": "Bad request", "type": "ERROR"}]),
            status=401,
            content_type="application/json",
        )
    )
    with pytest.raises(smarttub.LoginFailed):
        await unauthenticated_api.login("username", "password")


async def test_token_reauth_on_expiry(api, aresponses):
    """Test that we re-authenticate when the token expires."""
    # Expire the token
    api._token_expires_at = datetime.datetime.now() - datetime.timedelta(seconds=1)

    # Mock the re-login response
    aresponses.add(
        response=aresponses.Response(
            body=json.dumps(make_login_response(ACCOUNT_ID)),
            status=201,
            content_type="application/json",
        )
    )
    # Mock the actual API request
    aresponses.add(
        response=aresponses.Response(
            body=json.dumps({"status": "OK"}),
            status=200,
            content_type="application/json",
        )
    )

    response = await api.request("GET", "/")
    assert api._token_expires_at > datetime.datetime.now()
    assert response.get("status") == "OK"


async def test_get_account(api, aresponses):
    aresponses.add(
        response=aresponses.Response(
            body=json.dumps({"id": "id1", "email": "email1"}),
            status=200,
            content_type="application/json",
        )
    )

    account = await api.get_account()
    assert account.id == "id1"
    assert account.email == "email1"


async def test_api_error(api, aresponses):
    aresponses.add(response=aresponses.Response(status=500))
    with pytest.raises(smarttub.APIError):
        await api.get_account()


async def test_not_logged_in(unauthenticated_api):
    with pytest.raises(RuntimeError):
        await unauthenticated_api.request("GET", "/")


async def test_request_empty_response(api, aresponses):
    aresponses.add(
        response=aresponses.Response(
            body="",
            status=200,
            headers={"content-length": "0"},
        )
    )
    response = await api.request("GET", "/")
    assert response is None
