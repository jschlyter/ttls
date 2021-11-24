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
from itertools import cycle, islice
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from aiohttp import ClientResponseError, ClientSession, ClientTimeout
from aiohttp.web_exceptions import HTTPUnauthorized

logger = logging.getLogger("twinkly")

TwinklyColour = Tuple[int, int, int]
TwinklyFrame = List[TwinklyColour]
TwinklyResult = Optional[dict]

TWINKLY_MODES = ["rt", "movie", "off", "demo", "effect"]
RT_PAYLOAD_MAX_LIGHTS = 300

TWINKLY_MUSIC_DRIVERS_OFFICIAL = {
    "VU Meter": "00000000-0000-0000-0000-000000000001",
    "Beat Hue": "00000000-0000-0000-0000-000000000002",
    "Psychedelica": "00000000-0000-0000-0000-000000000003",
    "Red Vertigo": "00000000-0000-0000-0000-000000000004",
    "Dancing Bands": "00000000-0000-0000-0000-000000000005",
    "Diamond Swirl": "00000000-0000-0000-0000-000000000006",
    "Joyful Stripes": "00000000-0000-0000-0000-000000000007",
    "Angel Fade": "00000000-0000-0000-0000-000000000008",
    "Clockwork": "00000000-0000-0000-0000-000000000009",
    "Sipario": "00000000-0000-0000-0000-00000000000A",
    "Sunset": "00000000-0000-0000-0000-00000000000B",
    "Elevator": "00000000-0000-0000-0000-00000000000C",
}

TWINKLY_MUSIC_DRIVERS_UNOFFICIAL = {
    "VU Meter 2": "00000000-0000-0000-0000-000001000001",
    "Beat Hue 2": "00000000-0000-0000-0000-000001000002",
    "Psychedelica 2": "00000000-0000-0000-0000-000001000003",
    "Sparkle": "00000000-0000-0000-0000-000001000005",
    "Sparkle Hue": "00000000-0000-0000-0000-000001000006",
    "Psycho Sparkle": "00000000-0000-0000-0000-000001000007",
    "Psycho Hue": "00000000-0000-0000-0000-000001000008",
    "Red Line": "00000000-0000-0000-0000-000001000009",
    "Red Vertigo 2": "00000000-0000-0000-0000-000002000004",
    "Dancing Bands 2": "00000000-0000-0000-0000-000002000005",
    "Diamond Swirl 2": "00000000-0000-0000-0000-000002000006",
    "Angel Fade 2": "00000000-0000-0000-0000-000002000008",
    "Clockwork 2": "00000000-0000-0000-0000-000002000009",
    "Sunset 2": "00000000-0000-0000-0000-00000200000B",
}

TWINKLY_MUSIC_DRIVERS = {
    **TWINKLY_MUSIC_DRIVERS_OFFICIAL,
    **TWINKLY_MUSIC_DRIVERS_UNOFFICIAL,
}

DEFAULT_TIMEOUT = 3


