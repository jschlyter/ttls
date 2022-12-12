from dataclasses import dataclass
from typing import Optional, Tuple, Union

ColourTuple = Union[Tuple[int, int, int], Tuple[int, int, int, int]]


@dataclass(frozen=True)
class TwinklyColour:
    r: int
    g: int
    b: int
    w: Optional[int] = None

    def as_twinkly_tuple(self) -> ColourTuple:
        """Convert TwinklyColour to a tuple as used by Twinkly: (R,G,B) or (W,R,G,B)"""
        return (
            (self.w, self.r, self.g, self.b)
            if self.w is not None
            else (self.r, self.g, self.b)
        )

    def as_tuple(self) -> ColourTuple:
        """Convert TwinklyColour to a tuple: (R,G,B) or (R,G,B,W)"""
        return (
            (self.r, self.g, self.b, self.w)
            if self.w is not None
            else (self.r, self.g, self.b)
        )

    def __iter__(self):
        for i in self.as_tuple():
            yield i
