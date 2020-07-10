import datetime
import logging
import sys
import time

import jwt
import requests

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

    SECONDARY_FILTRATION_MODES = {'FREQUENT', 'INFREQUENT', 'AWAY'}
    HEAT_MODES = {'ECONOMY', 'DAY', 'AUTO'}
    LIGHT_MODES = {'PURPLE', 'ORANGE', 'RED', 'YELLOW', 'GREEN', 'AQUA', 'BLUE', 'HIGH_SPEED_WHEEL', 'OFF'}
    TEMPERATURE_FORMATS = ['FAHRENHEIT', 'CELSIUS']
    ENERGY_USAGE_INTERVALS = ['DAY', 'MONTH']

    def __init__(self):
        self.logged_in = False

    def login(self, username: str, password: str):
        """Authenticate to SmartTub

        This method must be called before any get_ or set_ methods

        username -- the email address for the SmartTub account
        password -- the password for the SmartTub account
        """

        # https://auth0.com/docs/api-auth/tutorials/password-grant
        r = requests.post(
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
        r.raise_for_status()
        j = r.json()

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

    def get_account(self):
        """Retrieve information about the SmartTub account
        """

        self._require_login()
        r = requests.get(f'{self.API_BASE}/accounts/{self.account_id}', headers=self._headers)
        r.raise_for_status()
        j = r.json()
        logger.debug(f'get_account successful: {j}')
        return j

    def get_spas(self):
        """Retrieve the list of spas associated with the account
        """

        self._require_login()
        r = requests.get(f'{self.API_BASE}/spas/?ownerId={self.account_id}', headers=self._headers)
        r.raise_for_status()
        j = r.json()
        logger.debug(f'get_spas successful: {j}')
        return j['content']

    def get_spa(self, spa_id: str):
        """Retrieve details about a spa
        """

        self._require_login()
        r = requests.get(f'{self.API_BASE}/spas/{spa_id}', headers=self._headers)
        r.raise_for_status()
        j = r.json()
        logger.debug(f'get_spa successful: {j}')
        return j

    def _spa_request(self, method, spa_id: str, resource: str, body=None):
        self._require_login()
        url = f'{self.API_BASE}/spas/{spa_id}/{resource}'
        r = requests.request(method, url, headers=self._headers, json=body)
        r.raise_for_status()
        j = r.json()
        logger.debug(f'{method} {resource} successful: {j}')
        return j

    def get_spa_status(self, spa_id: str) -> dict:
        return self._spa_request('GET', spa_id, 'status')

    def get_spa_pumps(self, spa_id: str) -> list:
        return self._spa_request('GET', spa_id, 'pumps')['pumps']

    def get_spa_lights(self, spa_id: str) -> list:
        """Retrieve the status of lights
        """
        return self._spa_request('GET', spa_id, 'lights')['lights']

    def get_spa_errors(self, spa_id: str) -> list:
        return self._spa_request('GET', spa_id, 'errors')['content']

    def get_spa_reminders(self, spa_id: str) -> dict:
        #  -> TypedDict('Reminders', {'filters': dict, 'reminders': dict})
        return self._spa_request('GET', spa_id, 'reminders')

    def get_spa_debug_status(self, spa_id: str) -> dict:
        return self._spa_request('GET', spa_id, 'debugStatus')['debugStatus']

    def get_spa_energy_usage(self, spa_id: str, interval: str, start_date: datetime.date, end_date: datetime.date) -> list:
        assert interval in self.ENERGY_USAGE_INTERVALS
        body = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "interval": interval,
        }
        return self._spa_request('POST', spa_id, 'energyUsage', body)['buckets']

    def set_spa_secondary_filtration_mode(self, spa_id: str, mode: str):
        assert mode in self.SECONDARY_FILTRATION_MODES
        body = {
            'secondaryFiltrationConfig': mode
        }
        self._spa_request('PATCH', spa_id, 'config', body)

    def set_spa_heat_mode(self, spa_id: str, mode: str):
        assert mode in self.HEAT_MODES
        body = {
            'heatMode': mode
        }
        self._spa_request('PATCH', spa_id, 'config', body)

    def set_spa_temperature(self, spa_id: str, temp_c: float):
        body = {
            'setTemperature': temp_c
        }
        self._spa_request('PATCH', spa_id, 'config', body)

    def set_spa_light(self, spa_id: str, light_id: int, intensity: int, mode: str):
        assert mode in self.LIGHT_MODES
        body = {
            'intensity': intensity,
            'mode': mode,
        }
        self._spa_request('PATCH', spa_id, 'config', body)

    def toggle_spa_pump(self, spa_id: str, pump_id: str):
        self._spa_request('POST', spa_id, f'pumps/{pump_id}/toggle')

    def toggle_spa_clearray(self, spa_id: str):
        self._spa_request('POST', spa_id, 'clearray/toggle')

    def set_spa_temperature_format(self, spa_id: str, temperature_format: str):
        assert temperature_format in self.TEMPERATURE_MODES
        body = {
            'displayTemperatureFormat': temperature_format
        }
        self._spa_request('POST', spa_id, 'config', body)

    def set_spa_date_time(self, spa_id: str, date: datetime.date=None, time: datetime.time=None):
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
        self._spa_request('POST', spa_id, body)


if __name__ == '__main__':
    from pprint import pprint
    st = SmartTub()
    st.login(*sys.argv[1:])
    pprint(st.get_account())
    spas = st.get_spas()
    spa_id = spas[0]['id']
    spa = st.get_spa(spa_id)
    pprint(spa)
    status = st.get_spa_status(spa_id)
    pprint(status)
    pumps = st.get_spa_pumps(spa_id)
    pprint(pumps)
    lights = st.get_spa_lights(spa_id)
    pprint(lights)
    errors = st.get_spa_errors(spa_id)
    pprint(errors)
    reminders = st.get_spa_reminders(spa_id)
    pprint(reminders)
    debug_status = st.get_spa_debug_status(spa_id)
    pprint(debug_status)
    energy_usage_day = st.get_spa_energy_usage(spa_id, 'DAY', end_date=datetime.date.today(), start_date=datetime.date.today() - datetime.timedelta(days=7))
    pprint(energy_usage_day)
