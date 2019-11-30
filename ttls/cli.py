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

from colour import Color

from .client import TWINKLY_MODES, Twinkly

logger = logging.getLogger(__name__)


async def main_loop() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description='Twinkly Twinkly Little Star')
    parser.add_argument('--host',
                        metavar='hostname',
                        required=True,
                        help='Device address')
    parser.add_argument('--debug',
                        action='store_true',
                        help="Enable debugging")
    parser.add_argument('--json',
                        action='store_true',
                        help="Output result as compact JSON")

    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('network', help="Get network status")
    subparsers.add_parser('firmware', help="Get firmware version")
    subparsers.add_parser('details', help="Get device details")

    parser_name = subparsers.add_parser('name', help="Get or set device name")
    parser_name.add_argument('--name', metavar='name', type=str, required=False)

    parser_mode = subparsers.add_parser('mode', help="Get or set LED operation mode")
    parser_mode.add_argument('--mode', choices=TWINKLY_MODES, required=False)

    parser_mqtt = subparsers.add_parser('mqtt', help="Get or set MQTT configuration")
    parser_mqtt.add_argument('--json',
                             dest='mqtt_json',
                             metavar='mqtt',
                             type=str,
                             required=False,
                             help="MQTT config as JSON")

    parser_movie = subparsers.add_parser('movie', help="Movie configuration")
    parser_movie.add_argument('--delay',
                              dest='movie_delay',
                              metavar='milliseconds',
                              type=int,
                              default=100,
                              required=False,
                              help="Delay between frames")
    parser_movie.add_argument('--file',
                              dest='movie_file',
                              metavar='filename',
                              type=str,
                              required=False,
                              help="Movie file")

    parser_colour = subparsers.add_parser('static', help="Set static")
    parser_colour.add_argument('--colour',
                               dest='colour',
                               metavar='colour',
                               type=str,
                               required=False,
                               help="Colour")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    t = Twinkly(host=args.host)

    if args.command == 'name':
        res = await (t.get_name() if args.name is None else t.set_name(args.name))
    elif args.command == 'network':
        res = await t.get_network_status()
    elif args.command == 'firmware':
        res = await t.get_firmware_version()
    elif args.command == 'details':
        res = await t.get_details()
    elif args.command == 'mode':
        res = await (t.get_mode() if args.mode is None else t.set_mode(args.mode))
    elif args.command == 'mqtt':
        if args.mqtt_json is None:
            res = await t.get_mqtt()
        else:
            data = json.loads(args.mqtt_json)
            res if args.mode is None else await t.set_mqtt(data)
    elif args.command == 'movie':
        if args.movie_file:
            with open(args.movie_file, 'rb') as f:
                movie = f.read()
            await t.interview()
            params = {
                'frame_delay': args.movie_delay,
                'leds_number': t.length,
                'frames_number': int(len(movie) / 3 / t.length)
            }
            await t.set_mode('movie')
            await t.set_movie_config(params)
            res = await t.upload_movie(movie)
        else:
            res = await t.get_movie_config()
    elif args.command == 'static':
        await t.interview()
        m = re.match(r'(\d+),(\d+),(\d+)', args.colour)
        if m is not None:
            rgb = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            res = await t.set_static_colour(rgb)
        else:
            c = Color(args.colour)
            rgb = (int(c.red * 255), int(c.green * 255), int(c.blue * 255))
            res = await t.set_static_colour(rgb)
    else:
        parser.print_help()
        await t.close()
        sys.exit(0)

    if args.json:
        print(json.dumps(res, indent=None, separators=(',', ':')))
    else:
        if res is not None:
            print(json.dumps(res, indent=4))

    await t.close()


def main() -> None:
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
