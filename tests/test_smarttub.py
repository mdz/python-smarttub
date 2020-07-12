from unittest.mock import AsyncMock, create_autospec

import aiohttp
import time

import jwt
import pytest

import smarttub

ACCOUNT_ID = 'account_id1'


@pytest.fixture(name='mock_session')
def mock_session(mock_response):
    session = create_autospec(aiohttp.ClientSession, instance=True)
    session.get = AsyncMock(spec=aiohttp.ClientSession.get)
    session.get.return_value = mock_response
    session.post = AsyncMock(spec=aiohttp.ClientSession.post)
    session.post.return_value = mock_response
    session.patch = AsyncMock(spec=aiohttp.ClientSession.patch)
    session.patch.return_value = mock_response
    session.request = AsyncMock(spec=aiohttp.ClientSession.request)
    session.request.return_value = mock_response
    return session


@pytest.fixture(name='unauthenticated_api')
def unauthenticated_api(mock_session):
    return smarttub.SmartTub(mock_session)


@pytest.fixture(name='api')
async def api(unauthenticated_api, mock_response):
    api = unauthenticated_api
    mock_response.json.return_value = {
        "access_token": jwt.encode({api.AUTH_ACCOUNT_ID_KEY: ACCOUNT_ID, "exp": time.time() + 3600}, 'secret').decode(),
        "token_type": "Bearer",
        "refresh_token": "refresh1",
    }
    await api.login('username1', 'password1')
    return api


@pytest.mark.asyncio
async def test_login(api, mock_response):
    assert api.account_id == ACCOUNT_ID
    assert api.logged_in is True


@pytest.mark.asyncio
async def test_refresh_token(api, mock_response):
    login_token_expiration = api.token_expires_at
    mock_response.json.return_value = {
        "access_token": jwt.encode({api.AUTH_ACCOUNT_ID_KEY: ACCOUNT_ID, "exp": time.time() + 3601}, 'secret').decode(),
    }
    await api._refresh_token()
    assert api.token_expires_at > login_token_expiration


@pytest.mark.asyncio
async def test_get_account(api, mock_response):
    mock_response.json.return_value = {
        "id": "id1",
        "email": "email1",
    }

    account = await api.get_account()
    assert account.id == "id1"
    assert account.email == "email1"
