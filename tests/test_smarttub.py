import unittest

import jwt
import requests_mock

import smarttub


class TestAPI(unittest.TestCase):
    ACCOUNT_ID = 'account_id1'

    def setUp(self):
        self.st = smarttub.SmartTub()

    def login(self, mock):
        mock.post(self.st.AUTH_URL, json={
            "access_token": jwt.encode({self.st.AUTH_ACCOUNT_ID_KEY: self.ACCOUNT_ID}, 'secret').decode(),
            "token_type": "Bearer",
            "expires_in": 86400,
            "refresh_token": "refresh1",
        })
        self.st.login('username1', 'password1')

    @requests_mock.Mocker()
    def test_login(self, mock):
        self.login(mock)
        self.assertEqual(self.st.account_id, self.ACCOUNT_ID)
        self.assertEqual(self.st.logged_in, True)

    @requests_mock.Mocker()
    def test_get_account(self, mock):
        self.login(mock)
        mock.get(f'{self.st.API_BASE}/accounts/{self.ACCOUNT_ID}', json="stuff")
        account = self.st.get_account()
        self.assertEqual(account, "stuff")

    @requests_mock.Mocker()
    def test_get_spas(self, mock):
        self.login(mock)
        mock.get(f'{self.st.API_BASE}/spas/?ownerId={self.ACCOUNT_ID}', json={"content": "stuff"})
        spas = self.st.get_spas()
        self.assertEqual(spas, "stuff")

    @requests_mock.Mocker()
    def test_get_spa(self, mock):
        self.login(mock)
        mock.get(f'{self.st.API_BASE}/spas/id1', json='stuff')
        spas = self.st.get_spa('id1')
        self.assertEqual(spas, "stuff")

