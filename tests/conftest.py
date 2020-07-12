import aiohttp
from unittest.mock import AsyncMock, create_autospec

import pytest

import smarttub


ACCOUNT_ID = 'account_id1'


@pytest.fixture(name='mock_response')
def mock_response():
    response = create_autospec(aiohttp.ClientResponse, instance=True)
    response.status = 200
    return response


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


@pytest.fixture(name='mock_api')
def mock_api(mock_session):
    api = create_autospec(smarttub.SmartTub, instance=True)
    return api


@pytest.fixture(name='mock_account')
def mock_account(mock_api):
    account = create_autospec(smarttub.Account, instance=True)
    return account
