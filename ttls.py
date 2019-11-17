"""Twinkly Twinkly Little Star"""

# based on:
# https://github.com/atlacom/python-twinkly-smart-decoration
# https://xled-docs.readthedocs.io/en/latest/

import argparse
import base64
import json
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

TWINKLY_MODES = ['rt', 'movie', 'off', 'demo', 'effect']


class Twinkly(object):

    def __init__(self, host: str, login: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()
        self.host = host
        self.expires = None
        if login:
            self.ensure_token()

    @property
    def base(self) -> str:
        return f"http://{self.host}/xled/v1"

    def _post(self, endpoint, **kwargs):
        self.ensure_token()
        self.logger.info("POST endpoint %s", kwargs.get('json'))
        return self.session.post(f"{self.base}/{endpoint}", **kwargs)

    def _get(self, endpoint, **kwargs):
        self.ensure_token()
        return self.session.get(f"{self.base}/{endpoint}", **kwargs)

    def ensure_token(self):
        if self.expires is None or self.expires <= time.time():
            self.logger.debug("Authentication token expired, will refresh")
            self.login()
            self.verify_login()
        else:
            self.logger.debug("Authentication token still valid")

    def login(self):
        challenge = base64.b64encode(os.urandom(32)).decode()
        payload = {"challenge": challenge}
        response = self.session.post(f"{self.base}/login", json=payload)
        response.raise_for_status()
        r = response.json()
        self.session.headers['X-Auth-Token'] = r['authentication_token']
        self.expires = time.time() + r['authentication_token_expires_in']

    def logout(self):
        response = self._post('logout', json={})
        response.raise_for_status()

    def verify_login(self):
        response = self._post('verify', json={})
        response.raise_for_status()

    @property
    def name(self) -> str:
        return self.get_name()['name']

    @name.setter
    def name(self, n: str) -> None:
        self.set_name({'name': n})

    @property
    def mode(self) -> str:
        return self.get_mode()['mode']

    @mode.setter
    def mode(self, m: str) -> None:
        self.set_mode({'mode': m})

    @property
    def version(self) -> str:
        return self.get_firmware_version()['version']

    def get_name(self):
        response = self._get('device_name')
        response.raise_for_status()
        return response.json()

    def set_name(self, data):
        response = self._post('device_name', json=data)
        response.raise_for_status()
        return response.json()

    def reset(self):
        response = self._get('reset')
        response.raise_for_status()
        return response.json()

    def get_network_status(self):
        response = self._get('network/status')
        response.raise_for_status()
        return response.json()

    def get_firmware_version(self):
        response = self._get('fw/version')
        response.raise_for_status()
        return response.json()

    def get_details(self):
        response = self._get('gestalt')
        response.raise_for_status()
        return response.json()

    def get_mode(self):
        response = self._get('led/mode')
        response.raise_for_status()
        return response.json()

    def set_mode(self, data):
        response = self._post('led/mode', json=data)
        response.raise_for_status()
        return response.json()

    def get_mqtt(self):
        response = self._get('mqtt/config')
        response.raise_for_status()
        return response.json()

    def set_mqtt(self, data):
        response = self._post('mqtt/config', json=data)
        response.raise_for_status()
        return response.json()

    def realtime(self):
        self.mode = "rt"

    def movie(self):
        self.mode = "movie"

    def off(self):
        self.mode = "off"

    def demo(self):
        self.mode = "demo"


def main():
    """ Main function"""

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

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    t = Twinkly(host=args.host)

    if args.command == 'name':
        res = t.get_name() if args.name is None else t.set_name({'name': args.name})
    elif args.command == 'network':
        res = t.get_network_status()
    elif args.command == 'firmware':
        res = t.get_firmware_version()
    elif args.command == 'details':
        res = t.get_details()
    elif args.command == 'mode':
        res = t.get_mode() if args.mode is None else t.set_mode({'mode': args.mode})
    elif args.command == 'mqtt':
        if args.mqtt_json is None:
            res = t.get_mqtt()
        else:
            data = json.loads(args.mqtt_json)
            res if args.mode is None else t.set_mqtt(data)
    else:
        raise Exception("Unknown command")

    if args.json:
        print(json.dumps(res, indent=None, separators=(',', ':')))
    else:
        print(json.dumps(res, indent=4))


if __name__ == "__main__":
    main()
