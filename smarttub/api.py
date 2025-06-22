import asyncio
import datetime
from enum import Enum
import logging
import time
from typing import List

import aiohttp
import dateutil.parser
from inflection import underscore
import jwt

logger = logging.getLogger(__name__)


class SmartTub:
    """Interface to the SmartTub API"""

    AUTH_AUDIENCE = "https://api.operation-link.com/"
    AUTH_URL = "https://smarttub.auth0.com/oauth/token"
    AUTH_CLIENT_ID = "dB7Rcp3rfKKh0vHw2uqkwOZmRb5WNjQC"
    AUTH_REALM = "Username-Password-Authentication"
    AUTH_ACCOUNT_ID_KEY = "http://operation-link.com/account_id"
    AUTH_GRANT_TYPE = "http://auth0.com/oauth/grant-type/password-realm"
    AUTH_SCOPE = "openid email offline_access User Admin"

    API_BASE = "https://api.smarttub.io"

    def __init__(self, session: aiohttp.ClientSession = None):
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
                "grant_type": self.AUTH_GRANT_TYPE,
                "realm": self.AUTH_REALM,
                "scope": self.AUTH_SCOPE,
                "username": username,
                "password": password,
            },
        )
        if r.status == 403:
            raise LoginFailed(r.text)

        r.raise_for_status()
        j = await r.json()

        self._set_access_token(j["access_token"])
        self.refresh_token = j["refresh_token"]
        assert j["token_type"] == "Bearer"

        self.account_id = self.access_token_data[self.AUTH_ACCOUNT_ID_KEY]
        self.logged_in = True

        logger.debug(f"login successful, username={username}")

    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _require_login(self):
        if not self.logged_in:
            raise RuntimeError("not logged in")
        if self.token_expires_at <= time.time():
            await self._refresh_token()

    def _set_access_token(self, token):
        self.access_token = token
        self.access_token_data = jwt.decode(
            self.access_token,
            algorithms=["HS256"],
            options={"verify_signature": False, "verify": False},
        )
        self.token_expires_at = self.access_token_data["exp"]

    async def _refresh_token(self):
        # https://auth0.com/docs/tokens/guides/use-refresh-tokens
        r = await self._session.post(
            self.AUTH_URL,
            json={
                "grant_type": "refresh_token",
                "client_id": self.AUTH_CLIENT_ID,
                "refresh_token": self.refresh_token,
            },
        )
        r.raise_for_status()
        j = await r.json()
        self._set_access_token(j["access_token"])
        logger.debug("token refresh successful")

    async def request(self, method, path, body=None):
        """Generic method for making an authenticated request to the API

        This is used by resource objects associated with this API object
        """

        await self._require_login()

        r = await self._session.request(
            method, f"{self.API_BASE}/{path}", headers=self._headers, json=body
        )

        try:
            r.raise_for_status()
        except aiohttp.ClientResponseError as e:
            raise APIError(e)

        if int(r.headers["content-length"]) == 0:
            ret = None
        else:
            ret = await r.json()

        logger.debug(f"{method} {path} successful: {ret}")

        return ret

    async def get_account(self) -> "Account":
        """Retrieve the SmartTub account of the authenticated user"""

        j = await self.request("GET", f"accounts/{self.account_id}")
        account = Account(self, **j)
        logger.debug(f"get_account successful: {j}")

        return account


class Account:
    def __init__(self, api: SmartTub, **properties):
        self._api = api
        self.id = properties["id"]
        self.email = properties["email"]
        self.properties = properties

    async def get_spas(self):
        return await asyncio.gather(
            *[
                self.get_spa(spa["id"])
                for spa in (await self._api.request("GET", f"spas?ownerId={self.id}"))[
                    "content"
                ]
            ]
        )

    async def get_spa(self, spa_id: str):
        return Spa(self._api, self, **await self._api.request("GET", f"spas/{spa_id}"))

    def __str__(self):
        return f"<Account {self.email}>"


