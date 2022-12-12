from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

ColourDict = Dict[str, int]
ColourTuple = Union[Tuple[int, int, int], Tuple[int, int, int, int]]
TwinklyColourTuple = Union[Tuple[int, int, int], Tuple[int, int, int, int]]


@dataclass(frozen=True)
class TwinklyColour:
    red: int
    green: int
    blue: int
    white: Optional[int] = None

    def as_twinkly_tuple(self) -> TwinklyColourTuple:
        """Convert TwinklyColour to a tuple as used by Twinkly: (R,G,B) or (W,R,G,B)"""
        if self.white is not None:
            return (self.white, self.red, self.green, self.blue)
        else:
            return (self.red, self.green, self.blue)

    def as_tuple(self) -> ColourTuple:
        """Convert TwinklyColour to a tuple: (R,G,B) or (R,G,B,W)"""
        if self.white is not None:
            return (self.red, self.green, self.blue, self.white)
        else:
            return (self.red, self.green, self.blue)

    def __iter__(self):
        for i in self.as_tuple():
            yield i

    def as_dict(self) -> ColourDict:
        """Convert TwinklyColour to a dict wth color names used by set-led functions."""
        if self.white is not None:
            return {
                "red": self.red,
                "green": self.green,
                "blue": self.blue,
                "white": self.white,
            }
        else:
            return {"red": self.red, "green": self.green, "blue": self.blue}

    @classmethod
    def from_twinkly_tuple(cls, t):
        if len(t) == 4:
            return cls(red=t[1], green=t[2], blue=t[3], white=t[0])
        elif len(t) == 3:
            return cls(red=t[0], green=t[1], blue=t[2])
        raise TypeError("Unknown colour format")
