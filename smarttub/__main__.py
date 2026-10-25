import argparse
import asyncio
import datetime
import logging
from pprint import pprint
import sys

import aiohttp

from . import SmartTub, SpaLight


async def _section(title, fetch):
    print(f"== {title} ==")
    try:
        pprint(await fetch())
    except Exception as err:
        print(f"Error: {type(err).__name__}: {err}")
    print()


async def info_command(spas, args):
    for spa in spas:
        print(f"= Spa '{spa.name}' =\n")

        status = None
        status_error = None
        if args.all or any(
            (
                args.status,
                args.location,
                args.pumps,
                args.lights,
                args.locks,
                args.sensors,
            )
        ):
            try:
                status = await spa.get_status_full_raw()
            except Exception as err:
                status_error = f"Error: {type(err).__name__}: {err}"

        def from_status(fetch):
            async def inner():
                if status is None:
                    raise RuntimeError(status_error)
                return fetch(status)

            return inner

        if args.all or args.status:
            # location is redacted for privacy unless --location is given
            await _section(
                "Status",
                from_status(lambda s: {k: v for k, v in s.items() if k != "location"}),
            )

        if args.location:
            # not included in --all
            await _section("Location", from_status(lambda s: s["location"]))

        if args.all or args.pumps:
            await _section("Pumps", from_status(lambda s: s.get("pumps")))

        if args.all or args.lights:
            await _section("Lights", from_status(lambda s: s.get("lights")))

        if args.all or args.errors:
            await _section("Errors", spa.get_errors_raw)

        if args.all or args.reminders:
            await _section("Reminders", spa.get_reminders_raw)

        if args.all or args.locks:
            await _section("Locks", from_status(lambda s: s.get("locks")))

        if args.all or args.energy:
            await _section(
                "Energy usage",
                lambda: spa.get_energy_usage(
                    spa.EnergyUsageInterval.DAY,
                    end_date=datetime.date.today(),
                    start_date=datetime.date.today() - datetime.timedelta(days=7),
                ),
            )

        if args.all or args.sensors:
            await _section("Sensors", from_status(lambda s: s.get("sensors")))

        if args.all or args.debug:
            await _section("Debug status", spa.get_debug_status)


async def set_command(spas, args):
    for spa in spas:
        if args.temperature:
            await spa.set_temperature(args.temperature)

        if args.light_mode:
            for light in await spa.get_lights():
                if args.verbosity > 0:
                    print(light)
                mode = light.LightMode[args.light_mode]
                if mode == light.LightMode.OFF:
                    await light.set_mode(mode, 0)
                else:
                    await light.set_mode(mode, 50)

        if args.snooze_reminder:
            reminder_id, days = args.snooze_reminder
            days = int(days)
            reminder = next(
                reminder
                for reminder in await spa.get_reminders()
                if reminder.id == reminder_id
            )
            await reminder.snooze(days)

        if args.reset_reminder:
            reminder_id, days = args.reset_reminder
            days = int(days)
            reminder = next(
                reminder
                for reminder in await spa.get_reminders()
                if reminder.id == reminder_id
            )
            await reminder.reset(days)

        if args.lock:
            status = await spa.get_status()
            lock = status.locks[args.lock.lower()]
            await lock.lock()
            print("OK")

        if args.unlock:
            status = await spa.get_status()
            lock = status.locks[args.unlock.lower()]
            await lock.unlock()
            print("OK")


async def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u", "--username", required=True, help="SmartTub account email"
    )
    parser.add_argument(
        "-p", "--password", required=True, help="SmartTub account password"
    )
    parser.add_argument("-v", "--verbosity", action="count", default=0)
    subparsers = parser.add_subparsers()

    info_parser = subparsers.add_parser("info", help="Show information about the spa")
    info_parser.set_defaults(func=info_command)
    info_parser.add_argument(
        "-a", "--all", action="store_true", help="Show all info except location"
    )
    info_parser.add_argument("--spas", action="store_true")
    info_parser.add_argument("--status", action="store_true")
    info_parser.add_argument(
        "--location", action="store_true", help="Show GPS location"
    )
    info_parser.add_argument("--pumps", action="store_true")
    info_parser.add_argument("--lights", action="store_true")
    info_parser.add_argument("--errors", action="store_true")
    info_parser.add_argument("--reminders", action="store_true")
    info_parser.add_argument("--locks", action="store_true")
    info_parser.add_argument("--debug", action="store_true")
    info_parser.add_argument("--sensors", action="store_true")
    info_parser.add_argument("--energy", action="store_true")

    set_parser = subparsers.add_parser("set", help="Change settings on the spa")
    set_parser.set_defaults(func=set_command)
    set_parser.add_argument(
        "-l", "--light_mode", choices=[mode.name for mode in SpaLight.LightMode]
    )
    set_parser.add_argument("-t", "--temperature", type=float)
    # TODO: should enforce types of str, int
    set_parser.add_argument(
        "--snooze-reminder",
        nargs=2,
        help="Snooze a reminder",
        metavar=("REMINDER_ID", "DAYS"),
    )
    # TODO: should enforce types of str, int
    set_parser.add_argument(
        "--reset-reminder",
        nargs=2,
        help="Reset a reminder",
        metavar=("REMINDER_ID", "DAYS"),
    )
    set_parser.add_argument("--lock", type=str)
    set_parser.add_argument("--unlock", type=str)

    args = parser.parse_args(argv)

    if args.verbosity > 1:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level)

    async with aiohttp.ClientSession() as session:
        st = SmartTub(session)
        await st.login(args.username, args.password)

        account = await st.get_account()

        spas = await account.get_spas()
        await args.func(spas, args)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
