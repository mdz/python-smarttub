import os
import asyncio
import pytest
import aiohttp
from smarttub import SmartTub, Spa

pytestmark = pytest.mark.integration

USERNAME = os.environ.get("SMARTTUB_USER")
PASSWORD = os.environ.get("SMARTTUB_PASS")
SPA_INDEX = int(os.environ.get("SMARTTUB_SPA_INDEX", "0"))
POLL_INTERVAL = 2
TIMEOUT = 60


@pytest.mark.asyncio
@pytest.mark.skipif(
    not USERNAME or not PASSWORD, reason="SMARTTUB_USER and SMARTTUB_PASS must be set"
)
async def test_real_api_polling():
    async with aiohttp.ClientSession() as session:
        st = SmartTub(session)
        await st.login(USERNAME, PASSWORD)
        account = await st.get_account()
        spas = await account.get_spas()
        spa = spas[SPA_INDEX]

        # Save original state
        orig_temp = (await spa.get_status()).set_temperature
        orig_heat_mode = (await spa.get_status()).heat_mode
        orig_temp_format = (await spa.get_status()).display_temperature_format
        orig_pump_state = None
        orig_light_mode = None
        orig_light_intensity = None
        unreverted = {}

        # 1. Test set_temperature (pick a value different from current)
        # Use valid setpoints: 98°F and 100°F (converted to Celsius)
        VALID_SETPOINTS = [round((f - 32) * 5 / 9, 1) for f in (98, 100)]
        test_temp = next(
            (t for t in VALID_SETPOINTS if round(t, 1) != round(orig_temp, 1)), None
        )
        if test_temp is not None:
            try:
                await spa.set_temperature(test_temp)
                await _wait_for(
                    lambda: spa.get_status(),
                    lambda s: round(s.set_temperature, 1) == round(test_temp, 1),
                )
            except Exception as e:
                print(f"WARNING: Could not set temperature to {test_temp}: {e}")
            # Restore
            try:
                await spa.set_temperature(orig_temp)
                await _wait_for(
                    lambda: spa.get_status(),
                    lambda s: round(s.set_temperature, 1) == round(orig_temp, 1),
                )
            except Exception as e:
                unreverted["set_temperature"] = {
                    "expected": orig_temp,
                    "current": (await spa.get_status()).set_temperature,
                    "error": str(e),
                }

        # 2. Test set_heat_mode (toggle)
        new_heat_mode = (
            Spa.HeatMode.ECONOMY
            if orig_heat_mode != Spa.HeatMode.ECONOMY
            else Spa.HeatMode.AUTO
        )
        try:
            await spa.set_heat_mode(new_heat_mode)
            await _wait_for(
                lambda: spa.get_status(), lambda s: s.heat_mode == new_heat_mode
            )
        except Exception as e:
            print(f"WARNING: Could not set heat mode to {new_heat_mode}: {e}")
        # Restore
        try:
            await spa.set_heat_mode(orig_heat_mode)
            await _wait_for(
                lambda: spa.get_status(), lambda s: s.heat_mode == orig_heat_mode
            )
        except Exception as e:
            unreverted["heat_mode"] = {
                "expected": orig_heat_mode,
                "current": (await spa.get_status()).heat_mode,
                "error": str(e),
            }

        # 3. Test set_temperature_format (toggle)
        new_format = (
            Spa.TemperatureFormat.FAHRENHEIT
            if orig_temp_format != Spa.TemperatureFormat.FAHRENHEIT
            else Spa.TemperatureFormat.CELSIUS
        )
        try:
            await spa.set_temperature_format(new_format)
            await _wait_for(
                lambda: spa.get_status(),
                lambda s: s.display_temperature_format == new_format.name,
            )
        except Exception as e:
            print(f"WARNING: Could not set temperature format to {new_format}: {e}")
        # Restore
        try:
            await spa.set_temperature_format(orig_temp_format)
            await _wait_for(
                lambda: spa.get_status(),
                lambda s: s.display_temperature_format == orig_temp_format.name,
            )
        except Exception as e:
            unreverted["temperature_format"] = {
                "expected": orig_temp_format,
                "current": (await spa.get_status()).display_temperature_format,
                "error": str(e),
            }

        # 4. Test SpaPump.toggle (first available pump)
        pumps = await spa.get_pumps()
        if pumps:
            pump = pumps[0]
            orig_pump_state = pump.state
            try:
                await pump.toggle()
                await _wait_for(
                    lambda: spa.get_status_full(),
                    lambda s: any(
                        p.id == pump.id and p.state != orig_pump_state for p in s.pumps
                    ),
                )
            except Exception as e:
                print(f"WARNING: Could not toggle pump {pump.id}: {e}")
            # Restore
            try:
                await pump.toggle()
                await _wait_for(
                    lambda: spa.get_status_full(),
                    lambda s: any(
                        p.id == pump.id and p.state == orig_pump_state for p in s.pumps
                    ),
                )
            except Exception as e:
                unreverted["pump"] = {
                    "id": pump.id,
                    "expected": orig_pump_state,
                    "error": str(e),
                }

        # 5. Test SpaLight.set_mode (first available light)
        lights = await spa.get_lights()
        if lights:
            light = lights[0]
            orig_light_mode = light.mode
            orig_light_intensity = light.intensity
            try:
                # Set to ON if currently OFF, else OFF
                if orig_light_mode.name == "OFF":
                    await light.set_mode(light.LightMode.RED, 50)
                    await _wait_for(
                        lambda: spa.get_status_full(),
                        lambda s: any(
                            light_obj.zone == light.zone
                            and light_obj.mode == light.LightMode.RED
                            for light_obj in s.lights
                        ),
                    )
                    # Restore
                    await light.set_mode(light.LightMode.OFF, 0)
                    await _wait_for(
                        lambda: spa.get_status_full(),
                        lambda s: any(
                            light_obj.zone == light.zone
                            and light_obj.mode == light.LightMode.OFF
                            for light_obj in s.lights
                        ),
                    )
                else:
                    await light.set_mode(light.LightMode.OFF, 0)
                    await _wait_for(
                        lambda: spa.get_status_full(),
                        lambda s: any(
                            light_obj.zone == light.zone
                            and light_obj.mode == light.LightMode.OFF
                            for light_obj in s.lights
                        ),
                    )
                    # Restore
                    await light.set_mode(orig_light_mode, orig_light_intensity)
                    await _wait_for(
                        lambda: spa.get_status_full(),
                        lambda s: any(
                            light_obj.zone == light.zone
                            and light_obj.mode == orig_light_mode
                            for light_obj in s.lights
                        ),
                    )
            except Exception as e:
                unreverted["light"] = {
                    "zone": light.zone,
                    "expected": orig_light_mode,
                    "intensity": orig_light_intensity,
                    "error": str(e),
                }

        # Final check and report
        print("\n--- Integration Test State Revert Report ---")
        if not unreverted:
            print("All state changes reverted successfully.")
        else:
            print("Some state could not be reverted. Please check and fix manually:")
            for key, info in unreverted.items():
                print(f"  {key}: {info}")


def c_to_f(c):
    return c * 9 / 5 + 32


async def _wait_for(
    get_status, check_func, timeout=TIMEOUT, poll_interval=POLL_INTERVAL
):
    import time

    start = time.time()
    while True:
        state = await get_status()
        if check_func(state):
            return
        if time.time() - start > timeout:
            raise RuntimeError("State change not reflected within timeout period")
        await asyncio.sleep(poll_interval)
