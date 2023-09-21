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


class TestTwinklyGeneric(aiounittest.AsyncTestCase):
    @classmethod
    def setUpClass(self):
        logging.basicConfig(level=logging.DEBUG)

    def setUp(self):
        self.client = TwinklyMock(host="192.0.2.1")

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


if __name__ == "__main__":
    unittest.main()
