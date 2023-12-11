#!/usr/bin/env python3

"""
Twinkly Twinkly Little Star
https://github.com/jschlyter/ttls

Copyright (c) 2019 Jakob Schlyter. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import argparse
import asyncio
import json
import logging
import re
import sys

from .client import (
    TWINKLY_MODES,
    TWINKLY_MUSIC_DRIVERS,
    TWINKLY_MUSIC_DRIVERS_OFFICIAL,
    TWINKLY_MUSIC_DRIVERS_UNOFFICIAL,
    Twinkly,
)
from .colours import TwinklyColour

logger = logging.getLogger(__name__)


async def command_name(t: Twinkly, args: argparse.Namespace):
    if args.name is None:
        return await t.get_name()
    return await t.set_name(args.name)


async def command_network(t: Twinkly, args: argparse.Namespace):
    return await t.get_network_status()


async def command_firmware(t: Twinkly, args: argparse.Namespace):
    return await t.get_firmware_version()


async def command_details(t: Twinkly, args: argparse.Namespace):
    return await t.get_details()


async def command_power(t: Twinkly, args: argparse.Namespace):
    if args.on:
        return await t.turn_on()
    elif args.off:
        return await t.turn_off()
    else:
        on = await t.is_on()
        if on:
            return "on"
        else:
            return "off"


async def command_brightness(t: Twinkly, args: argparse.Namespace):
    if args.pct is None:
        return await t.get_brightness()
    return await t.set_brightness(args.pct)


async def command_mode(t: Twinkly, args: argparse.Namespace):
    if args.mode is None:
        return await t.get_mode()
    return await t.set_mode(args.mode)


async def command_mqtt(t: Twinkly, args: argparse.Namespace):
    if args.mqtt_json is None:
        return await t.get_mqtt()
    data = json.loads(args.mqtt_json)
    return await t.set_mqtt(data)


async def command_movie(t: Twinkly, args: argparse.Namespace):
    if args.movie_file is None:
        return await t.get_movie_config()
    with open(args.movie_file, "rb") as f:
        movie = f.read()
    await t.interview()
    params = {
        "frame_delay": args.movie_delay,
        "leds_number": t.length,
        "frames_number": int(len(movie) / 3 / t.length),
    }
    await t.set_mode("movie")
    await t.set_movie_config(params)
    return await t.upload_movie(movie)


async def command_static(t: Twinkly, args: argparse.Namespace):
    await t.interview()
    m = re.match(r"(\d+),(\d+),(\d+)", args.colour)
    if m is not None:
        rgb = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    else:
        c = TwinklyColour(args.colour)
        rgb = (int(c.red * 255), int(c.green * 255), int(c.blue * 255))
    return await t.set_static_colour(rgb)


async def command_summary(t: Twinkly, args: argparse.Namespace):
    return await t.summary()


async def command_music(t: Twinkly, args: argparse.Namespace):
    if args.on:
        return await t.music_on()
    elif args.off:
        return await t.music_off()
    elif args.next:
        return await t.next_music_driver()
    elif args.prev:
        return await t.previous_music_driver()
    elif args.current:
        return await t.get_current_music_driver()
    elif args.driver:
        return await t.set_current_music_driver(args.driver)
    elif args.list:
        if args.list == "all":
            return TWINKLY_MUSIC_DRIVERS
        elif args.list == "official":
            return TWINKLY_MUSIC_DRIVERS_OFFICIAL
        elif args.list == "unofficial":
            return TWINKLY_MUSIC_DRIVERS_UNOFFICIAL


async def main_loop() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="Twinkly Twinkly Little Star")
    parser.add_argument(
        "--host", metavar="hostname", required=True, help="Device address"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debugging")
    parser.add_argument(
        "--json", action="store_true", help="Output result as compact JSON"
    )

    subparsers = parser.add_subparsers(dest="command")

    parser_network = subparsers.add_parser("network", help="Get network status")
    parser_network.set_defaults(func=command_network)

    parser_firmware = subparsers.add_parser("firmware", help="Get firmware version")
    parser_firmware.set_defaults(func=command_firmware)

    parser_details = subparsers.add_parser("details", help="Get device details")
    parser_details.set_defaults(func=command_details)

    parser_name = subparsers.add_parser("name", help="Get or set device name")
    parser_name.add_argument("--name", metavar="name", type=str, required=False)
    parser_name.set_defaults(func=command_name)

    parser_power = subparsers.add_parser(
        "power", help="Get or set device power state ('on', 'off')"
    )
    parser_power.add_argument(
        "--on", action="store_true", required=False, help="Turn device on"
    )
    parser_power.add_argument(
        "--off", action="store_true", required=False, help="Turn device off"
    )
    parser_power.set_defaults(func=command_power)

    parser_brightness = subparsers.add_parser(
        "brightness", help="Get or set LED brightness"
    )
    parser_brightness.add_argument(
        "--pct",
        metavar="value",
        type=int,
        required=False,
        help="Percent brightness (1-100)",
    )
    parser_brightness.set_defaults(func=command_brightness)

    parser_mode = subparsers.add_parser("mode", help="Get or set LED operation mode")
    parser_mode.add_argument(
        "--mode",
        choices=TWINKLY_MODES,
        required=False,
    )
    parser_mode.set_defaults(func=command_mode)

    parser_mqtt = subparsers.add_parser("mqtt", help="Get or set MQTT configuration")
    parser_mqtt.add_argument(
        "--json",
        dest="mqtt_json",
        metavar="mqtt",
        type=str,
        required=False,
        help="MQTT config as JSON",
    )
    parser_mqtt.set_defaults(func=command_mqtt)

    parser_movie = subparsers.add_parser("movie", help="Movie configuration")
    parser_movie.add_argument(
        "--delay",
        dest="movie_delay",
        metavar="milliseconds",
        type=int,
        default=100,
        required=False,
        help="Delay between frames",
    )
    parser_movie.add_argument(
        "--file",
        dest="movie_file",
        metavar="filename",
        type=str,
        required=False,
        help="Movie file",
    )
    parser_movie.set_defaults(func=command_movie)

    parser_colour = subparsers.add_parser("static", help="Set static")
    parser_colour.add_argument(
        "--colour",
        dest="colour",
        metavar="colour",
        type=str,
        required=True,
        help="Colour",
    )
    parser_colour.set_defaults(func=command_static)

    parser_summary = subparsers.add_parser("summary", help="Get device summary")
    parser_summary.set_defaults(func=command_summary)

    parser_music = subparsers.add_parser("music", help="Twinkly Music device control")
    parser_music.add_argument(
        "--on",
        action="store_true",
        help="Turn on Twinkly Music",
    )
    parser_music.add_argument(
        "--off",
        action="store_true",
        help="Turn off Twinkly Music",
    )
    parser_music.add_argument(
        "--next",
        action="store_true",
        help="Select next official music driver",
    )
    parser_music.add_argument(
        "--prev",
        action="store_true",
        help="Select previous official music driver",
    )
    parser_music.add_argument(
        "--current",
        action="store_true",
        help="Get the current music driver",
    )
    parser_music.add_argument(
        "--driver",
        metavar="name",
        type=str,
        choices=list(TWINKLY_MUSIC_DRIVERS.keys()),
        help="Set a music driver",
    )
    parser_music.add_argument(
        "--list",
        metavar="type",
        choices=["all", "official", "unofficial"],
        nargs="?",
        const="all",
        help="List all, official, or unofficial music drivers (default: all)",
    )
    parser_music.set_defaults(func=command_music)

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    t = Twinkly(host=args.host)

    try:
        res = await args.func(t, args)
    except AttributeError:
        parser.print_help()
        await t.close()
        sys.exit(0)

    if args.json:
        print(json.dumps(res, indent=None, separators=(",", ":")))
    else:
        if res is not None:
            print(json.dumps(res, indent=4))

    await t.close()


def main() -> None:
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
