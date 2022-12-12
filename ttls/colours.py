from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

ColourTuple = Union[Tuple[int, int, int], Tuple[int, int, int, int]]
ColourDict = Dict[str, int]


@dataclass(frozen=True)
class TwinklyColour:
    r: int
    g: int
    b: int
    w: Optional[int] = None

    def as_twinkly_tuple(self) -> ColourTuple:
        """Convert TwinklyColour to a tuple as used by Twinkly: (R,G,B) or (W,R,G,B)"""
        if self.w is not None:
            return (self.w, self.r, self.g, self.b)
        else:
            return (self.r, self.g, self.b)

    def as_tuple(self) -> ColourTuple:
        """Convert TwinklyColour to a tuple: (R,G,B) or (R,G,B,W)"""
        if self.w is not None:
            return (self.r, self.g, self.b, self.w)
        else:
            return (self.r, self.g, self.b)

    def __iter__(self):
        for i in self.as_tuple():
            yield i

    def as_dict(self) -> ColourDict:
        """Convert TwinklyColour to a dict wth color names used by set-led functions."""
        if self.w is not None:
            return {
                "red": self.r,
                "green": self.g,
                "blue": self.b,
                "white": self.w,
            }
        else:
            return {"red": self.r, "green": self.g, "blue": self.b}
