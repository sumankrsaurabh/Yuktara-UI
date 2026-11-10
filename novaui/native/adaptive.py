"""Window-aware adaptive information for native Yuktara UI applications.

All dimensions are logical UI units, never backing pixels or monitor resolution.
The size class is recomputed from the actual application window on every resize.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class WindowWidthSizeClass(str, Enum):
    COMPACT = "compact"
    MEDIUM = "medium"
    EXPANDED = "expanded"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class WindowHeightSizeClass(str, Enum):
    COMPACT = "compact"
    MEDIUM = "medium"
    EXPANDED = "expanded"


@dataclass(frozen=True, slots=True)
class WindowSizeBreakpoints:
    """Logical-unit breakpoints; customizable for non-standard app designs."""

    width_medium: float = 600.0
    width_expanded: float = 840.0
    width_large: float = 1200.0
    width_extra_large: float = 1600.0
    height_medium: float = 480.0
    height_expanded: float = 900.0

    def __post_init__(self):
        values = (
            self.width_medium, self.width_expanded, self.width_large,
            self.width_extra_large, self.height_medium, self.height_expanded,
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not isfinite(float(value)) or value <= 0 for value in values):
            raise ValueError("window breakpoints must be finite positive numbers")
        if not (self.width_medium < self.width_expanded < self.width_large
                < self.width_extra_large):
            raise ValueError("width breakpoints must be strictly increasing")
        if self.height_medium >= self.height_expanded:
            raise ValueError("height breakpoints must be strictly increasing")


@dataclass(frozen=True, slots=True)
class WindowAdaptiveInfo:
    """Snapshot of the app window's adaptive environment.

    width/height are logical UI units. pixel_width/pixel_height describe the
    backing surface and must not be used for layout breakpoint decisions.
    """

    width: float
    height: float
    pixel_width: int
    pixel_height: int
    scale_x: float
    scale_y: float
    width_size_class: WindowWidthSizeClass
    height_size_class: WindowHeightSizeClass
    orientation: str
    aspect_ratio: float

    @property
    def is_compact_width(self) -> bool:
        return self.width_size_class is WindowWidthSizeClass.COMPACT

    @property
    def is_expanded_width(self) -> bool:
        return self.width_size_class in {
            WindowWidthSizeClass.EXPANDED,
            WindowWidthSizeClass.LARGE,
            WindowWidthSizeClass.EXTRA_LARGE,
        }

    @property
    def is_landscape(self) -> bool:
        return self.orientation == "landscape"


def compute_window_adaptive_info(
    width: float,
    height: float,
    *,
    pixel_width: int | None = None,
    pixel_height: int | None = None,
    scale_x: float | None = None,
    scale_y: float | None = None,
    breakpoints: WindowSizeBreakpoints = WindowSizeBreakpoints(),
) -> WindowAdaptiveInfo:
    """Classify the available app window, independently of monitor resolution."""
    for value, name in ((width, "width"), (height, "height")):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a finite positive number")
        if not isfinite(float(value)) or value <= 0:
            raise ValueError(f"{name} must be a finite positive number")

    width, height = float(width), float(height)
    sx = float(scale_x) if scale_x is not None else (
        float(pixel_width) / width if pixel_width is not None else 1.0
    )
    sy = float(scale_y) if scale_y is not None else (
        float(pixel_height) / height if pixel_height is not None else 1.0
    )
    for value, name in ((sx, "scale_x"), (sy, "scale_y")):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")

    if pixel_width is None:
        pixel_width = max(1, round(width * sx))
    if pixel_height is None:
        pixel_height = max(1, round(height * sy))
    for value, name in ((pixel_width, "pixel_width"), (pixel_height, "pixel_height")):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")

    if width >= breakpoints.width_extra_large:
        width_class = WindowWidthSizeClass.EXTRA_LARGE
    elif width >= breakpoints.width_large:
        width_class = WindowWidthSizeClass.LARGE
    elif width >= breakpoints.width_expanded:
        width_class = WindowWidthSizeClass.EXPANDED
    elif width >= breakpoints.width_medium:
        width_class = WindowWidthSizeClass.MEDIUM
    else:
        width_class = WindowWidthSizeClass.COMPACT

    if height >= breakpoints.height_expanded:
        height_class = WindowHeightSizeClass.EXPANDED
    elif height >= breakpoints.height_medium:
        height_class = WindowHeightSizeClass.MEDIUM
    else:
        height_class = WindowHeightSizeClass.COMPACT

    return WindowAdaptiveInfo(
        width=width,
        height=height,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        scale_x=sx,
        scale_y=sy,
        width_size_class=width_class,
        height_size_class=height_class,
        orientation="landscape" if width > height else "portrait" if height > width else "square",
        aspect_ratio=width / height,
    )
