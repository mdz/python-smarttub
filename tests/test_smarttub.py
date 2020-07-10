import unittest
from unittest.mock import create_autospec

import jwt
import requests_mock

import smarttub


class TestSmartTub(unittest.TestCase):
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
        mock.get(f'{self.st.API_BASE}/accounts/{self.ACCOUNT_ID}', json={
            "id": "id1",
            "email": "email1",
        })
        account = self.st.get_account()
        self.assertEqual(account.id, "id1")
        self.assertEqual(account.email, "email1")


class TestAccount(unittest.TestCase):
    def setUp(self):
        self.api = create_autospec(smarttub.SmartTub, instance=True)
        self.account = smarttub.Account(self.api, id='id1', email='email1')

    def test_get_spas(self):
        self.api.request.side_effect = [
                {'content': [{'id': 'sid1'}]},
                {'id': 'sid1', 'brand': 'brand1', 'model': 'model1'}
        ]
        spas = self.account.get_spas()
        self.assertEqual(len(spas), 1)
        spa = spas[0]
        self.assertEqual(spa.id, 'sid1')


class TestSpa(unittest.TestCase):
    def setUp(self):
        self.api = create_autospec(smarttub.SmartTub, instance=True)
        self.account = create_autospec(smarttub.Account, instance=True)
        self.spa = smarttub.Spa(self.api, self.account, id='id1', brand='brand1', model='model1')

    def test_get_status(self):
        self.api.request.return_value = 'status1'
        status = self.spa.get_status()
        self.assertEqual(status, 'status1')

    def test_get_pumps(self):
        self.api.request.return_value = {
            'pumps': [{
                'id': 'pid1',
                'speed': 'speed1',
                'state': 'state1',
                'type': 'type1',
            }]
        }
        pumps = self.spa.get_pumps()
        self.assertEqual(len(pumps), 1)
        pump = pumps[0]
        self.assertEqual(pump.id, 'pid1')

    def test_get_lights(self):
        self.api.request.return_value = {
            'lights': [{
                'color': {'blue': 0, 'green': 0, 'red': 0},
                'intensity': 0,
                'mode': 'OFF',
                'zone': 1,
            }]
        }
        lights = self.spa.get_lights()
        self.assertEqual(len(lights), 1)
        light = lights[0]
        self.assertEqual(light.zone, 1)

    def test_get_errors(self):
        self.api.request.return_value = {'content': []}
        errors = self.spa.get_errors()
        self.assertEqual(len(errors), 0)

    def test_get_reminders(self):
        self.api.request.return_value = {
                'reminders': [{
                    "id": "id1",
                    "lastUpdated": "2020-07-09T06:42:53.857Z",
                    "name": "name1",
                    "remainingDuration": 23,
                    "snoozed": False,
                    "state": "INACTIVE"
                }]
        }
        reminders = self.spa.get_reminders()
        self.assertEqual(len(reminders), 1)
        reminder = reminders[0]
        self.assertEqual(reminder.id, "id1")
        self.assertEqual(reminder.name, "name1")
