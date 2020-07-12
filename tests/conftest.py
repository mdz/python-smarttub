import aiohttp
from unittest.mock import create_autospec

import pytest

import smarttub


ACCOUNT_ID = 'account_id1'


@pytest.fixture(name='mock_response')
def mock_response():
    response = create_autospec(aiohttp.ClientResponse, instance=True)
    response.status = 200
    return response


@pytest.fixture(name='mock_api')
def mock_api():
    api = create_autospec(smarttub.SmartTub, instance=True)
    return api


@pytest.fixture(name='mock_account')
def mock_account(mock_api):
    account = create_autospec(smarttub.Account, instance=True)
    return account
