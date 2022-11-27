import asyncio
import logging
import unittest
import uuid
from typing import Any

import aiounittest

from ttls.client import Twinkly, TwinklyFrame

_LOGGER = logging.getLogger(__name__)


class TwinklyMock(Twinkly):
    async def send_frame(self, frame: TwinklyFrame) -> None:
        _LOGGER.debug("MOCK: send_frame()")

    async def _post(self, endpoint: str, **kwargs) -> Any:
        _LOGGER.debug("MOCK: POST endpoint %s", endpoint)

    async def _get(self, endpoint: str, **kwargs) -> Any:
        _LOGGER.debug("MOCK: GET endpoint %s", endpoint)
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
                "code": 1000,
            }
        _LOGGER.warning("Endpoint %s not yet implemented")
        return


class TestTwinklyGeneric(aiounittest.AsyncTestCase):
    @classmethod
    def setUpClass(self):
        logging.basicConfig(level=logging.DEBUG)

    def setUp(self):
        self.client = TwinklyMock(host="192.0.2.1")

    async def test_get_details(self):
        res = await self.client.get_details()
        self.assertEqual(res["product_name"], "Twinkly")


if __name__ == "__main__":
    unittest.main()
