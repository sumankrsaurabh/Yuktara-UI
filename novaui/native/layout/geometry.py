"""Geometry and constraint primitives for Yuktara UI's native layout engine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


def _number(value: float, name: str, *, allow_infinity: bool = False) -> float:
    """Validate a geometry scalar without silently accepting bool or NaN."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if math.isnan(result) or (not allow_infinity and not math.isfinite(result)):
        qualifier = "not NaN" if allow_infinity else "finite"
        raise ValueError(f"{name} must be {qualifier}")
    return result


def _finite_nonnegative(value: float, name: str) -> float:
    result = _number(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


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

    def __post_init__(self):
        _number(self.x, "x")
        _number(self.y, "y")


@dataclass(frozen=True)
class Rect:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    def __post_init__(self):
        _number(self.x, "x")
        _number(self.y, "y")
        _finite_nonnegative(self.width, "width")
        _finite_nonnegative(self.height, "height")

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def size(self):
        return Size(self.width, self.height)

    def contains(self, point: Point) -> bool:
        return self.x <= point.x < self.right and self.y <= point.y < self.bottom

    def inset(self, insets: "Insets") -> "Rect":
        w = max(0.0, self.width - insets.horizontal)
        h = max(0.0, self.height - insets.vertical)
        return Rect(self.x + insets.left, self.y + insets.top, w, h)


@dataclass(frozen=True)
class Insets:
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    def __post_init__(self):
        for name in ("top", "right", "bottom", "left"):
            _finite_nonnegative(getattr(self, name), name)

    @classmethod
    def all(cls, value: float) -> "Insets":
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, vertical: float = 0.0, horizontal: float = 0.0) -> "Insets":
        return cls(vertical, horizontal, vertical, horizontal)

    @property
    def horizontal(self):
        return self.left + self.right

    @property
    def vertical(self):
        return self.top + self.bottom


@dataclass(frozen=True)
class Constraints:
    min_width: float = 0.0
    max_width: float = math.inf
    min_height: float = 0.0
    max_height: float = math.inf

    def __post_init__(self):
        for name in ("min_width", "min_height"):
            value = _finite_nonnegative(getattr(self, name), name)
        for name in ("max_width", "max_height"):
            value = _number(getattr(self, name), name, allow_infinity=True)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.min_width > self.max_width or self.min_height > self.max_height:
            raise ValueError("minimum constraints cannot exceed maximum constraints")

    def constrain(self, size: Size) -> Size:
        return Size(
            min(max(size.width, self.min_width), self.max_width),
            min(max(size.height, self.min_height), self.max_height),
        )

    def loosen(self) -> "Constraints":
        return Constraints(0, self.max_width, 0, self.max_height)

    def with_max(self, width: float, height: float) -> "Constraints":
        return Constraints(
            self.min_width, min(self.max_width, width),
            self.min_height, min(self.max_height, height),
        )


class Alignment(str, Enum):
    START = "start"
    CENTER = "center"
    END = "end"
    STRETCH = "stretch"
    BASELINE = "baseline"


class MainAxisAlignment(str, Enum):
    START = "start"
    CENTER = "center"
    END = "end"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"
