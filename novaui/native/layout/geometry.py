"""Geometry and constraint primitives for Yuktara UI's native layout engine."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math

def _finite_nonnegative(value: float, name: str) -> float:
    value=float(value)
    if math.isnan(value) or value < 0:
        raise ValueError(f"{name} must be non-negative and not NaN")
    return value

@dataclass(frozen=True)
class Size:
    width: float = 0.0
    height: float = 0.0
    def __post_init__(self):
        _finite_nonnegative(self.width, "width")
        _finite_nonnegative(self.height, "height")

@dataclass(frozen=True)
class Point:
    x: float = 0.0
    y: float = 0.0

@dataclass(frozen=True)
class Rect:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    @property
    def right(self): return self.x + self.width
    @property
    def bottom(self): return self.y + self.height
    @property
    def size(self): return Size(self.width, self.height)
    def contains(self, point: Point) -> bool:
        return self.x <= point.x < self.right and self.y <= point.y < self.bottom
    def inset(self, insets: "Insets") -> "Rect":
        w=max(0.0,self.width-insets.horizontal)
        h=max(0.0,self.height-insets.vertical)
        return Rect(self.x+insets.left,self.y+insets.top,w,h)

@dataclass(frozen=True)
class Insets:
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    def __post_init__(self):
        for name in ("top","right","bottom","left"):
            _finite_nonnegative(getattr(self,name), name)
    @classmethod
    def all(cls, value: float) -> "Insets":
        return cls(value,value,value,value)
    @classmethod
    def symmetric(cls, vertical: float=0.0, horizontal: float=0.0) -> "Insets":
        return cls(vertical,horizontal,vertical,horizontal)
    @property
    def horizontal(self): return self.left+self.right
    @property
    def vertical(self): return self.top+self.bottom

@dataclass(frozen=True)
class Constraints:
    min_width: float = 0.0
    max_width: float = math.inf
    min_height: float = 0.0
    max_height: float = math.inf
    def __post_init__(self):
        for name in ("min_width","max_width","min_height","max_height"):
            value=getattr(self,name)
            if math.isnan(value) or value < 0:
                raise ValueError(f"{name} must be non-negative and not NaN")
        if self.min_width > self.max_width or self.min_height > self.max_height:
            raise ValueError("minimum constraints cannot exceed maximum constraints")
    def constrain(self, size: Size) -> Size:
        return Size(min(max(size.width,self.min_width),self.max_width),
                    min(max(size.height,self.min_height),self.max_height))
    def loosen(self) -> "Constraints":
        return Constraints(0,self.max_width,0,self.max_height)
    def with_max(self, width: float, height: float) -> "Constraints":
        return Constraints(self.min_width,min(self.max_width,width),
                           self.min_height,min(self.max_height,height))

class Alignment(str, Enum):
    START="start"
    CENTER="center"
    END="end"
    STRETCH="stretch"

class MainAxisAlignment(str, Enum):
    START="start"
    CENTER="center"
    END="end"
    SPACE_BETWEEN="space-between"
    SPACE_AROUND="space-around"
    SPACE_EVENLY="space-evenly"