class Spa:
    HeatMode = Enum("HeatMode", "ECONOMY DAY AUTO READY REST")
    TemperatureFormat = Enum("TemperatureFormat", "FAHRENHEIT CELSIUS")
    EnergyUsageInterval = Enum("EnergyUsageInterval", "DAY MONTH")

    def __init__(self, api: SmartTub, account: Account, **properties):
        self._api = api
        self.account = account
        self.id = properties["id"]
        self.brand = properties["brand"]
        self.model = properties["model"]
        self.properties = properties

        self.name = f"{self.brand} {self.model}"

    async def request(self, method, resource: str, body=None):
        return await self._api.request(method, f"spas/{self.id}/{resource}", body)

    async def _wait_for_state_change(
        self, check_func, timeout=10, get_status_method=None
    ):
        """Wait for a state change to be reflected in the API.

        Args:
            check_func: A function that takes a SpaState and returns True if the desired state is reached
            timeout: Maximum time to wait in seconds
            get_status_method: A method to call to get the current state if needed

        Returns:
            The final SpaState after the change is complete

        Raises:
            RuntimeError if the state change is not reflected within the timeout period
        """
        start_time = datetime.datetime.now().timestamp()
        while True:
            state = await self.get_status()
            if check_func(state):
                return state

            if datetime.datetime.now().timestamp() - start_time > timeout:
                raise RuntimeError("State change not reflected within timeout period")

            await asyncio.sleep(0.5)

            if get_status_method:
                state = await get_status_method()

    async def get_status(self) -> "SpaState":
        """Query the status of the spa."""
        return SpaState(self, **await self.request("GET", "status"))

    async def get_pumps(self) -> List["SpaPump"]:
        return [
            SpaPump(self, **pump_info)
            for pump_info in (await self.request("GET", "pumps"))["pumps"]
        ]

    async def get_lights(self) -> List["SpaLight"]:
        return [
            SpaLight(self, **light_info)
            for light_info in (await self.request("GET", "lights"))["lights"]
        ]

    async def get_errors(self) -> List["SpaError"]:
        return [
            SpaError(self, **error_info)
            for error_info in (await self.request("GET", "errors"))["content"]
        ]

    async def get_reminders(self) -> List["SpaReminder"]:
        # API returns both 'reminders' and 'filters', both seem to be identical
        return [
            SpaReminder(self, **reminder_info)
            for reminder_info in (await self.request("GET", "reminders"))["reminders"]
        ]

    async def get_status_full(self) -> "SpaStateFull":
        """Retrieves the state of lights and pumps in addition to what get_status does."""
        full_status = await self.request("GET", "fullStatus")
        try:
            return SpaStateFull(self, full_status)
        except Exception:
            logger.error(f"Failed to parse fullStatus response: {full_status}")
            raise

    async def get_debug_status(self) -> dict:
        return (await self.request("GET", "debugStatus"))["debugStatus"]

    async def get_energy_usage(
        self,
        interval: EnergyUsageInterval,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list:
        body = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "interval": interval.name,
        }
        return (await self.request("POST", "energyUsage", body))["buckets"]

    async def set_heat_mode(self, mode: HeatMode):
        body = {"heatMode": mode.name}
        await self.request("PATCH", "config", body)
        await self._wait_for_state_change(lambda state: state.heat_mode == mode)

    async def set_temperature(self, temp_c: float):
        body = {
            # responds with 500 if given more than 1 decimal point
            "setTemperature": round(temp_c, 1)
        }
        await self.request("PATCH", "config", body)
        await self._wait_for_state_change(
            lambda state: state.set_temperature == round(temp_c, 1)
        )

    async def toggle_clearray(self):
        await self.request("POST", "clearray/toggle")
        # No need to wait for state change as this is a toggle operation

    async def set_temperature_format(self, temperature_format: TemperatureFormat):
        body = {"displayTemperatureFormat": temperature_format.name}
        await self.request("POST", "config", body)
        await self._wait_for_state_change(
            lambda state: state.display_temperature_format == temperature_format.name
        )

    async def set_date_time(
        self, date: datetime.date = None, time: datetime.time = None
    ):
        """Set the spa date, time, or both"""

        if date is None and time is None:
            raise ValueError("at least one of date or time must be specified")
        config = {}
        if date is not None:
            config["date"] = date.isoformat()
        if time is not None:
            config["time"] = time.isoformat("minutes")
        body = {"dateTimeConfig": config}
        await self.request("POST", "config", body)
        # No need to wait for state change as this is a one-time operation

    def __str__(self):
        return f"<Spa {self.id}>"


