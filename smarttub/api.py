import asyncio
import datetime
from enum import Enum
import logging
import time
from typing import List

import aiohttp
import dateutil.parser
import jwt

logger = logging.getLogger(__name__)


class SmartTub:
    """Interface to the SmartTub API
    """

    AUTH_AUDIENCE = 'https://api.operation-link.com/'
    AUTH_URL = 'https://smarttub.auth0.com/oauth/token'
    AUTH_CLIENT_ID = 'dB7Rcp3rfKKh0vHw2uqkwOZmRb5WNjQC'
    AUTH_REALM = 'Username-Password-Authentication'
    AUTH_ACCOUNT_ID_KEY = 'http://operation-link.com/account_id'

    API_BASE = 'https://api.smarttub.io'

    def __init__(self, session: aiohttp.ClientSession=None):
        self.logged_in = False
        self._session = session or aiohttp.ClientSession()

    async def login(self, username: str, password: str):
        """Authenticate to SmartTub

        This method must be called before any useful work can be done.

        username -- the email address for the SmartTub account
        password -- the password for the SmartTub account
        """

        # https://auth0.com/docs/api-auth/tutorials/password-grant
        r = await self._session.post(
            self.AUTH_URL,
            json={
                "audience": self.AUTH_AUDIENCE,
                "client_id": self.AUTH_CLIENT_ID,
                "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
                "realm": self.AUTH_REALM,
                "scope": "openid email offline_access User Admin",
                "username": username,
                "password": password,
            }
        )
        if r.status == 403:
            raise LoginFailed(r.text)

        r.raise_for_status()
        j = await r.json()

        self._set_access_token(j['access_token'])
        self.refresh_token = j['refresh_token']
        assert j['token_type'] == 'Bearer'

        self.account_id = self.access_token_data[self.AUTH_ACCOUNT_ID_KEY]
        self.logged_in = True

        logger.debug(f'login successful, username={username}')

    @property
    def _headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}

    async def _require_login(self):
        if not self.logged_in:
            raise RuntimeError('not logged in')
        if self.token_expires_at <= time.time():
            await self._refresh_token()

    def _set_access_token(self, token):
        self.access_token = token
        self.access_token_data = jwt.decode(self.access_token, verify=False)
        self.token_expires_at = self.access_token_data['exp']

    async def _refresh_token(self):
        # https://auth0.com/docs/tokens/guides/use-refresh-tokens
        r = await self._session.post(
            self.AUTH_URL,
            json={
                "grant_type": "refresh_token",
                "client_id": self.AUTH_CLIENT_ID,
                "refresh_token": self.refresh_token,
            }
        )
        r.raise_for_status()
        j = await r.json()
        self._set_access_token(j['access_token'])
        logger.debug('token refresh successful')

    async def request(self, method, path, body=None):
        """Generic method for making an authenticated request to the API

        This is used by resource objects associated with this API object
        """

        await self._require_login()

        r = await self._session.request(method, f'{self.API_BASE}/{path}', headers=self._headers, json=body)

        try:
            r.raise_for_status()
        except aiohttp.ClientResponseError as e:
            raise APIError(e)

        if int(r.headers['content-length']) == 0:
            return None
        j = await r.json()

        logger.debug(f'{method} {path} successful: {j}')
        return j

    async def get_account(self) -> 'Account':
        """Retrieve the SmartTub account of the authenticated user
        """

        j = await self.request('GET', f'accounts/{self.account_id}')
        account = Account(self, **j)
        logger.debug(f'get_account successful: {j}')

        return account


class Account:
    def __init__(self, api: SmartTub, **properties):
        self._api = api
        self.id = properties['id']
        self.email = properties['email']
        self.properties = properties

    async def get_spas(self):
        return await asyncio.gather(*[self.get_spa(spa['id'])
                                      for spa in (await self._api.request('GET', f'spas?ownerId={self.id}'))['content']])

    async def get_spa(self, spa_id: str):
        return Spa(self._api, self, **await self._api.request('GET', f'spas/{spa_id}'))

    def __str__(self):
        return f'<Account {self.email}>'


