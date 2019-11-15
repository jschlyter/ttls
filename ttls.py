"""Twinkly Twinkly Little Star"""

# based on:
# https://github.com/atlacom/python-twinkly-smart-decoration
# https://xled-docs.readthedocs.io/en/latest/

import argparse
import base64
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)


class Twinkly(object):

    def __init__(self, host: str, login: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base = f"http://{host}/xled/v1"
        self.session = requests.Session()
        self.expires = None
        if login:
            self.ensure_token()

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

    @mode.settera
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
                        dest='host',
                        metavar='host',
                        required=True,
                        help='Device address')
    parser.add_argument('--debug',
                        dest='debug',
                        action='store_true',
                        help="Enable debugging")
    parser.add_argument('command')
    parser.add_argument('state', metavar='arg', nargs='*')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    t = Twinkly(host=args.host)

    if args.command == 'get-name':
        res = t.get_name()
    elif args.command == 'get-network':
        res = t.get_network_status()
    elif args.command == 'get-firmware':
        res = t.get_firmware_version()
    elif args.command == 'get-details':
        res = t.get_details()
    elif args.command == 'get-mode':
        res = t.get_mode()
    elif args.command == 'set-mode':
        res = t.set_mode({'mode': args.state[0]})
    elif args.command == 'get-mqtt':
        res = t.get_mqtt()
    else:
        raise Exception("Unknown command")

    print(res)


if __name__ == "__main__":
    main()