class SpaState:
    CycleStatus = Enum("CycleStatus", "INACTIVE ACTIVE")

    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.properties = properties.copy()
        self._prop("ambientTemperature")
        self._prop("blowoutCycle", constructor=lambda x: self.CycleStatus[x])
        self._prop("cleanupCycle", constructor=lambda x: self.CycleStatus[x])
        self._prop("current")
        self._prop("date", constructor=dateutil.parser.isoparse)
        self._prop("demoMode")
        self._prop("dipSwitches")
        self._prop("displayTemperatureFormat")
        self._prop("error")
        self._prop("errorCode")
        self._prop(
            "fieldsLastUpdated",
            constructor=lambda d: {
                k: dateutil.parser.isoparse(v) if v is not None else None
                for k, v in d.items()
            },
        )
        self._prop("flowSwitch")
        self._prop("heatMode", constructor=lambda x: Spa.HeatMode[x])
        self._prop("heater")
        self._prop("highTemperatureLimit")
        self._prop("lastUpdated", constructor=dateutil.parser.isoparse)
        self._prop("lights")  # seems to be None even when there are lights?
        self._prop("location")
        self._prop(
            "locks",
            constructor=lambda x: {
                k: SpaLock(self.spa, kind=k, state=v) for k, v in x.items()
            },
        )
        self._prop("online")
        self._prop("ozone")
        self._prop(
            "primaryFiltration",
            constructor=lambda p: SpaPrimaryFiltrationCycle(self.spa, **p),
        )
        self._prop(
            "secondaryFiltration",
            constructor=lambda p: SpaSecondaryFiltrationCycle(self.spa, **p),
        )
        self._prop("setTemperature")
        self._prop("state")
        self._prop("time", constructor=datetime.time.fromisoformat)
        self._prop("timeFormat")
        self._prop("timeSet")  # ?
        self._prop("timezone")  # ?
        self._prop("uv")
        self._prop("uvOnDemand")
        self._prop("versions")
        self._prop("water", constructor=lambda p: SpaWaterState(self.spa, **p))
        self._prop("watercare")

    def _prop(
        self,
        json_key,
        instance_variable_name=None,
        constructor=None,
    ):
        """Set an instance variable corresponding to the specified JSON property

        Arguments:
            json_key -- a key in the self.properties map
            instance_variable_name -- the name of the variable to set
            constructor -- a callable which accepts the raw value as an argument, and returns an appropriate internal representation (e.g. enum)
        """

        if instance_variable_name is None:
            instance_variable_name = underscore(json_key)
        if json_key in self.properties:
            if constructor is None:
                setattr(self, instance_variable_name, self.properties[json_key])
            else:
                # if value is None, skip constructor
                if self.properties[json_key] is None:
                    setattr(self, instance_variable_name, None)
                else:
                    setattr(
                        self,
                        instance_variable_name,
                        constructor(self.properties[json_key]),
                    )
        else:
            setattr(self, instance_variable_name, None)

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.properties}>"


class SpaStateFull(SpaState):
    def __init__(self, spa: Spa, state: dict):
        super().__init__(spa, **state)
        self.lights = [
            SpaLight(spa, **light_props) for light_props in self.properties["lights"]
        ]
        self.pumps = [
            SpaPump(spa, **pump_props) for pump_props in self.properties["pumps"]
        ]
        self.sensors = [
            SpaSensor(spa, **sensor_props)
            for sensor_props in self.properties.get("sensors", [])
        ]


class SpaWaterState(SpaState):
    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.properties = properties.copy()

        self._prop("temperature")
        self._prop("temperatureLastUpdated", constructor=dateutil.parser.isoparse)


class SpaPrimaryFiltrationCycle(SpaState):
    PrimaryFiltrationMode = Enum("PrimaryFiltrationMode", "NORMAL NANO_MODE")

    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.properties = properties.copy()

        self._prop("cycle")
        self._prop("duration")
        self._prop("lastUpdated", constructor=dateutil.parser.isoparse)
        self._prop("mode", constructor=lambda x: self.PrimaryFiltrationMode[x])
        self._prop("startHour")
        self._prop("status", constructor=lambda x: self.CycleStatus[x])

    async def set(self, cycle=None, duration=None, mode=None, start_hour=None):
        body = {
            "primaryFiltrationConfig": {
                "cycle": cycle if cycle is not None else self.cycle,
                "duration": duration if duration is not None else self.duration,
                "mode": mode.name if mode is not None else self.mode.name,
                "startHour": start_hour if start_hour is not None else self.start_hour,
            }
        }
        await self.spa.request("PATCH", "config", body)


class SpaSecondaryFiltrationCycle(SpaState):
    SecondaryFiltrationMode = Enum(
        "SecondaryFiltrationMode", "AWAY FREQUENT INFREQUENT"
    )

    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.properties = properties.copy()

        self._prop("lastUpdated", constructor=dateutil.parser.isoparse)
        self._prop("mode", constructor=lambda x: self.SecondaryFiltrationMode[x])
        self._prop("status", constructor=lambda x: self.CycleStatus[x])

    async def set_mode(self, mode: SecondaryFiltrationMode):
        body = {"secondaryFiltrationConfig": mode.name}
        await self.spa.request("PATCH", "config", body)