class Spa:
    SecondaryFiltrationMode = Enum('SecondaryFiltrationMode', 'FREQUENT INFREQUENT AWAY')
    HeatMode = Enum('HeatMode', 'ECONOMY DAY AUTO')
    TemperatureFormat = Enum('TemperatureFormat', 'FAHRENHEIT CELSIUS')
    EnergyUsageInterval = Enum('EnergyUsageInterval', 'DAY MONTH')

    def __init__(self, api: SmartTub, account: Account, **properties):
        self._api = api
        self.account = account
        self.id = properties['id']
        self.brand = properties['brand']
        self.model = properties['model']
        self.properties = properties

        self.name = f'{self.brand} {self.model}'

    async def request(self, method, resource: str, body=None):
        return await self._api.request(method, f'spas/{self.id}/{resource}', body)

    async def get_status(self) -> dict:
        """Query the status of the spa.

        Example response:

        {'ambientTemperature': 65.6,
         'blowoutCycle': 'INACTIVE',
         'cleanupCycle': 'INACTIVE',
         'current': {'average': 0.0, 'kwh': 0.48, 'max': 0.0, 'min': 0.0, 'value': 0.0},
         'date': '2021-02-17',
         'demoMode': 'DISABLED',
         'dipSwitches': 8,
         'displayTemperatureFormat': 'FAHRENHEIT',
         'error': {'code': 0, 'description': None, 'title': 'All Clear'},
         'errorCode': 0,
         'fieldsLastUpdated': {'cfstEvent': '2021-02-17T07:24:32.010Z',
                               'errEvent': '2021-02-17T09:10:31.059Z',
                               'heatMode': '2020-07-09T19:40:01.883Z',
                               'locEvent': '2021-02-14T01:12:05.980Z',
                               'online': '2021-02-17T16:59:15.785Z',
                               'rpstEvent': '2021-02-17T15:33:44.539Z',
                               'setTemperature': '2021-02-16T17:54:01.511Z',
                               'sp2stEvent': '2021-02-17T07:24:34.019Z',
                               'spstEvent': '2021-02-17T16:44:26.266Z',
                               'uv': '2021-02-17T06:52:47.019Z',
                               'uvOnDemand': '2021-02-13T04:36:06.268Z',
                               'wcstEvent': '2021-02-17T16:54:29.315Z'},
         'flowSwitch': 'OPEN',
         'heatMode': 'AUTO',
         'heater': 'OFF',
         'highTemperatureLimit': 35.6,
         'lastUpdated': '2021-02-17T16:54:29.443Z',
         'lights': None,
         'location': {'accuracy': 823.0,
                      'latitude': 35.123456,
                      'longitude': -120.123456},
         'locks': {'access': 'UNLOCKED',
                   'maintenance': 'UNLOCKED',
                   'spa': 'UNLOCKED',
                   'temperature': 'UNLOCKED'},
         'online': True,
         'ozone': 'OFF',
         'primaryFiltration': {'cycle': 1,
                               'duration': 4,
                               'lastUpdated': '2021-01-20T11:38:57.014Z',
                               'mode': 'NORMAL',
                               'startHour': 2,
                               'status': 'INACTIVE'},
         'pumps': None,
         'secondaryFiltration': {'lastUpdated': '2020-07-09T19:39:52.961Z',
                                 'mode': 'AWAY',
                                 'status': 'INACTIVE'},
         'setTemperature': 38.3,
         'state': 'NORMAL',
         'time': '00:36:00',
         'timeFormat': 'HOURS_12',
         'timeSet': None,
         'timezone': None,
         'uv': 'OFF',
         'uvOnDemand': 'OFF',
         'versions': {'balboa': '1.06', 'controller': '1.28', 'jacuzziLink': '53'},
         'water': {'oxidationReductionPotential': 604,
                   'ph': 7.01,
                   'temperature': 38.3,
                   'temperatureLastUpdated': '2021-02-17T14:15:26.694Z',
                   'turbidity': 0.01},
         'watercare': None}
        """
        return await self.request('GET', 'status')

    async def get_pumps(self) -> List['SpaPump']:
        return [SpaPump(self, **pump_info)
                for pump_info in (await self.request('GET', 'pumps'))['pumps']]

    async def get_lights(self) -> List['SpaLight']:
        return [SpaLight(self, **light_info)
                for light_info in (await self.request('GET', 'lights'))['lights']]

    async def get_errors(self) -> List['SpaError']:
        return [SpaError(self, **error_info)
                for error_info in (await self.request('GET', 'errors'))['content']]

    async def get_reminders(self) -> List['SpaReminder']:
        # API returns both 'reminders' and 'filters', both seem to be identical
        return [SpaReminder(self, **reminder_info)
                for reminder_info in (await self.request('GET', 'reminders'))['reminders']]

    async def get_debug_status(self) -> dict:
        return (await self.request('GET', 'debugStatus'))['debugStatus']

    async def get_energy_usage(self, interval: EnergyUsageInterval, start_date: datetime.date, end_date: datetime.date) -> list:
        body = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "interval": interval.name,
        }
        return (await self.request('POST', 'energyUsage', body))['buckets']

    async def set_secondary_filtration_mode(self, mode: SecondaryFiltrationMode):
        body = {
            'secondaryFiltrationConfig': mode.name
        }
        await self.request('PATCH', 'config', body)

    async def set_heat_mode(self, mode: HeatMode):
        body = {
            'heatMode': mode.name
        }
        await self.request('PATCH', 'config', body)

    async def set_temperature(self, temp_c: float):
        body = {
            # responds with 500 if given more than 1 decimal point
            'setTemperature': round(temp_c, 1)
        }
        await self.request('PATCH', 'config', body)

    async def toggle_clearray(self, str):
        await self.request('POST', 'clearray/toggle')

    async def set_temperature_format(self, temperature_format: TemperatureFormat):
        body = {
            'displayTemperatureFormat': temperature_format.name
        }
        await self.request('POST', 'config', body)

    async def set_date_time(self, date: datetime.date=None, time: datetime.time=None):
        """Set the spa date, time, or both
        """

        assert date is not None or time is not None
        config = {}
        if date is not None:
            config['date'] = date.isoformat()
        if time is not None:
            config['time'] = time.isoformat('minutes')
        body = {
            'dateTimeConfig': config
        }
        await self.request('POST', body)

    def __str__(self):
        return f'<Spa {self.id}>'


