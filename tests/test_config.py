import unittest

from ttls.client import Twinkly


class TestTwinklyConfig(unittest.TestCase):
    def setUp(self):
        self.client = Twinkly(host="192.0.2.1")

    def test_set_default_mode(self):
        self.client.default_mode = "movie"
        self.assertEqual(self.client.default_mode, "movie")
        with self.assertRaises(ValueError):
            self.client.default_mode = "b0rken"
