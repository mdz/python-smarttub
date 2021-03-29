from unittest.mock import create_autospec

import pytest

import smarttub


ACCOUNT_ID = "account_id1"


@pytest.fixture(name="mock_api")
def mock_api():
    api = create_autospec(smarttub.SmartTub, instance=True)
    return api


@pytest.fixture(name="spa")
def spa(mock_api, mock_account):
    spa = smarttub.Spa(mock_api, mock_account, id="id1", brand="brand1", model="model1")
    return spa