class SpaPump:
    PumpState = Enum("PumpState", "OFF LOW HIGH")
    PumpType = Enum("PumpType", "BLOWER CIRCULATION JET")

    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.id = properties["id"]
        self.speed = properties["speed"]
        self.state = self.PumpState[properties["state"]]
        self.type = self.PumpType[properties["type"]]
        self.properties = properties

    async def toggle(self):
        # For toggle, we need to wait for the state to change from its current state
        current_state = self.state
        await self.spa.request("POST", f"pumps/{self.id}/toggle")
        await self.spa._wait_for_state_change(
            lambda state: any(
                pump.state != current_state
                for pump in state.pumps
                if pump.id == self.id
            ),
            get_status_method=self.spa.get_status_full,
        )

    def __str__(self):
        return f"<SpaPump {self.id}: {self.type.name}={self.state.name}>"


class SpaLight:
    LightMode = Enum(
        "LightMode",
        "PURPLE ORANGE RED YELLOW GREEN AQUA BLUE WHITE AMBER HIGH_SPEED_COLOR_WHEEL HIGH_SPEED_WHEEL LOW_SPEED_WHEEL FULL_DYNAMIC_RGB AUTO_TIMER_EXTERIOR PARTY COLOR_WHEEL OFF ON",
    )

    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.zone = properties["zone"]

        color = properties["color"]
        self.red = color["red"]
        self.green = color["green"]
        self.blue = color["blue"]
        self.white = color["white"]

        self.intensity = properties["intensity"]
        self.mode = self.LightMode[properties["mode"]]
        self.properties = properties

    async def set_mode(self, mode: LightMode, intensity: int):
        assert (intensity == 0) == (mode == self.LightMode.OFF)

        body = {
            "intensity": intensity,
            "mode": mode.name,
        }
        await self.spa.request("PATCH", f"lights/{self.zone}", body)
        await self.spa._wait_for_state_change(
            lambda state: any(
                light.mode == mode and light.intensity == intensity
                for light in state.lights
                if light.zone == self.zone
            ),
            get_status_method=self.spa.get_status_full,
        )

    async def turn_off(self):
        await self.set_mode(self.LightMode.OFF, 0)

    def __str__(self):
        return f"<SpaLight {self.zone}: {self.mode.name} (R {self.red}/G {self.green}/B {self.blue}/W {self.white}) @ {self.intensity}>"


class SpaReminder:
    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.id = properties["id"]
        self.name = properties["name"]
        self.remaining_days = properties["remainingDuration"]
        self.snoozed = properties["snoozed"]
        self.state = properties["state"]
        self.last_updated = None

        last_updated_str = properties.get("lastUpdated")
        if last_updated_str is not None:
            self.last_updated = dateutil.parser.isoparse(last_updated_str)

    async def snooze(self, days: int):
        body = {"remainingDuration": days}
        await self.spa.request("PATCH", f"reminders/{self.id}", body)

    async def reset(self, days: int):
        body = {"remainingDuration": days, "reset": True}
        await self.spa.request("PATCH", f"reminders/{self.id}", body)

    def __str__(self):
        return f"<SpaReminder {self.id}: {self.state}/{self.remaining_days}/{self.snoozed}>"


class SpaError:
    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.code = properties["code"]
        self.title = properties["title"]
        self.description = properties["description"]
        self.created_at = dateutil.parser.isoparse(properties["createdAt"])
        self.updated_at = dateutil.parser.isoparse(properties["updatedAt"])
        self.active = properties["active"]
        self.error_type = properties["errorType"]

    def __str__(self):
        return f"<SpaError {self.title}>"


class SpaLock:
    CODE = "0772"

    def __init__(self, spa: Spa, kind: str, state: str):
        self.spa = spa
        self.kind = kind
        self.state = state

    async def lock(self):
        if self.state != "LOCKED":
            await self.spa.request(
                "POST",
                "lock",
                {
                    "type": self.kind.upper(),
                    "code": self.CODE,
                },
            )

    async def unlock(self):
        if self.state != "UNLOCKED":
            await self.spa.request(
                "POST",
                "unlock",
                {
                    "type": self.kind.upper(),
                    "code": self.CODE,
                },
            )

    def __str__(self):
        return f"<SpaLock {self.kind}: {self.state}>"


class SpaSensor:
    def __init__(self, spa: Spa, **properties):
        self.spa = spa
        self.address = properties["address"]
        self.name = properties["name"]
        self.type = properties["type"]
        self.subType = properties["subType"]

        self.magnet = properties["magnet"]
        self.pressure = properties["pressure"]
        self.motion = properties["motion"]
        self.fill_drain = properties["fill_drain"]

    def __str__(self):
        return f"<SpaSensor {self.name} ({self.type})"


class LoginFailed(RuntimeError):
    pass


class APIError(RuntimeError):
    pass
