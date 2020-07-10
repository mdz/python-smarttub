import asyncio
import datetime
import logging
import time

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
    API_KEY = 'TfXKgnYbv81lRdJBQcmGH6lWuA2V6oJp7xPlQRTz'

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

        self.access_token = j['access_token']
        self.access_token_data = jwt.decode(self.access_token, verify=False)
        self.expires_at = time.time() + j['expires_in']
        self.refresh_token = j['refresh_token']
        assert j['token_type'] == 'Bearer'

        self.account_id = self.access_token_data[self.AUTH_ACCOUNT_ID_KEY]
        self.logged_in = True

        logger.debug(f'login successful, username={username}')

    @property
    def _headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}

    def _require_login(self):
        if not self.logged_in:
            raise RuntimeError('not logged in')

    async def request(self, method, path, body=None):
        """Generic method for making an authenticated request to the API

        This is used by resource objects associated with this API object
        """

        self._require_login()

        r = await self._session.request(method, f'{self.API_BASE}/{path}', headers=self._headers, json=body)
        r.raise_for_status()
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
    def __init__(self, _api: SmartTub, **properties):
        self._api = _api
        self.id = properties['id']
        self.email = properties['email']
        self.properties = properties

    async def get_spas(self):
        return await asyncio.gather(*[self.get_spa(spa['id'])
                                      for spa in (await self._api.request('GET', f'spas?ownerId={self.id}'))['content']])

    async def get_spa(self, spa_id: str):
        return Spa(self._api, self, **await self._api.request('GET', f'spas/{spa_id}'))


class Spa:
    SECONDARY_FILTRATION_MODES = {'FREQUENT', 'INFREQUENT', 'AWAY'}
    HEAT_MODES = {'ECONOMY', 'DAY', 'AUTO'}
    LIGHT_MODES = {'PURPLE', 'ORANGE', 'RED', 'YELLOW', 'GREEN', 'AQUA', 'BLUE', 'HIGH_SPEED_WHEEL', 'OFF'}
    TEMPERATURE_FORMATS = ['FAHRENHEIT', 'CELSIUS']
    ENERGY_USAGE_INTERVALS = ['DAY', 'MONTH']

    def __init__(self, _api: SmartTub, account: Account, **properties):
        self._api = _api
        self.account = account
        self.id = properties['id']
        self.brand = properties['brand']
        self.model = properties['model']
        self.properties = properties

    async def request(self, method, resource: str, body=None):
        return await self._api.request(method, f'spas/{self.id}/{resource}', body)

    async def get_status(self) -> dict:
        return await self.request('GET', 'status')

    async def get_pumps(self) -> list:
        return [SpaPump(self._api, self, **pump_info)
                for pump_info in (await self.request('GET', 'pumps'))['pumps']]

    async def get_lights(self) -> list:
        return [SpaLight(self._api, self, **light_info)
                for light_info in (await self.request('GET', 'lights'))['lights']]

    async def get_errors(self) -> list:
        return (await self.request('GET', 'errors'))['content']

    async def get_reminders(self) -> dict:
        # API returns both 'reminders' and 'filters', both seem to be identical
        return [SpaReminder(self._api, self, **reminder_info)
                for reminder_info in (await self.request('GET', 'reminders'))['reminders']]

    async def get_debug_status(self) -> dict:
        return (await self.request('GET', 'debugStatus'))['debugStatus']

    async def get_energy_usage(self, interval: str, start_date: datetime.date, end_date: datetime.date) -> list:
        assert interval in self.ENERGY_USAGE_INTERVALS
        body = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "interval": interval,
        }
        return (await self.request('POST', 'energyUsage', body))['buckets']

    async def set_secondary_filtration_mode(self, mode: str):
        assert mode in self.SECONDARY_FILTRATION_MODES
        body = {
            'secondaryFiltrationConfig': mode
        }
        await self.request('PATCH', 'config', body)

    async def set_heat_mode(self, mode: str):
        assert mode in self.HEAT_MODES
        body = {
            'heatMode': mode
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

    async def set_temperature_format(self, temperature_format: str):
        assert temperature_format in self.TEMPERATURE_MODES
        body = {
            'displayTemperatureFormat': temperature_format
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
    def __init__(self, _api: SmartTub, spa: Spa, **properties):
        self._api = _api
        self.spa = spa
        self.id = properties['id']
        self.speed = properties['speed']
        self.state = properties['state']
        self.type = properties['type']
        self.properties = properties

    async def toggle(self):
        await self.spa.request('POST', f'pumps/{self.id}/toggle')

    def __str__(self):
        return f'<SpaPump {self.id}>'


class SpaLight:
    def __init__(self, _api: SmartTub, spa: Spa, **properties):
        self._api = _api
        self.spa = spa
        self.zone = properties['zone']
        self.color = properties['color']
        self.intensity = properties['intensity']
        self.mode = properties['mode']
        self.properties = properties

    async def set(self, intensity: int, mode: str):
        assert mode in self.LIGHT_MODES
        assert (intensity == 0) == (mode == 'OFF')
        body = {
            'intensity': intensity,
            'mode': mode,
        }
        await self.spa.request('PATCH', f'lights/{self.zone}', body)

    def __str__(self):
        return f'<SpaLight {self.zone}>'


class SpaReminder:
    def __init__(self, _api: SmartTub, spa: Spa, **properties):
        self._api = _api
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


class LoginFailed(RuntimeError):
    pass
