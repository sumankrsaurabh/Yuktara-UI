"""Experimental native rendering foundation for Yuktara UI.

This package contains the native SDL3 + Skia runtime and no browser-rendering stack.
"""
from .renderer import SkiaRenderer, RenderSize
from .typography import (FontConfig, FontResolver, FontRun, DEFAULT_FONT_FAMILY)

__all__ = [
    "DEFAULT_FONT_FAMILY",
    "FontConfig",
    "FontResolver",
    "FontRun",
    "RenderSize",
    "SkiaRenderer",
]

# SDL3 is imported explicitly from novaui.native.platform to keep it optional.

from .runtime import NativeRuntime
from .animations import AnimationHandle, AnimationManager
from .overlays import OverlayHandle, OverlayManager
__all__ += ["NativeRuntime", "OverlayHandle", "OverlayManager",
            "AnimationHandle", "AnimationManager"]

from .dependencies import DependencyError, ensure_skia_python, ensure_sdl3_runtime
__all__ += ["DependencyError", "ensure_skia_python", "ensure_sdl3_runtime"]

from .accessibility import SemanticNode, build_accessibility_tree
from .widgets import (Badge, Button, Card, Checkbox, Divider, Dropdown, Label,
                      ProgressBar, RadioGroup, RichText, SegmentedControl, Slider, Spacer,
                      Switch, TabItem, Tabs, TextArea, TextField, column, row, stack,
                      ContextMenu, Dialog, MenuItem, Popover, Toast, Tooltip,
                      Calendar, Container, DatePicker, Grid, GridItem, Image, NavigationDrawer,
                      NavigationItem, Positioned, ScrollView, Table, TreeItem, TreeView, FilePicker)
__all__ += [
    "SemanticNode", "build_accessibility_tree", "Badge", "Button", "Card",
    "Checkbox", "Divider", "Dropdown", "Label", "ProgressBar", "RadioGroup", "RichText",
    "SegmentedControl", "Slider", "Spacer", "Switch", "TabItem", "Tabs",
    "TextArea", "TextField", "column", "row", "stack", "ContextMenu",
    "Dialog", "MenuItem", "Popover", "Toast", "Tooltip", "Calendar",
    "Container", "DatePicker", "Grid", "GridItem", "Image", "NavigationDrawer",
    "NavigationItem", "Positioned", "ScrollView", "Table", "TreeItem", "TreeView", "FilePicker",
]

from .theme import NativeTheme
from .layout import (Alignment, Constraints, Insets, MainAxisAlignment, Point,
                     Rect, Size, LayoutEngine, LayoutNode)
__all__ += [
    "NativeTheme", "Alignment", "Constraints", "Insets", "MainAxisAlignment",
    "Point", "Rect", "Size", "LayoutEngine", "LayoutNode",
]

from .text import (ParagraphStyle, TextCluster, TextLayout, TextLine, TextMeasurer,
                   TextPaintRun, TextParagraph, TextStyleSpan, HarfBuzzShaper,
                   ShapedCluster, ShapedGlyphRun, ShapedText, grapheme_spans,
                   next_grapheme_boundary, normalize_grapheme_boundary,
                   previous_grapheme_boundary, can_break_between,
                   is_nonbreaking_boundary, line_break_offsets)
__all__ += ["ParagraphStyle", "TextCluster", "TextLayout", "TextLine", "TextMeasurer",
            "TextPaintRun", "TextParagraph", "TextStyleSpan",
            "HarfBuzzShaper", "ShapedCluster", "ShapedGlyphRun", "ShapedText",
            "grapheme_spans", "next_grapheme_boundary",
            "normalize_grapheme_boundary", "previous_grapheme_boundary",
            "can_break_between", "is_nonbreaking_boundary", "line_break_offsets"]

from .document import (PageSize, PageMargins, PageBreak, DocumentParagraph, PageTemplate,
                       PositionedPageText, ParagraphFragment, DocumentPage,
                       DocumentLayout, DocumentPaginator)
__all__ += ["PageSize", "PageMargins", "PageBreak", "DocumentParagraph",
            "PageTemplate", "PositionedPageText", "ParagraphFragment",
            "DocumentPage", "DocumentLayout", "DocumentPaginator"]
