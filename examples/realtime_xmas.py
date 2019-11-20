"""Example of sending realtime frames to Twinkly"""

import argparse
import random
import time

from ttls.client import Twinkly, TwinklyFrame

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
    parser.add_argument('--host',
                        metavar='hostname',
                        required=True,
                        help='Device address')
    parser.add_argument('--count',
                        dest='count',
                        metavar='n',
                        type=int,
                        default=10,
                        required=False,
                        help="Number of iterations")
    parser.add_argument('--delay',
                        dest='delay',
                        metavar='seconds',
                        type=float,
                        default=0.2,
                        required=False,
                        help="Delay between frames")
    args = parser.parse_args()

    t = Twinkly(host=args.host)
    t.mode = 'rt'

    for _ in range(0, args.count):
        frame = generate_xmas_frame(t.length)
        t.send_frame(frame)
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
