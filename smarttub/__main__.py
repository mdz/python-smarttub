import argparse
import asyncio
import datetime
import logging
from pprint import pprint
import sys

import aiohttp

from . import SmartTub, SpaLight


async def info_command(spas, args):
    for spa in spas:
        print(f"= Spa '{spa.name}' =\n")
        if args.all or args.status or args.location or args.locks:
            status = await spa.get_status_full()

        if args.all or args.status:
            print("== Status ==")
            status_dict = status.properties.copy()
            # redact location for privacy
            location = status_dict.pop("location")
            pprint(status_dict)
            print()

        if args.location:
            # not included in --all
            print(
                f"Location: {location['latitude']} {location['longitude']} (accuracy: {location['accuracy']})\n"
            )

        if args.all or args.pumps:
            print("== Pumps ==")
            for pump in status.pumps:
                print(pump)
            print()

        if args.all or args.lights:
            print("== Lights ==")
            for light in status.lights:
                print(light)
            print()

        if args.all or args.errors:
            print("== Errors ==")
            for error in await spa.get_errors():
                print(error)
            print()

        if args.all or args.reminders:
            print("== Reminders ==")
            for reminder in await spa.get_reminders():
                print(reminder)
            print()

        if args.all or args.locks:
            print("== Locks ==")
            for lock in status.locks.values():
                print(lock)
            print()

        if args.all or args.energy:
            print("== Energy usage ==")
            energy_usage_day = spa.get_energy_usage(
                spa.EnergyUsageInterval.DAY,
                end_date=datetime.date.today(),
                start_date=datetime.date.today() - datetime.timedelta(days=7),
            )
            pprint(await energy_usage_day)
            print()

        if args.all or args.sensors:
            print("== Sensors ==")
            for sensor in status.sensors:
                print(sensor)
            print()

        if args.all or args.debug:
            debug_status = await spa.get_debug_status()
            print("== Debug status ==")
            pprint(debug_status)
            print()


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


asyncio.run(main(sys.argv[1:]))
