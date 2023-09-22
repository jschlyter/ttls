import unittest

from ttls.colours import TwinklyColour


class TestTwinklyColours(unittest.TestCase):
    def test_colours_rgb(self):
        col = TwinklyColour(1, 2, 3)
        self.assertEqual(col.as_twinkly_tuple(), (1, 2, 3))
        self.assertEqual(tuple(col), (1, 2, 3))
        self.assertEqual(col.as_dict(), {"blue": 3, "green": 2, "red": 1})

        col = TwinklyColour.from_twinkly_tuple((1, 2, 3))
        self.assertEqual(col.as_twinkly_tuple(), (1, 2, 3))
        self.assertEqual(tuple(col), (1, 2, 3))
        self.assertEqual(col.as_dict(), {"blue": 3, "green": 2, "red": 1})

        rgb = TwinklyColour.from_twinkly_tuple((1, 2, 3))
        self.assertEqual(rgb.as_dict(), {"blue": 3, "green": 2, "red": 1})

    def test_colours_rgbw(self):
        col = TwinklyColour(1, 2, 3, 4)
        self.assertEqual(col.as_twinkly_tuple(), (4, 1, 2, 3))
        self.assertEqual(tuple(col), (1, 2, 3, 4))
        self.assertEqual(col.as_dict(), {"blue": 3, "green": 2, "red": 1, "white": 4})

        rgbw = TwinklyColour.from_twinkly_tuple((1, 2, 3, 4))
        self.assertEqual(rgbw.as_dict(), {"blue": 4, "green": 3, "red": 2, "white": 1})
