from dataclasses import dataclass

ColourDict = dict[str, int]
ColourTuple = tuple[int, int, int] | tuple[int, int, int, int] | tuple[int, int, int, int, int]
TwinklyColourTuple = tuple[int, int, int] | tuple[int, int, int, int] | tuple[int, int, int, int, int]


@dataclass(frozen=True)
class TwinklyColour:
    red: int
    green: int
    blue: int
    white: int | None = None
    cold_white: int | None = None

    def __post_init__(self):
        if self.cold_white is not None and self.white is None:
            raise ValueError("cold_white requires white to be set")

    def as_twinkly_tuple(self) -> TwinklyColourTuple:
        """Convert TwinklyColour to a tuple as used by Twinkly: (R,G,B), (W,R,G,B) or (CW,W,R,G,B)"""
        if self.cold_white is not None and self.white is not None:
            return (self.cold_white, self.white, self.red, self.green, self.blue)
        elif self.white is not None:
            return (self.white, self.red, self.green, self.blue)
        else:
            return (self.red, self.green, self.blue)

    def as_tuple(self) -> ColourTuple:
        """Convert TwinklyColour to a tuple: (R,G,B), (R,G,B,W) or (R,G,B,W,CW)"""
        if self.cold_white is not None and self.white is not None:
            return (self.red, self.green, self.blue, self.white, self.cold_white)
        elif self.white is not None:
            return (self.red, self.green, self.blue, self.white)
        else:
            return (self.red, self.green, self.blue)

    def __iter__(self):
        yield from self.as_tuple()

    def as_dict(self) -> ColourDict:
        """Convert TwinklyColour to a dict wth color names used by set-led functions."""
        return {
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
            **({"white": self.white} if self.white is not None else {}),
            **({"cold_white": self.cold_white} if self.cold_white is not None else {}),
        }

    @classmethod
    def from_twinkly_tuple(cls, t):
        match len(t):
            case 5:
                return cls(red=t[2], green=t[3], blue=t[4], white=t[1], cold_white=t[0])
            case 4:
                return cls(red=t[1], green=t[2], blue=t[3], white=t[0])
            case 3:
                return cls(red=t[0], green=t[1], blue=t[2])
            case _:
                raise TypeError("Unknown colour format")
