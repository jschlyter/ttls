"""Pre-registered tests for turning Twinkly devices on."""

from unittest.mock import AsyncMock

import aiounittest

from ttls.client import Twinkly


class TestTwinklyTurnOn(aiounittest.AsyncTestCase):
    def setUp(self):
        self.client = Twinkly(host="192.0.2.1", api_version=1)
        self.client.get_saved_movies = AsyncMock(return_value={"movies": []})
        self.client.set_mode = AsyncMock(return_value=None)

    async def test_falls_back_to_color_without_movies(self):
        """Turn on in color mode when the default movie has no saved movie."""
        await self.client.turn_on()

        self.client.get_saved_movies.assert_awaited_once_with()
        self.client.set_mode.assert_awaited_once_with("color")

    async def test_uses_movie_when_available(self):
        """Keep movie mode when at least one saved movie exists."""
        self.client.get_saved_movies.return_value = {"movies": [{"id": 0}]}

        await self.client.turn_on()

        self.client.get_saved_movies.assert_awaited_once_with()
        self.client.set_mode.assert_awaited_once_with("movie")

    async def test_does_not_check_movies_for_other_modes(self):
        """Do not query movies for explicit non-movie defaults."""
        for mode in ("color", "effect", "playlist", "demo", "rt"):
            with self.subTest(mode=mode):
                self.client.default_mode = mode
                self.client.get_saved_movies.reset_mock()
                self.client.set_mode.reset_mock()

                await self.client.turn_on()

                self.client.get_saved_movies.assert_not_awaited()
                self.client.set_mode.assert_awaited_once_with(mode)