class Twinkly(object):
    def __init__(
        self,
        host: str,
        session: Optional[ClientSession] = None,
        timeout: Optional[int] = None,
    ):
        self.timeout = ClientTimeout(total=timeout or DEFAULT_TIMEOUT)
        if session:
            self._session = session
            self._shared_session = True
        else:
            self._session = ClientSession()
            self._shared_session = False
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._headers: Dict[str, str] = {}
        self._host = host
        self._rt_port = 7777
        self._expires = None
        self._token = None
        self._details: Dict[str, Union[str, int]] = {}

    @property
    def base(self) -> str:
        return f"http://{self._host}/xled/v1"

    @property
    def length(self) -> int:
        return int(self._details["number_of_led"])

    async def close(self) -> None:
        if not self._shared_session:
            await self._session.close()

    async def interview(self) -> None:
        if len(self._details) == 0:
            self._details = await self.get_details()

    async def _post(self, endpoint: str, **kwargs) -> Any:
        await self.ensure_token()
        logger.info("POST endpoint %s", endpoint)
        if "json" in kwargs:
            logger.info("POST payload %s", kwargs["json"])
        headers = kwargs.pop("headers", self._headers)
        retry_num = kwargs.pop("retry_num", 0)
        try:
            async with self._session.post(
                f"{self.base}/{endpoint}",
                headers=headers,
                timeout=self.timeout,
                raise_for_status=True,
                **kwargs,
            ) as r:
                return await r.json()
        except ClientResponseError as e:
            if e.status == HTTPUnauthorized.status_code:
                await self._handle_authorized(
                    self._post, endpoint, exception=e, retry_num=retry_num, **kwargs
                )
            else:
                raise e

    async def _get(self, endpoint: str, **kwargs) -> Any:
        await self.ensure_token()
        logger.info("GET endpoint %s", endpoint)
        headers = kwargs.pop("headers", self._headers)
        retry_num = kwargs.pop("retry_num", 0)
        try:
            async with self._session.get(
                f"{self.base}/{endpoint}",
                headers=headers,
                timeout=self.timeout,
                raise_for_status=True,
                **kwargs,
            ) as r:
                return await r.json()
        except ClientResponseError as e:
            if e.status == HTTPUnauthorized.status_code:
                await self._handle_authorized(
                    self._get,
                    endpoint,
                    exception=e,
                    retry_num=retry_num,
                    **kwargs,
                )
            else:
                raise e

    async def _handle_authorized(
        self, request_method: Callable, endpoint: str, exception: Exception, **kwargs
    ) -> None:
        max_retries = 1
        retry_num = kwargs.pop("retry_num", 0)

        if retry_num >= max_retries:
            logger.debug(
                f"Invalid token for request. Maximum retries of {max_retries} exceeded."
            )
            raise exception

        retry_num += 1
        logger.debug(
            f"Invalid token for request. Refreshing token and attempting retry {retry_num} of {max_retries}."
        )
        await self.refresh_token()
        await request_method(
            endpoint, headers=self._headers, retry_num=retry_num, **kwargs
        )

    async def refresh_token(self) -> None:
        await self.login()
        await self.verify_login()
        logger.debug("Authentication token has been refreshed")

    async def ensure_token(self) -> str:
        if self._expires is None or self._expires <= time.time():
            logger.debug("Authentication token expired, will refresh")
            await self.refresh_token()
        else:
            logger.debug("Authentication token still valid")
        return self._token or ""

    async def login(self) -> None:
        challenge = base64.b64encode(os.urandom(32)).decode()
        payload = {"challenge": challenge}
        async with self._session.post(
            f"{self.base}/login",
            json=payload,
            timeout=self.timeout,
            raise_for_status=True,
        ) as r:
            data = await r.json()
        self._token = data["authentication_token"]
        self._headers["X-Auth-Token"] = self._token
        self._expires = time.time() + data["authentication_token_expires_in"]

    async def logout(self) -> None:
        await self._post("logout", json={})
        self._token = None

    async def verify_login(self) -> None:
        await self._post("verify", json={})

    async def get_name(self) -> Any:
        return await self._get("device_name")

    async def set_name(self, name: str) -> Any:
        return await self._post("device_name", json={"name": name})

    async def reset(self) -> Any:
        return await self._get("reset")

    async def get_network_status(self) -> Any:
        return await self._get("network/status")

    async def get_firmware_version(self) -> Any:
        return await self._get("fw/version")

    async def get_details(self) -> Any:
        return await self._get("gestalt")

    async def is_on(self) -> bool:
        mode = await self.get_mode()
        return mode.get("mode", "off") != "off"

    async def turn_on(self) -> Any:
        return await self.set_mode("movie")

    async def turn_off(self) -> Any:
        return await self.set_mode("off")

    async def get_brightness(self) -> Any:
        return await self._get("led/out/brightness")

    async def set_brightness(self, percent: int) -> Any:
        return await self._post(
            "led/out/brightness", json={"value": percent, "type": "A"}
        )

    async def get_mode(self) -> Any:
        return await self._get("led/mode")

    async def set_mode(self, mode: str) -> Any:
        return await self._post("led/mode", json={"mode": mode})

    async def get_mqtt(self) -> Any:
        return await self._get("mqtt/config")

    async def set_mqtt(self, data: dict) -> Any:
        return await self._post("mqtt/config", json=data)

    async def send_frame(self, frame: TwinklyFrame) -> None:
        await self.interview()
        if len(frame) != self.length:
            raise ValueError("Invalid frame length")
        token = await self.ensure_token()
        header = bytes([0x01]) + bytes(base64.b64decode(token)) + bytes([self.length])
        payload = []
        for x in frame:
            payload.extend(list(x))
        self._socket.sendto(header + bytes(payload), (self._host, self._rt_port))

    async def send_frame_2(self, frame: TwinklyFrame) -> None:
        await self.interview()
        if len(frame) != self.length:
            raise ValueError("Invalid frame length")
        token = await self.ensure_token()
        frame_segments = [
            frame[i : i + RT_PAYLOAD_MAX_LIGHTS]
            for i in range(0, len(frame), RT_PAYLOAD_MAX_LIGHTS)
        ]
        for i in range(0, len(frame_segments)):
            header = (
                bytes([len(frame_segments)])
                + bytes(base64.b64decode(token))
                + bytes([0, 0])
                + bytes([i])
            )
            payload = []
            for x in frame_segments[i]:
                payload.extend(list(x))
            self._socket.sendto(header + bytes(payload), (self._host, self._rt_port))

    async def get_movie_config(self) -> Any:
        return await self._get("led/movie/config")

    async def set_movie_config(self, data: dict) -> Any:
        return await self._post("led/movie/config", json=data)

    async def upload_movie(self, movie: bytes) -> Any:
        return await self._post(
            "led/movie/full",
            data=movie,
            headers={"Content-Type": "application/octet-stream"},
        )

    async def set_static_colour(
        self, colour: Union[TwinklyColour, List[TwinklyColour]]
    ) -> None:
        if isinstance(colour, Tuple):
            sequence = [colour]
        else:
            sequence = colour
        frame = list(islice(cycle(sequence), self.length))
        movie = bytes([item for t in frame for item in t])
        await self.upload_movie(movie)
        await self.set_movie_config(
            {
                "frames_number": 1,
                "loop_type": 0,
                "frame_delay": 1000,
                "leds_number": self.length,
            }
        )
        await self.set_mode("movie")

    async def summary(self) -> Any:
        return await self._get("summary")

    async def music_on(self) -> Any:
        return await self._post("music/enabled", json={"enabled": 1})

    async def music_off(self) -> Any:
        return await self._post("music/enabled", json={"enabled": 0})

    async def get_music_drivers(self) -> Any:
        """
        This endpoint is not currently used by the Twinkly app, but was discovered through
        trial & error.  It raises a 400 error ('unexpected content-length header') when
        called from aiohttp, but returns JSON when called via requests.
        This endpoint was used to map driver names to IDs and identify the 'unofficial'
        drivers on the device.
        {"code": 1000, "drivers_number": 26, "unique_ids": [<list of ID strings>]}
        """
        # return await self._get("music/drivers")
        raise NotImplementedError

    async def next_music_driver(self) -> Any:
        return await self._post("music/drivers/current", json={"action": "next"})

    async def previous_music_driver(self) -> Any:
        return await self._post("music/drivers/current", json={"action": "prev"})

    async def get_current_music_driver(self) -> Any:
        return await self._get("music/drivers/current")

    async def set_current_music_driver(self, driver_name: str) -> Any:
        unique_id = self._music_driver_id(driver_name)
        if not unique_id:
            logger.error(f"'{driver_name}' is an invalid music driver")
            return
        # An explicit driver cannot be set unless next/previous driver was called first
        current_driver = await self.get_current_music_driver()
        if current_driver["handle"] == -1:
            await self.next_music_driver()
        return await self._post("music/drivers/current", json={"unique_id": unique_id})

    def _music_driver_id(self, driver_name: str) -> Any:
        if driver_name in TWINKLY_MUSIC_DRIVERS_OFFICIAL:
            return TWINKLY_MUSIC_DRIVERS_OFFICIAL[driver_name]
        elif driver_name in TWINKLY_MUSIC_DRIVERS_UNOFFICIAL:
            logger.warn(
                f"Music driver '{driver_name}'is defined, but is not officially supported"
            )
            return TWINKLY_MUSIC_DRIVERS_UNOFFICIAL[driver_name]
        else:
            return None
