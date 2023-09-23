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
from __future__ import annotations

import base64
import logging
import os
import socket
import time
from itertools import cycle, islice
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from aiohttp import ClientResponseError, ClientSession, ClientTimeout
from aiohttp.web_exceptions import HTTPUnauthorized

from .colours import TwinklyColour, TwinklyColourTuple

_LOGGER = logging.getLogger(__name__)

TwinklyFrame = List[TwinklyColourTuple]
TwinklyResult = Optional[dict]


TWINKLY_MODES = [
    "color",
    "demo",
    "effect",
    "movie",
    "off",
    "playlist",
    "rt",
]
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

TWINKLY_RETURN_CODE = "code"
TWINKLY_RETURN_CODE_OK = 1000

DEFAULT_TIMEOUT = 3


class Twinkly(object):
    def __init__(
        self,
        host: str,
        session: Optional[ClientSession] = None,
        timeout: Optional[int] = None,
    ):
        self.host = host
        self._timeout = ClientTimeout(total=timeout or DEFAULT_TIMEOUT)
        if session:
            self._session = session
            self._shared_session = True
        else:
            self._session = None
            self._shared_session = False
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._headers: Dict[str, str] = {}
        self._rt_port = 7777
        self._expires = None
        self._token = None
        self._details: Dict[str, Union[str, int]] = {}
        self._default_mode = "movie"

    @property
    def base(self) -> str:
        return f"http://{self.host}/xled/v1"

    @property
    def length(self) -> int:
        return int(self._details["number_of_led"])

    def is_rgbw(self) -> bool:
        return self._details["led_profile"] == "RGBW"

    def is_rgb(self) -> bool:
        return self._details["led_profile"] == "RGB"

    @property
    def default_mode(self) -> str:
        return self._default_mode

    @default_mode.setter
    def default_mode(self, mode: str | None = None) -> str:
        if not mode:
            return
        if mode not in TWINKLY_MODES:
            raise ValueError("Invalid mode")
        if mode == "off":
            _LOGGER.warning("Setting default mode to off")
        self._default_mode = mode

    async def close(self) -> None:
        if not self._shared_session:
            await self._get_session().close()

    async def interview(self, force: bool | None = False) -> None:
        if len(self._details) == 0 or force:
            self._details = await self.get_details()
            mode = await self.get_mode()
            if mode.get("mode") != "off":
                self.default_mode = mode.get("mode")

    def _get_session(self):
        return self._session or ClientSession()

    async def _post(self, endpoint: str, **kwargs) -> Any:
        await self.ensure_token()
        _LOGGER.debug("POST endpoint %s", endpoint)
        if "json" in kwargs:
            _LOGGER.debug("POST payload %s", kwargs["json"])
        headers = kwargs.pop("headers", self._headers)
        retry_num = kwargs.pop("retry_num", 0)
        try:
            async with self._get_session().post(
                f"{self.base}/{endpoint}",
                headers=headers,
                timeout=self._timeout,
                raise_for_status=True,
                **kwargs,
            ) as r:
                _LOGGER.debug("POST response %d", r.status)
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
        _LOGGER.debug("GET endpoint %s", endpoint)
        headers = kwargs.pop("headers", self._headers)
        retry_num = kwargs.pop("retry_num", 0)
        try:
            async with self._get_session().get(
                f"{self.base}/{endpoint}",
                headers=headers,
                timeout=self._timeout,
                raise_for_status=True,
                **kwargs,
            ) as r:
                _LOGGER.debug("GET response %d", r.status)
                return await r.json()
        except ClientResponseError as e:
            if e.status == HTTPUnauthorized.status_code:
                return await self._handle_authorized(
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
            _LOGGER.debug(
                f"Invalid token for request. Maximum retries of {max_retries} exceeded."
            )
            raise exception

        retry_num += 1
        _LOGGER.debug(
            f"Invalid token for request. Refreshing token and attempting retry {retry_num} of {max_retries}."
        )
        await self.refresh_token()
        return await request_method(
            endpoint, headers=self._headers, retry_num=retry_num, **kwargs
        )

    async def refresh_token(self) -> None:
        await self.login()
        await self.verify_login()
        _LOGGER.debug("Authentication token refreshed")

    async def ensure_token(self) -> str:
        if self._expires is None or self._expires <= time.time():
            _LOGGER.debug("Authentication token expired, will refresh")
            await self.refresh_token()
        else:
            _LOGGER.debug("Authentication token still valid")
        return self._token or ""

    async def login(self) -> None:
        challenge = base64.b64encode(os.urandom(32)).decode()
        payload = {"challenge": challenge}
        async with self._get_session().post(
            f"{self.base}/login",
            json=payload,
            timeout=self._timeout,
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
        return self._valid_response(await self._get("device_name"))

    async def set_name(self, name: str) -> Any:
        return await self._post("device_name", json={"name": name})

    async def reset(self) -> Any:
        return self._valid_response(await self._get("reset"))

    async def get_network_status(self) -> Any:
        return self._valid_response(await self._get("network/status"))

    async def get_firmware_version(self) -> Any:
        return self._valid_response(await self._get("fw/version"))

    async def get_details(self) -> Any:
        return self._valid_response(await self._get("gestalt"))

    async def is_on(self) -> Optional[bool]:
        mode = await self.get_mode()
        if mode is None:
            return None
        return mode.get("mode", "off") != "off"

    async def turn_on(self) -> Any:
        return await self.set_mode(self._default_mode)

    async def turn_off(self) -> Any:
        return await self.set_mode("off")

    async def get_brightness(self) -> Any:
        return self._valid_response(await self._get("led/out/brightness"))

    async def set_brightness(self, percent: int) -> Any:
        return await self._post(
            "led/out/brightness", json={"value": percent, "type": "A"}
        )

    async def get_mode(self) -> Any:
        return self._valid_response(await self._get("led/mode"))

    async def set_mode(self, mode: str) -> Any:
        return await self._post("led/mode", json={"mode": mode})

    async def get_mqtt(self) -> Any:
        return self._valid_response(await self._get("mqtt/config"))

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
        self._socket.sendto(header + bytes(payload), (self.host, self._rt_port))

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
            self._socket.sendto(header + bytes(payload), (self.host, self._rt_port))

    async def get_movie_config(self) -> Any:
        return self._valid_response(await self._get("led/movie/config"))

    async def set_movie_config(self, data: dict) -> Any:
        return await self._post("led/movie/config", json=data)

    async def upload_movie(self, movie: bytes) -> Any:
        return await self._post(
            "led/movie/full",
            data=movie,
            headers={"Content-Type": "application/octet-stream"},
        )

    async def set_static_colour(
        self,
        colour: Union[
            TwinklyColour,
            TwinklyColourTuple,
            List[TwinklyColour],
            List[TwinklyColourTuple],
        ],
    ) -> None:
        if not self._details:
            await self.interview()
        if isinstance(colour, List):
            colour = colour[0]
        if isinstance(colour, Tuple):
            colour = TwinklyColour.from_twinkly_tuple(colour)
        await self._post(
            "led/color",
            json=colour.as_dict(),
        )
        await self.set_mode("color")

    async def set_cycle_colours(
        self,
        colour: Union[
            TwinklyColour,
            TwinklyColourTuple,
            List[TwinklyColour],
            List[TwinklyColourTuple],
        ],
    ) -> None:
        if isinstance(colour, TwinklyColour):
            sequence = [colour.as_twinkly_tuple()]
        elif isinstance(colour, Tuple):
            sequence = [colour]
        elif isinstance(colour, List):
            if isinstance(colour[0], TwinklyColour):
                sequence = [c.as_twinkly_tuple() for c in colour]
            else:
                sequence = colour
        else:
            raise TypeError("Unknown colour format")
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
        return self._valid_response(await self._get("summary"))

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
        return self._valid_response(await self._get("music/drivers/current"))

    async def set_current_music_driver(self, driver_name: str) -> Any:
        unique_id = self._music_driver_id(driver_name)
        if not unique_id:
            _LOGGER.error(f"'{driver_name}' is an invalid music driver")
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
            _LOGGER.warn(
                f"Music driver '{driver_name}'is defined, but is not officially supported"
            )
            return TWINKLY_MUSIC_DRIVERS_UNOFFICIAL[driver_name]
        else:
            return None

    async def get_saved_movies(self) -> Any:
        return self._valid_response(await self._get("movies"), check_for="movies")

    async def get_current_movie(self) -> Any:
        return self._valid_response(await self._get("movies/current"))

    async def set_current_movie(self, movie_id: int) -> Any:
        return await self._post("movies/current", json={"id": movie_id})

    async def get_current_colour(self) -> Any:
        return self._valid_response(await self._get("led/color"))

    async def get_predefined_effects(self) -> Any:
        """Get the list of predefined effects."""
        return self._valid_response(await self._get("led/effects"))

    async def get_current_predefined_effect(self) -> Any:
        """Get current effect."""
        return self._valid_response(await self._get("led/effects/current"))

    async def set_current_predefined_effect(self, effect_id: int) -> None:
        """Set current effect."""
        await self._post(
            "led/effects/current",
            json={"effect_id": effect_id},
        )

    async def get_playlist(self) -> Any:
        """Get the playlist."""
        return self._valid_response(await self._get("playlist"))

    async def get_current_playlist_entry(self) -> Any:
        """Get current playlist."""
        return self._valid_response(await self._get("playlist/current"))

    async def set_current_playlist_entry(self, entry_id: int) -> None:
        """Jump to specific effect in the playlist."""
        await self._post(
            "playlist/current",
            json={"id": entry_id},
        )

    def _valid_response(
        self, response: dict[Any, Any], check_for: str | None = None
    ) -> dict[Any, Any]:
        """Validate twinkly-responses from the API."""
        if (
            response
            and response.get(TWINKLY_RETURN_CODE) == TWINKLY_RETURN_CODE_OK
            and (not check_for or check_for in response)
        ):
            _LOGGER.debug("Twinkly response: %s", response)
            return response
        raise TwinklyError(f"Invalid response from Twinkly: {response}")


class TwinklyError(ValueError):
    """Error from the API."""
