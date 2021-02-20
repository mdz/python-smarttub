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
        if args.all or args.status:
            print("== Status ==")
            pprint(await spa.get_status())
            print()

        if args.all or args.pumps:
            print("== Pumps ==")
            for pump in await spa.get_pumps():
                print(pump)
            print()

        if args.all or args.lights:
            print("== Lights ==")
            for light in await spa.get_lights():
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

        if args.all or args.energy:
            print("== Energy usage ==")
            energy_usage_day = spa.get_energy_usage(spa.EnergyUsageInterval.DAY, end_date=datetime.date.today(), start_date=datetime.date.today() - datetime.timedelta(days=7))
            pprint(await energy_usage_day)
            print()

        if args.all or args.debug:
            debug_status = await spa.get_debug_status()
            print(f"== Debug status ==\n{debug_status}\n")

        print()


async def set_command(spas, args):
    for spa in spas:
        if args.temperature:
            await spa.set_temperature(38.3)

        if args.light_mode:
            for light in await spa.get_lights():
                await light.set_mode(light.LightModes[args.lights], 25)
                if args.verbosity > 0:
                    print(light)


async def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument("-v", "--verbosity", action="count", default=0)

    subparsers = parser.add_subparsers()
    info_parser = subparsers.add_parser("info")
    info_parser.set_defaults(func=info_command)
    info_parser.add_argument("-a", "--all", action="store_true")
    info_parser.add_argument("--spas", action="store_true")
    info_parser.add_argument("--status", action="store_true")
    info_parser.add_argument("--pumps", action="store_true")
    info_parser.add_argument("--lights", action="store_true")
    info_parser.add_argument("--errors", action="store_true")
    info_parser.add_argument("--reminders", action="store_true")
    info_parser.add_argument("--debug", action="store_true")
    info_parser.add_argument("--energy", action="store_true")

    set_parser = subparsers.add_parser("set")
    set_parser.set_defaults(func=set_command)
    set_parser.add_argument("-l", "--light_mode", choices=[mode.name for mode in SpaLight.LightMode])
    set_parser.add_argument("-t", "--temperature", type=float)

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
