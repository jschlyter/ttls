"""Example of Twinkly movie file"""

import argparse
import random

from ttls.client import TwinklyFrame

RED = (0xff, 0x00, 0x00)
GREEN = (0x00, 0xff, 0x00)
BLUE = (0x00, 0x00, 0xff)


def generate_xmas_frame(n: int) -> TwinklyFrame:
    """Generate a very merry frame"""
    res = []
    for i in range(0, n):
        if random.random() > 0.5:
            res.append(RED)
        else:
            res.append(GREEN)
    return res


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--leds',
                        dest='leds',
                        metavar='n',
                        type=int,
                        default=105,
                        required=False,
                        help="Number of LEDs")
    parser.add_argument('--count',
                        dest='count',
                        metavar='n',
                        type=int,
                        default=10,
                        required=False,
                        help="Number of iterations")
    parser.add_argument('--output',
                        dest='output',
                        metavar='filename',
                        type=str,
                        default='movie.bin',
                        help="Output file")
    args = parser.parse_args()

    movie = []

    for n in range(0, args.count):
        frame = [v for sublist in generate_xmas_frame(args.leds) for v in sublist]
        movie.extend(frame)

    with open(args.output, 'wb') as f:
        f.write(bytes(movie))


if __name__ == "__main__":
    main()
