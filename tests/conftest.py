from unittest.mock import create_autospec

import pytest

import smarttub


ACCOUNT_ID = "account_id1"


@pytest.fixture
def mock_api():
    api = create_autospec(smarttub.SmartTub, instance=True)
    return api


@pytest.fixture
def mock_spa():
    spa = create_autospec(smarttub.Spa, instance=True)
    return spa
