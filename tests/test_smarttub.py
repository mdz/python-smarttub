import aiohttp
import time
from unittest.mock import AsyncMock, create_autospec

import aiounittest
import jwt

import smarttub


class TestSmartTub(aiounittest.AsyncTestCase):
    ACCOUNT_ID = 'account_id1'

    def setUp(self):
        self.session = self.mock_session()
        self.st = smarttub.SmartTub(self.session)

    @staticmethod
    def mock_session():
        session = create_autospec(aiohttp.ClientSession, instance=True)
        session.get = AsyncMock(spec=aiohttp.ClientSession.get)
        session.post = AsyncMock(spec=aiohttp.ClientSession.post)
        session.patch = AsyncMock(spec=aiohttp.ClientSession.patch)
        session.request = AsyncMock(spec=aiohttp.ClientSession.request)
        return session

    @staticmethod
    def mock_response(json, status=200):
        response = create_autospec(aiohttp.ClientResponse, instance=True)
        response.status = status
        response.json.return_value = json
        return response

    async def login(self):
        self.session.post.return_value = self.mock_response({
            "access_token": jwt.encode({self.st.AUTH_ACCOUNT_ID_KEY: self.ACCOUNT_ID, "exp": time.time() + 3600}, 'secret').decode(),
            "token_type": "Bearer",
            "refresh_token": "refresh1",
        })
        return await self.st.login('username1', 'password1')

    async def test_login(self):
        await self.login()
        self.assertEqual(self.st.account_id, self.ACCOUNT_ID)
        self.assertEqual(self.st.logged_in, True)

    async def test_refresh_token(self):
        await self.login()
        login_token_expiration = self.st.token_expires_at
        self.session.post.return_value = self.mock_response({
            "access_token": jwt.encode({self.st.AUTH_ACCOUNT_ID_KEY: self.ACCOUNT_ID, "exp": time.time() + 3601}, 'secret').decode(),
        })
        await self.st._refresh_token()
        self.assertGreater(self.st.token_expires_at, login_token_expiration)

    async def test_get_account(self):
        await self.login()
        self.session.request.return_value = self.mock_response({
            "id": "id1",
            "email": "email1",
        })

        account = await self.st.get_account()
        self.assertEqual(account.id, "id1")
        self.assertEqual(account.email, "email1")


class TestAccount(aiounittest.AsyncTestCase):
    def setUp(self):
        self.api = create_autospec(smarttub.SmartTub, instance=True)
        self.account = smarttub.Account(self.api, id='id1', email='email1')

    async def test_get_spas(self):
        self.api.request.side_effect = [
            {'content': [{'id': 'sid1'}]},
            {'id': 'sid1', 'brand': 'brand1', 'model': 'model1'}
        ]
        spas = await self.account.get_spas()
        self.assertEqual(len(spas), 1)
        spa = spas[0]
        self.assertEqual(spa.id, 'sid1')


class TestSpa(aiounittest.AsyncTestCase):
    def setUp(self):
        self.api = create_autospec(smarttub.SmartTub, instance=True)
        self.account = create_autospec(smarttub.Account, instance=True)
        self.spa = smarttub.Spa(self.api, self.account, id='id1', brand='brand1', model='model1')

    async def test_get_status(self):
        self.api.request.return_value = 'status1'
        status = await self.spa.get_status()
        self.assertEqual(status, 'status1')

    async def test_get_pumps(self):
        self.api.request.return_value = {
            'pumps': [{
                'id': 'pid1',
                'speed': 'speed1',
                'state': 'state1',
                'type': 'type1',
            }]
        }
        pumps = await self.spa.get_pumps()
        self.assertEqual(len(pumps), 1)
        pump = pumps[0]
        self.assertEqual(pump.id, 'pid1')

    async def test_get_lights(self):
        self.api.request.return_value = {
            'lights': [{
                'color': {'blue': 0, 'green': 0, 'red': 0},
                'intensity': 0,
                'mode': 'OFF',
                'zone': 1,
            }]
        }
        lights = await self.spa.get_lights()
        self.assertEqual(len(lights), 1)
        light = lights[0]
        self.assertEqual(light.zone, 1)

    async def test_get_errors(self):
        self.api.request.return_value = {'content': []}
        errors = await self.spa.get_errors()
        self.assertEqual(len(errors), 0)

    async def test_get_reminders(self):
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
        reminders = await self.spa.get_reminders()
        self.assertEqual(len(reminders), 1)
        reminder = reminders[0]
        self.assertEqual(reminder.id, "id1")
        self.assertEqual(reminder.name, "name1")
