import logging
import unittest
import uuid
from typing import Any

import aiounittest
import pytest

from ttls.client import (
    TWINKLY_RETURN_CODE,
    TWINKLY_RETURN_CODE_OK,
    Twinkly,
    TwinklyError,
    TwinklyFrame,
)

_LOGGER = logging.getLogger(__name__)


class TwinklyMock(Twinkly):
    async def send_frame(self, frame: TwinklyFrame) -> None:
        _LOGGER.debug("MOCK: send_frame()")

    async def _post(self, endpoint: str, **kwargs) -> Any:
        _LOGGER.debug("MOCK: POST endpoint %s", endpoint)

    async def _get(self, endpoint: str, **kwargs) -> Any:
        _LOGGER.debug("MOCK: GET endpoint %s", endpoint)
        if self._api_version == 1:
            return await self._get_v1(endpoint, **kwargs)
        return await self._get_v2(endpoint, **kwargs)

    async def _get_v1(self, endpoint: str, **kwargs) -> Any:
        if endpoint == "gestalt":
            return {
                "product_name": "Twinkly",
                "hardware_version": "100",
                "bytes_per_led": 3,
                "hw_id": "e00000",
                "flash_size": 64,
                "led_type": 14,
                "product_code": "TWS250STP-B",
                "fw_family": "F",
                "device_name": "Xmas tree",
                "uptime": "21172191",
                "mac": "aa:bb:cc:dd:ee:ff",
                "uuid": str(uuid.uuid4()),
                "max_supported_led": 500,
                "number_of_led": 250,
                "led_profile": "RGB",
                "frame_rate": 23.77,
                "measured_frame_rate": 25,
                "movie_capacity": 5397,
                "max_movies": 55,
                "copyright": "LEDWORKS 2021",
                TWINKLY_RETURN_CODE: TWINKLY_RETURN_CODE_OK,
            }
        if endpoint == "device_name":
            # Code should be 1000
            return {TWINKLY_RETURN_CODE: TWINKLY_RETURN_CODE_OK + 1}
        if endpoint == "movies":
            # Attribute "movies" is missing from the response
            return {TWINKLY_RETURN_CODE: TWINKLY_RETURN_CODE_OK}

        _LOGGER.warning("Endpoint %s not yet implemented")
        return

    async def _get_v2(self, endpoint: str, **kwargs) -> Any:
        if endpoint == "gestalt":
            return {
                "artnet_en": False,
                "cloud": True,
                "device_config": {
                    "drv_params": {
                        "t0h": 7000,
                        "t0l": 2000,
                        "t1h": 3500,
                        "t1l": 5500,
                        "tendh": 4000,
                        "tendl": 12500,
                    },
                    "led_drv": "d9865c",
                    "led_id": 136,
                    "led_profile": "RGBW",
                    "ports": [
                        {"port_id": 0, "strings": [{"len": 250, "start": 1}]},
                        {"port_id": 1, "strings": [{"len": 250, "start": 1}]},
                        {"port_id": 2, "strings": [{"len": 250, "start": 1}]},
                        {"port_id": 3, "strings": [{"len": 250, "start": 1}]},
                    ],
                },
                "device_name": "MockPro",
                "frame_rate": 9,
                "group": {"mode": "none", "offset": 0, "size": 0, "uid": ""},
                "max_capacity": 6722,
                "max_movies": 24,
                "max_playlists": 4,
                "max_steps": 16,
                "max_supported_led": 1500,
                "movie_capacity": 6544,
                "network": {
                    "dhcp": True,
                    "gateway": "192.168.0.0",
                    "ip": "192.0.2.1",
                    "netmask": "255.255.255.0",
                },
                "number_of_led": 1000,
                "osc_en": False,
                "poe_en": True,
                "product_code": "TWPROCTRLPLC21",
                "rest_locked": False,
                "result": {"code": 1000},
                "ui_en": True,
                "uptime": 365688633,
            }

        if endpoint == "device/name":
            # Code should be 1000
            return {"result": {TWINKLY_RETURN_CODE: TWINKLY_RETURN_CODE_OK + 1}}
        if endpoint == "movies":
            # Attribute "movies" is missing from the response
            return {
                "size": 4,
                "max": 24,
                "available_frames": 6544,
                "max_capacity": 6722,
                "result": {TWINKLY_RETURN_CODE: TWINKLY_RETURN_CODE_OK},
            }

        _LOGGER.warning("Endpoint %s not yet implemented")
        return


class TestTwinklyGeneric(aiounittest.AsyncTestCase):
    @classmethod
    def setUpClass(self):
        logging.basicConfig(level=logging.DEBUG)

    def setUp(self):
        self.client = TwinklyMock(host="192.0.2.1", api_version=1)
        self.client_v2 = TwinklyMock(host="192.0.2.1", api_version=2)

    async def test_get_details(self):
        res = await self.client.get_details()
        self.assertEqual(res["product_name"], "Twinkly")

    async def test_validation_error_code(self):
        with pytest.raises(TwinklyError) as e:
            await self.client.get_name()
        assert "Invalid response from Twinkly" in str(e.value)

    async def test_validation_error_string(self):
        with pytest.raises(TwinklyError) as e:
            await self.client.get_saved_movies()
        assert "Invalid response from Twinkly" in str(e.value)

    async def test_get_details_v2(self):
        res = await self.client_v2.get_details()
        self.assertEqual(res["product_code"], "TWPROCTRLPLC21")

    async def test_validation_error_code_v2(self):
        with pytest.raises(TwinklyError) as e:
            await self.client_v2.get_name()
        assert "Invalid response from Twinkly" in str(e.value)

    async def test_validation_error_string_v2(self):
        with pytest.raises(TwinklyError) as e:
            await self.client_v2.get_saved_movies()
        assert "Invalid response from Twinkly" in str(e.value)


if __name__ == "__main__":
    unittest.main()
