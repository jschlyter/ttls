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

import base64
import logging
import os
import socket
import time
from typing import List, Optional, Tuple, Dict, Any, Union

from aiohttp import ClientSession

logger = logging.getLogger(__name__)

TwinklyColour = Tuple[int, int, int]
TwinklyFrame = List[TwinklyColour]
TwinklyResult = Optional[dict]

TWINKLY_MODES = ['rt', 'movie', 'off', 'demo', 'effect']


class Twinkly(object):

    def __init__(self, host: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = ClientSession(raise_for_status=True)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.headers: Dict[str, str] = {}
        self.host = host
        self.rt_port = 7777
        self.expires = None
        self._token = ''
        self.details: Dict[str, Union[str, int]] = {}

    @property
    def base(self) -> str:
        return f"http://{self.host}/xled/v1"

    @property
    def length(self) -> int:
        return int(self.details['number_of_led'])

    async def close(self) -> None:
        await self.session.close()

    async def interview(self) -> None:
        if len(self.details) == 0:
            self.details = await self.get_details()

    async def _post(self, endpoint: str, **kwargs) -> Any:
        await self.ensure_token()
        self.logger.info("POST endpoint %s", endpoint)
        if 'json' in kwargs:
            self.logger.info("POST payload %s", kwargs['json'])
        headers = kwargs.pop('headers', self.headers)
        async with self.session.post(f"{self.base}/{endpoint}", headers=headers, **kwargs) as r:
            return await r.json()

    async def _get(self, endpoint: str, **kwargs) -> Any:
        await self.ensure_token()
        self.logger.info("GET endpoint %s", endpoint)
        async with self.session.get(f"{self.base}/{endpoint}", headers=self.headers, **kwargs) as r:
            return await r.json()

    async def ensure_token(self) -> str:
        if self.expires is None or self.expires <= time.time():
            self.logger.debug("Authentication token expired, will refresh")
            await self.login()
            await self.verify_login()
        else:
            self.logger.debug("Authentication token still valid")
        return self._token

    async def login(self) -> None:
        challenge = base64.b64encode(os.urandom(32)).decode()
        payload = {"challenge": challenge}
        async with self.session.post(f"{self.base}/login", json=payload) as r:
            data = await r.json()
        self._token = data['authentication_token']
        self.headers['X-Auth-Token'] = self._token
        self.expires = time.time() + data['authentication_token_expires_in']

    async def logout(self) -> None:
        await self._post('logout', json={})
        self._token = ''

    async def verify_login(self) -> None:
        await self._post('verify', json={})

    async def get_name(self) -> Any:
        return await self._get('device_name')

    async def set_name(self, name: str) -> Any:
        return await self._post('device_name', json={'name': name})

    async def reset(self) -> Any:
        return await self._get('reset')

    async def get_network_status(self) -> Any:
        return await self._get('network/status')

    async def get_firmware_version(self) -> Any:
        return await self._get('fw/version')

    async def get_details(self) -> Any:
        return await self._get('gestalt')

    async def get_mode(self) -> Any:
        return await self._get('led/mode')

    async def set_mode(self, mode: str) -> Any:
        return await self._post('led/mode', json={'mode': mode})

    async def get_mqtt(self) -> Any:
        return await self._get('mqtt/config')

    async def set_mqtt(self, data: dict) -> Any:
        return await self._post('mqtt/config', json=data)

    async def send_frame(self, frame: TwinklyFrame) -> None:
        await self.interview()
        if len(frame) != self.length:
            raise ValueError("Invalid frame length")
        token = await self.ensure_token()
        header = bytes([0x01]) + bytes(base64.b64decode(token)) + bytes([self.length])
        payload = []
        for x in frame:
            payload.extend(list(x))
        self.socket.sendto(header + bytes(payload), (self.host, self.rt_port))

    async def get_movie_config(self) -> Any:
        return await self._get('led/movie/config')

    async def set_movie_config(self, data: dict) -> Any:
        return await self._post('led/movie/config', json=data)

    async def upload_movie(self, movie: bytes) -> Any:
        return await self._post('led/movie/full', data=movie,
                                headers={'Content-Type': 'application/octet-stream'})

    async def set_static_colour(self, colour: TwinklyColour) -> None:
        frame = [colour for _ in range(0, self.length)]
        movie = bytes([item for t in frame for item in t])
        await self.upload_movie(movie)
        await self.set_movie_config({'frames_number': 1})
        await self.set_mode('movie')
