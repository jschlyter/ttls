import unittest

from ttls.colours import TwinklyColour


class TestTwinklyColours(unittest.TestCase):
    def test_colours(self):
        rgb = TwinklyColour(1, 2, 3)
        rgbw = TwinklyColour(1, 2, 3, 4)

        self.assertEqual(rgb.as_twinkly_tuple(), (1, 2, 3))
        self.assertEqual(rgbw.as_twinkly_tuple(), (4, 1, 2, 3))
        self.assertEqual(tuple(rgb), (1, 2, 3))
        self.assertEqual(tuple(rgbw), (1, 2, 3, 4))