class SpaPump:
    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.id = properties['id']
        self.speed = properties['speed']
        self.state = properties['state']
        self.type = properties['type']
        self.properties = properties

    async def toggle(self):
        await self.spa.request('POST', f'pumps/{self.id}/toggle')

    def __str__(self):
        return f'<SpaPump {self.id}: {self.type}={self.state}>'


class SpaLight:
    LightMode = Enum('LightMode', 'PURPLE ORANGE RED YELLOW GREEN AQUA BLUE HIGH_SPEED_WHEEL OFF')

    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.zone = properties['zone']

        color = properties['color']
        self.red = color['red']
        self.green = color['green']
        self.blue = color['blue']
        self.white = color['white']

        self.intensity = properties['intensity']
        self.mode = properties['mode']
        self.properties = properties

    async def set_mode(self, mode: LightMode, intensity: int):
        assert (intensity == 0) == (mode == self.LightMode.OFF)

        body = {
            'intensity': intensity,
            'mode': mode.name,
        }
        await self.spa.request('PATCH', f'lights/{self.zone}', body)

    def __str__(self):
        return f'<SpaLight {self.zone}: {self.red}/{self.green}/{self.blue}/{self.white}>'


class SpaReminder:
    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.id = properties['id']
        self.last_updated = dateutil.parser.isoparse(properties['lastUpdated'])
        self.name = properties['name']
        self.remaining_days = properties['remainingDuration']
        self.snoozed = properties['snoozed']
        self.state = properties['state']

    # TODO: snoozing

    def __str__(self):
        return f'<SpaReminder {self.id}>'


class SpaError:
    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.code = properties['code']
        self.title = properties['title']
        self.description = properties['description']
        self.created_at = dateutil.parser.isoparse(properties['createdAt'])
        self.updated_at = dateutil.parser.isoparse(properties['updatedAt'])
        self.active = properties['active']
        self.error_type = properties['errorType']

    def __str__(self):
        return f'<SpaError {self.title}>'


class LoginFailed(RuntimeError):
    pass


class APIError(RuntimeError):
    pass
