"""Experimental native rendering foundation for Yuktara UI.

This package contains the native SDL3 + Skia runtime and no browser-rendering stack.
"""
from .renderer import SkiaRenderer, RenderSize
from .typography import FontConfig, FontResolver, DEFAULT_FONT_FAMILY

__all__ = [
    "DEFAULT_FONT_FAMILY",
    "FontConfig",
    "FontResolver",
    "RenderSize",
    "SkiaRenderer",
]

# SDL3 is imported explicitly from novaui.native.platform to keep it optional.

from .runtime import NativeRuntime
__all__.append("NativeRuntime")

from .dependencies import DependencyError, ensure_skia_python, ensure_sdl3_runtime
__all__ += ["DependencyError", "ensure_skia_python", "ensure_sdl3_runtime"]

from .accessibility import SemanticNode, build_accessibility_tree
from .widgets import (Badge, Button, Card, Checkbox, Divider, Label, ProgressBar,
                      RadioGroup, Spacer, Switch, column, row, stack)
__all__ += [
    "SemanticNode", "build_accessibility_tree", "Badge", "Button", "Card",
    "Checkbox", "Divider", "Label", "ProgressBar", "RadioGroup", "Spacer", "Switch",
    "column", "row", "stack",
]

from .theme import NativeTheme
from .layout import (Alignment, Constraints, Insets, MainAxisAlignment, Point,
                     Rect, Size, LayoutEngine, LayoutNode)
__all__ += [
    "NativeTheme", "Alignment", "Constraints", "Insets", "MainAxisAlignment",
    "Point", "Rect", "Size", "LayoutEngine", "LayoutNode",
]
