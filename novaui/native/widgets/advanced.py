"""General-purpose native layout and application widgets.

These controls build retained LayoutNode trees. They do not embed HTML or a
browser runtime and remain usable with any renderer implementing Yuktara's
native drawing protocol.
"""
from __future__ import annotations

import calendar as _calendar
from math import isfinite
from dataclasses import dataclass, field
from datetime import date
from os import PathLike
from typing import Callable, Sequence

from ..layout import Alignment, Insets, LayoutNode, Size
from ..theme import NativeTheme
from .core import _node, _text_node


def _insets(value: float | Insets, name: str) -> Insets:
    if isinstance(value, Insets):
        return value
    if not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{name} must be a non-negative number or Insets")
    return Insets.all(float(value))


@dataclass(frozen=True)
class ResponsiveVariant:
    """A layout tree selected when its parent reaches a minimum UI width."""

    min_width: float
    child: object


@dataclass
class Responsive:
    """Select compact, medium or expanded composition from available width.

    Variants are ordered by strictly increasing minimum width. The first
    variant is the fallback below its threshold. The active child is selected
    during layout, so a window resize can switch variants without rebuilding
    the application component.
    """

    variants: Sequence[ResponsiveVariant | tuple[float, object]]
    padding: float | Insets = 0
    align: Alignment = Alignment.STRETCH
    key: str | None = None

    def build(self) -> LayoutNode:
        if not self.variants:
            raise ValueError("Responsive requires at least one variant")
        normalized = []
        previous_width = -1.0
        for variant in self.variants:
            if isinstance(variant, ResponsiveVariant):
                minimum_width, child = variant.min_width, variant.child
            elif isinstance(variant, (tuple, list)) and len(variant) == 2:
                minimum_width, child = variant
            else:
                raise TypeError("responsive variants must be ResponsiveVariant or (min_width, child) pairs")
            if (not isinstance(minimum_width, (int, float))
                    or isinstance(minimum_width, bool)
                    or minimum_width < 0):
                raise ValueError("responsive variant min_width must be non-negative")
            minimum_width = float(minimum_width)
            if minimum_width <= previous_width:
                raise ValueError("responsive variant min_width values must be strictly increasing")
            if child is None:
                raise ValueError("responsive variant children cannot be None")
            normalized.append((minimum_width, _node(child)))
            previous_width = minimum_width
        return LayoutNode(
            "responsive",
            responsive_variants=tuple(normalized),
            padding=_insets(self.padding, "padding"),
            align=self.align,
            key=self.key,
            accessibility_role="group",
        )


@dataclass(frozen=True)
class AdaptiveVariant:
    """A composition selected when both minimum logical window dimensions fit."""

    min_width: float
    min_height: float
    child: object

    def __post_init__(self):
        for value, name in ((self.min_width, "min_width"), (self.min_height, "min_height")):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or value < 0):
                raise ValueError(f"AdaptiveVariant {name} must be a non-negative number")
        if self.child is None:
            raise ValueError("AdaptiveVariant child cannot be None")


@dataclass
class AdaptiveLayout:
    """Choose a retained layout variant using available width AND height.

    The first variant is the fallback. Later matching variants take
    precedence, allowing explicit height-only and width-only alternatives.
    Thresholds use logical window units, independent of display scaling.
    """

    variants: Sequence[AdaptiveVariant | tuple[float, float, object]]
    padding: float | Insets = 0
    align: Alignment = Alignment.STRETCH
    key: str | None = None

    def build(self) -> LayoutNode:
        if not self.variants:
            raise ValueError("AdaptiveLayout requires at least one variant")
        normalized = []
        seen_thresholds = set()
        for variant in self.variants:
            if isinstance(variant, AdaptiveVariant):
                minimum_width, minimum_height, child = (
                    variant.min_width, variant.min_height, variant.child
                )
            elif isinstance(variant, (tuple, list)) and len(variant) == 3:
                minimum_width, minimum_height, child = variant
            else:
                raise TypeError(
                    "adaptive variants must be AdaptiveVariant or (min_width, min_height, child) triples"
                )
            values = (minimum_width, minimum_height)
            if any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or value < 0 for value in values):
                raise ValueError("adaptive variant minimum dimensions must be non-negative")
            current = (float(minimum_width), float(minimum_height))
            if current in seen_thresholds:
                raise ValueError("adaptive variant thresholds must be unique")
            if child is None:
                raise ValueError("adaptive variant children cannot be None")
            normalized.append((current[0], current[1], _node(child)))
            seen_thresholds.add(current)
        return LayoutNode(
            "adaptive", adaptive_variants=tuple(normalized),
            padding=_insets(self.padding, "padding"), align=self.align,
            key=self.key, accessibility_role="group",
        )


@dataclass
class Container:
    """A styled native container with padding, margin, border and alignment."""
    child: object | None = None
    children: Sequence[object] = ()
    width: float | str | None = None
    height: float | str | None = None
    min_width: float | str | None = None
    max_width: float | str | None = None
    min_height: float | str | None = None
    max_height: float | str | None = None
    position: str = "flow"
    left: float | str | None = None
    right: float | str | None = None
    top: float | str | None = None
    bottom: float | str | None = None
    padding: float | Insets = 12
    margin: float | Insets = 0
    spacing: float = 8
    background: int | None = None
    radius: float = 0
    border_color: int | None = None
    border_width: float = 0
    align: Alignment = Alignment.STRETCH
    theme: NativeTheme = field(default_factory=NativeTheme)

    def build(self) -> LayoutNode:
        if self.spacing < 0 or self.radius < 0 or self.border_width < 0:
            raise ValueError("Container spacing, radius and border width must be non-negative")
        content = list(self.children)
        if self.child is not None:
            if content:
                raise ValueError("Use either child or children, not both")
            content = [self.child]
        nodes = [_node(item) for item in content]
        child_node = (nodes[0] if len(nodes) == 1 else
                      LayoutNode.column(*nodes, spacing=self.spacing) if nodes else None)
        styled = LayoutNode.box(
            child_node, padding=_insets(self.padding, "padding"),
            background=self.background,
            radius=self.radius,
            border_color=self.border_color,
            border_width=self.border_width,
            align=self.align,
            intrinsic_size=Size(),
            accessibility_role="group",
        )
        margin = _insets(self.margin, "margin")
        return LayoutNode.box(
            styled, width=self.width, height=self.height,
            min_width=self.min_width, max_width=self.max_width,
            min_height=self.min_height, max_height=self.max_height,
            position=self.position, left=self.left, right=self.right,
            top=self.top, bottom=self.bottom, padding=margin,
            accessibility_role="group",
        )


@dataclass(frozen=True)
class GridItem:
    """A grid child with optional explicit cell and span information."""
    child: object
    row: int | None = None
    column: int | None = None
    row_span: int = 1
    column_span: int = 1

    def __post_init__(self):
        if self.row is not None and self.row < 0:
            raise ValueError("GridItem row must be non-negative")
        if self.column is not None and self.column < 0:
            raise ValueError("GridItem column must be non-negative")
        if self.row_span < 1 or self.column_span < 1:
            raise ValueError("GridItem spans must be at least 1")


@dataclass
class Positioned:
    """Place a child relative to its parent's content box, outside normal flow."""
    child: object
    left: float | str | None = None
    right: float | str | None = None
    top: float | str | None = None
    bottom: float | str | None = None
    width: float | str | None = None
    height: float | str | None = None
    min_width: float | str | None = None
    max_width: float | str | None = None
    min_height: float | str | None = None
    max_height: float | str | None = None

    def build(self) -> LayoutNode:
        return LayoutNode.box(
            _node(self.child), position="absolute", left=self.left,
            right=self.right, top=self.top, bottom=self.bottom,
            width=self.width, height=self.height,
            min_width=self.min_width, max_width=self.max_width,
            min_height=self.min_height, max_height=self.max_height,
        )


@dataclass
class Grid:
    """Equal-track grid that can reduce its column count at narrow widths.

    ``columns`` is the maximum column count. When ``min_column_width`` is set,
    the layout engine chooses the largest count that fits the available width.
    """
    children: Sequence[object] = ()
    columns: int = 2
    column_gap: float = 12
    row_gap: float = 12
    min_column_width: float | None = None
    width: float | str | None = None
    height: float | str | None = None
    cross_align: Alignment = Alignment.STRETCH
    accessibility_label: str = "Grid"

    def __post_init__(self):
        if self.columns < 1:
            raise ValueError("Grid columns must be at least 1")
        if self.column_gap < 0 or self.row_gap < 0:
            raise ValueError("Grid gaps must be non-negative")
        if self.min_column_width is not None and self.min_column_width <= 0:
            raise ValueError("min_column_width must be positive")

    def build(self) -> LayoutNode:
        cells = []
        for entry in self.children:
            if isinstance(entry, GridItem):
                child_node = _node(entry.child)
                cell = LayoutNode.box(
                    child_node, grid_row=entry.row, grid_column=entry.column,
                    grid_row_span=entry.row_span, grid_column_span=entry.column_span,
                    accessibility_role="gridcell",
                    accessibility_label=child_node.accessibility_label or child_node.text,
                )
            else:
                child_node = _node(entry)
                cell = LayoutNode.box(
                    child_node, accessibility_role="gridcell",
                    accessibility_label=child_node.accessibility_label or child_node.text,
                )
            cells.append(cell)
        return LayoutNode(
            "grid", cells,
            width=self.width, height=self.height,
            grid_columns=self.columns,
            grid_min_column_width=self.min_column_width,
            grid_column_gap=self.column_gap,
            grid_row_gap=self.row_gap,
            cross_align=self.cross_align,
            accessibility_role="grid",
            accessibility_label=self.accessibility_label,
        )


@dataclass
class ScrollView:
    """A clipped scroll viewport around one child widget or layout node."""
    child: object
    axis: str = "vertical"
    width: float | str | None = None
    height: float | str | None = None
    background: int | None = None
    padding: float | Insets = 0
    accessibility_label: str | None = None

    def build(self) -> LayoutNode:
        if self.axis not in {"vertical", "horizontal", "both"}:
            raise ValueError("ScrollView axis must be vertical, horizontal or both")
        return LayoutNode.scroll(
            _node(self.child), scroll_axis=self.axis, width=self.width,
            height=self.height, background=self.background,
            padding=_insets(self.padding, "padding"),
            accessibility_role="scrollview",
            accessibility_label=self.accessibility_label or "Scrollable content",
        )


@dataclass
class Image:
    """Native image view. ``source`` can be a path, encoded bytes or Skia image."""
    source: str | PathLike | bytes | bytearray | memoryview | object
    width: float = 160
    height: float = 120
    fit: str = "contain"
    alt: str = "Image"
    radius: float = 0
    background: int | None = None
    opacity: float = 1.0

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Image width and height must be positive")
        if self.fit not in {"contain", "cover", "fill", "none"}:
            raise ValueError("Image fit must be contain, cover, fill or none")
        if self.radius < 0 or not 0 <= self.opacity <= 1:
            raise ValueError("Image radius must be non-negative and opacity between 0 and 1")
        if not self.alt:
            raise ValueError("Image alt text must not be empty")

    def build(self) -> LayoutNode:
        node = LayoutNode(
            "box", width=self.width, height=self.height,
            intrinsic_size=Size(self.width, self.height),
            background=self.background,
            radius=self.radius,
            accessibility_role="image",
            accessibility_label=self.alt,
            opacity=self.opacity,
        )

        def paint(renderer, target):
            draw_image = getattr(renderer, "draw_image", None)
            if callable(draw_image):
                draw_image(self.source, target.content_bounds.x, target.content_bounds.y,
                           target.content_bounds.width, target.content_bounds.height,
                           fit=self.fit, radius=target.radius, opacity=target.opacity)

        node.paint_callback = paint
        return node


@dataclass
class Table:
    """Accessible table built from native rows and weighted cell containers."""
    rows: Sequence[Sequence[object]]
    headers: Sequence[object] | None = None
    column_widths: Sequence[float] | None = None
    row_height: float | None = None
    header_height: float | None = None
    cell_padding: float = 9
    border_color: int | None = None
    striped: bool = True
    theme: NativeTheme = field(default_factory=NativeTheme)
    accessibility_label: str = "Table"

    def __post_init__(self):
        if self.row_height is not None and self.row_height <= 0:
            raise ValueError("row_height must be positive")
        if self.header_height is not None and self.header_height <= 0:
            raise ValueError("header_height must be positive")
        if self.cell_padding < 0:
            raise ValueError("cell_padding must be non-negative")
        widths = self.column_widths
        if widths is not None and (not widths or any(value <= 0 for value in widths)):
            raise ValueError("column_widths must contain positive weights")
        count = len(self.headers) if self.headers is not None else (len(self.rows[0]) if self.rows else 0)
        if count == 0:
            raise ValueError("Table needs at least one column")
        for row in self.rows:
            if len(row) != count:
                raise ValueError("Every table row must have the same number of cells")
        if widths is not None and len(widths) != count:
            raise ValueError("column_widths length must match the table column count")

    def build(self) -> LayoutNode:
        t = self.theme
        weights = tuple(self.column_widths or (1.0,) *
                        (len(self.headers) if self.headers is not None else len(self.rows[0])))
        border = self.border_color if self.border_color is not None else t.border
        row_nodes = []

        def make_row(values, *, header=False, index=0):
            cells = []
            for column_index, value in enumerate(values):
                child = (_text_node(value, color=t.foreground, size=13,
                                    weight="semibold" if header else "normal",
                                    role="text", label=value)
                         if isinstance(value, str) else _node(value))
                cell = LayoutNode.box(
                    child, weight=weights[column_index],
                    padding=Insets.all(self.cell_padding),
                    background=(t.surface_variant if header else
                                (t.surface if not self.striped or index % 2 == 0 else t.background)),
                    border_color=border, border_width=0.5,
                    accessibility_role="columnheader" if header else "cell",
                )
                cells.append(cell)
            return LayoutNode.row(
                *cells, spacing=0,
                height=(self.header_height if header else self.row_height),
                cross_align=Alignment.STRETCH,
                accessibility_role="row",
            )

        if self.headers is not None:
            row_nodes.append(make_row(self.headers, header=True))
        row_nodes.extend(make_row(values, index=index) for index, values in enumerate(self.rows))
        return LayoutNode.column(
            *row_nodes, spacing=0,
            accessibility_role="table", accessibility_label=self.accessibility_label,
        )


@dataclass(frozen=True)
class NavigationItem:
    label: str
    icon: str | None = None
    disabled: bool = False
    badge: str | None = None
    key: str | None = None

    def __post_init__(self):
        if not self.label:
            raise ValueError("Navigation item label must not be empty")


@dataclass
class NavigationDrawer:
    """Selectable native navigation panel with compact and expanded modes."""
    items: Sequence[NavigationItem]
    selected: str | None = None
    on_select: Callable[[NavigationItem], None] | None = None
    header: object | None = None
    footer: object | None = None
    width: float = 248
    compact: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.width <= 0:
            raise ValueError("NavigationDrawer width must be positive")
        if not self.items:
            raise ValueError("NavigationDrawer needs at least one item")
        if any(not isinstance(item, NavigationItem) for item in self.items):
            raise TypeError("items must contain NavigationItem instances")
        keys = [item.key or item.label for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Navigation item keys must be unique")
        if self.selected is not None and self.selected not in keys:
            raise ValueError("selected must match an item key or label")
        self._root: LayoutNode | None = None
        self._item_nodes: dict[str, LayoutNode] = {}

    def _key(self, item):
        return item.key or item.label

    def _select(self, item):
        if item.disabled:
            return
        self.selected = self._key(item)
        self._sync_selection()
        if self.on_select is not None:
            self.on_select(item)

    def _sync_selection(self):
        t = self.theme
        for item in self.items:
            key = self._key(item)
            node = self._item_nodes.get(key)
            if node is None:
                continue
            selected = self.selected == key or self.selected == item.label
            node.background = t.primary_soft if selected else None
            node.text_color = (t.disabled_text if item.disabled else
                               t.primary if selected else t.foreground)
            node.accessibility_selected = selected

    def build(self):
        t = self.theme
        children = []
        if self.header is not None:
            children.append(_node(self.header))
        self._item_nodes = {}
        for item in self.items:
            key = self._key(item)
            selected = self.selected in {key, item.label}
            prefix = (item.icon + "  ") if item.icon else ""
            suffix = ("   " + item.badge) if item.badge else ""
            label = (item.icon or item.label) if self.compact else prefix + item.label + suffix
            node = LayoutNode(
                "text", text=label, font_size=14,
                text_color=t.disabled_text if item.disabled else (t.primary if selected else t.foreground),
                padding=Insets.symmetric(vertical=10, horizontal=12),
                background=t.primary_soft if selected else None,
                radius=t.radius_small,
                accessibility_role="navigationitem", accessibility_label=item.label,
                accessibility_disabled=item.disabled, accessibility_selected=selected,
                on_click=None if item.disabled else (lambda _event=None, value=item: self._select(value)),
            )
            self._item_nodes[key] = node
            children.append(node)
        if self.footer is not None:
            children.append(_node(self.footer))
        self._root = LayoutNode.column(
            *children, spacing=6, padding=Insets.all(10), width=self.width,
            background=t.surface, border_color=t.border, border_width=1,
            accessibility_role="navigation", accessibility_label="Main navigation",
        )
        return self._root


@dataclass
class NavigationScaffold:
    """Window-adaptive navigation chrome around a persistent content view.

    Compact windows use a bottom bar, medium windows use a navigation rail,
    and spacious desktop windows use a full drawer. The same content node and
    selection model are retained across all three compositions.
    """

    items: Sequence[NavigationItem]
    content: object
    selected: str | None = None
    on_select: Callable[[NavigationItem], None] | None = None
    min_rail_width: float = 600
    min_drawer_width: float = 1100
    min_drawer_height: float = 640
    drawer_width: float = 248
    rail_width: float = 76
    bottom_height: float = 68
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if not self.items:
            raise ValueError("NavigationScaffold needs at least one item")
        if any(not isinstance(item, NavigationItem) for item in self.items):
            raise TypeError("items must contain NavigationItem instances")
        keys = [item.key or item.label for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Navigation item keys must be unique")
        if self.selected is not None and self.selected not in keys and self.selected not in {
            item.label for item in self.items
        }:
            raise ValueError("selected must match an item key or label")
        dimensions = (
            self.min_rail_width, self.min_drawer_width, self.min_drawer_height,
            self.drawer_width, self.rail_width, self.bottom_height,
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not isfinite(float(value)) or value <= 0 for value in dimensions):
            raise ValueError("navigation scaffold dimensions must be finite and positive")
        if self.min_drawer_width <= self.min_rail_width:
            raise ValueError("min_drawer_width must exceed min_rail_width")
        if self.content is None:
            raise ValueError("NavigationScaffold content cannot be None")
        self._item_nodes: dict[str, list[LayoutNode]] = {}
        self._content_node: LayoutNode | None = None
        self._root: LayoutNode | None = None

    def _key(self, item: NavigationItem) -> str:
        return item.key or item.label

    def _select(self, item: NavigationItem):
        if item.disabled:
            return
        self.selected = self._key(item)
        self._sync_selection()
        if self.on_select is not None:
            self.on_select(item)

    def _sync_selection(self):
        t = self.theme
        for item in self.items:
            key = self._key(item)
            selected = self.selected in {key, item.label}
            for node in self._item_nodes.get(key, ()):
                node.background = t.primary_soft if selected else None
                node.text_color = (
                    t.disabled_text if item.disabled else
                    t.primary if selected else t.foreground
                )
                node.accessibility_selected = selected

    def _navigation_item_node(self, item: NavigationItem, mode: str) -> LayoutNode:
        t = self.theme
        selected = self.selected in {self._key(item), item.label}
        if mode == "rail":
            label = item.icon or item.label[:1]
            padding = Insets.symmetric(vertical=13, horizontal=10)
        elif mode == "bottom":
            label = ((item.icon + "\\n") if item.icon else "") + item.label
            padding = Insets.symmetric(vertical=8, horizontal=4)
        else:
            prefix = (item.icon + "  ") if item.icon else ""
            suffix = ("   " + item.badge) if item.badge else ""
            label = prefix + item.label + suffix
            padding = Insets.symmetric(vertical=11, horizontal=12)
        node = LayoutNode(
            "text", text=label, font_size=13,
            text_color=t.disabled_text if item.disabled else (t.primary if selected else t.foreground),
            padding=padding, background=t.primary_soft if selected else None,
            radius=t.radius_small,
            weight=1 if mode == "bottom" else 0,
            accessibility_role="navigationitem",
            accessibility_label=item.label,
            accessibility_disabled=item.disabled,
            accessibility_selected=selected,
            on_click=None if item.disabled else (lambda _event=None, value=item: self._select(value)),
        )
        self._item_nodes.setdefault(self._key(item), []).append(node)
        return node

    def build(self) -> LayoutNode:
        t = self.theme
        self._item_nodes = {}
        content_node = _node(self.content)
        self._content_node = LayoutNode.box(
            content_node, weight=1, padding=Insets.all(16),
            accessibility_role="main", accessibility_label="Main content",
        )

        bottom_items = [self._navigation_item_node(item, "bottom") for item in self.items]
        bottom_bar = LayoutNode.row(
            *bottom_items, spacing=2, height=self.bottom_height,
            padding=Insets.symmetric(horizontal=8, vertical=4),
            background=t.surface, border_color=t.border, border_width=1,
            cross_align=Alignment.CENTER,
            accessibility_role="navigation", accessibility_label="Bottom navigation",
        )
        compact = LayoutNode.column(
            self._content_node, bottom_bar, cross_align=Alignment.STRETCH,
            accessibility_role="group",
        )

        rail_items = [self._navigation_item_node(item, "rail") for item in self.items]
        rail = LayoutNode.column(
            *rail_items, spacing=6, width=self.rail_width,
            padding=Insets.symmetric(horizontal=6, vertical=12),
            background=t.surface, border_color=t.border, border_width=1,
            accessibility_role="navigation", accessibility_label="Navigation rail",
        )
        medium = LayoutNode.row(
            rail, self._content_node, cross_align=Alignment.STRETCH,
            accessibility_role="group",
        )

        drawer_items = [self._navigation_item_node(item, "drawer") for item in self.items]
        drawer = LayoutNode.column(
            *drawer_items, spacing=6, width=self.drawer_width,
            padding=Insets.all(10), background=t.surface,
            border_color=t.border, border_width=1,
            accessibility_role="navigation", accessibility_label="Main navigation",
        )
        expanded = LayoutNode.row(
            drawer, self._content_node, cross_align=Alignment.STRETCH,
            accessibility_role="group",
        )
        self._root = AdaptiveLayout(
            variants=(
                AdaptiveVariant(0, 0, compact),
                AdaptiveVariant(self.min_rail_width, 0, medium),
                AdaptiveVariant(self.min_drawer_width, self.min_drawer_height, expanded),
            )
        ).build()
        return self._root


@dataclass
class Calendar:
    """Month calendar with date constraints and native day selection."""
    value: date | None = None
    month: date | None = None
    min_date: date | None = None
    max_date: date | None = None
    on_change: Callable[[date], None] | None = None
    first_weekday: int = 0
    width: float = 280
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.first_weekday not in range(7):
            raise ValueError("first_weekday must be between 0 (Monday) and 6 (Sunday)")
        if self.width <= 0:
            raise ValueError("Calendar width must be positive")
        if self.min_date and self.max_date and self.min_date > self.max_date:
            raise ValueError("min_date cannot be after max_date")
        for name, value in (("value", self.value), ("month", self.month),
                            ("min_date", self.min_date), ("max_date", self.max_date)):
            if value is not None and not isinstance(value, date):
                raise TypeError(f"Calendar {name} must be a datetime.date")
        self.month = self._month_start(self.month or self.value or date.today())
        self._root: LayoutNode | None = None

    @staticmethod
    def _month_start(value: date) -> date:
        return date(value.year, value.month, 1)

    def _shift_month(self, delta):
        month_index = self.month.month - 1 + delta
        year = self.month.year + month_index // 12
        month = month_index % 12 + 1
        self.month = date(year, month, 1)
        self._sync()

    def _select(self, value):
        if self.min_date and value < self.min_date or self.max_date and value > self.max_date:
            return
        self.value = value
        self._sync()
        if self.on_change is not None:
            self.on_change(value)

    def _build_nodes(self):
        from .core import Button
        t = self.theme
        month_label = date(self.month.year, self.month.month, 1).strftime("%B %Y")
        previous = Button("‹", on_click=lambda _event=None: self._shift_month(-1), variant="ghost", size="small", theme=t).build()
        next_button = Button("›", on_click=lambda _event=None: self._shift_month(1), variant="ghost", size="small", theme=t).build()
        heading = _text_node(month_label, color=t.foreground, size=15, weight="semibold",
                             align="center", role="heading", label=month_label)
        header = LayoutNode.row(previous, heading, next_button, spacing=6,
                                cross_align=Alignment.CENTER)
        names = list(_calendar.day_abbr)
        names = names[self.first_weekday:] + names[:self.first_weekday]
        weekdays = Grid(
            children=[_text_node(name, color=t.muted, size=11, weight="semibold", align="center")
                      for name in names],
            columns=7, column_gap=2, row_gap=2, width=self.width,
        ).build()
        cal = _calendar.Calendar(firstweekday=self.first_weekday)
        weeks = cal.monthdatescalendar(self.month.year, self.month.month)
        while len(weeks) < 6:
            last_day = weeks[-1][-1]
            weeks.append([last_day.fromordinal(last_day.toordinal() + i) for i in range(1, 8)])
        day_nodes = []
        for week in weeks[:6]:
            for day in week:
                in_month = day.month == self.month.month
                disabled = ((self.min_date is not None and day < self.min_date) or
                            (self.max_date is not None and day > self.max_date) or not in_month)
                selected = self.value == day
                text = str(day.day) if in_month else ""
                node = _text_node(
                    text, color=(t.on_primary if selected else t.disabled_text if disabled else t.foreground),
                    size=12, weight="semibold" if selected else "normal",
                    align="center", background=t.primary if selected else None,
                    radius=t.radius_small, role="button" if in_month else "text",
                    label=day.isoformat() if in_month else "",
                    disabled=disabled,
                    selected=selected,
                    on_click=None if disabled else (lambda _event=None, value=day: self._select(value)),
                )
                node.height = 30
                day_nodes.append(node)
        days = Grid(children=day_nodes, columns=7, column_gap=2, row_gap=2,
                    min_column_width=None, width=self.width).build()
        return [header, weekdays, days]

    def _sync(self):
        if self._root is not None:
            self._root.children = self._build_nodes()

    def build(self):
        self._root = LayoutNode.column(
            *self._build_nodes(), spacing=8, padding=Insets.all(10), width=self.width,
            background=self.theme.surface, radius=self.theme.radius_medium,
            border_color=self.theme.border, border_width=1,
            accessibility_role="group", accessibility_label="Calendar",
        )
        return self._root


@dataclass
class DatePicker:
    """Inline expandable date picker. The selected value is a ``datetime.date``."""
    value: date | str | None = None
    placeholder: str = "Select date"
    min_date: date | None = None
    max_date: date | None = None
    on_change: Callable[[date], None] | None = None
    width: float = 280
    expanded: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if isinstance(self.value, str):
            self.value = date.fromisoformat(self.value)
        if self.value is not None and not isinstance(self.value, date):
            raise TypeError("DatePicker value must be a date or ISO date string")
        for name, bound in (("min_date", self.min_date), ("max_date", self.max_date)):
            if bound is not None and not isinstance(bound, date):
                raise TypeError(f"DatePicker {name} must be a datetime.date")
        if self.min_date and self.max_date and self.min_date > self.max_date:
            raise ValueError("min_date cannot be after max_date")
        if self.value is not None and ((self.min_date and self.value < self.min_date) or
                                       (self.max_date and self.value > self.max_date)):
            raise ValueError("DatePicker value is outside the allowed date range")
        if self.width <= 0:
            raise ValueError("DatePicker width must be positive")
        self._root: LayoutNode | None = None

    def _picked(self, value):
        self.value = value
        self.expanded = False
        self._sync()
        if self.on_change is not None:
            self.on_change(value)

    def _toggle(self, _event=None):
        self.expanded = not self.expanded
        self._sync()

    def _sync(self):
        if self._root is None:
            return
        from .core import Button
        label = self.value.isoformat() if self.value else self.placeholder
        trigger = Button(label + ("  ▴" if self.expanded else "  ▾"),
                         on_click=self._toggle, variant="outline", theme=self.theme).build()
        trigger.width = self.width
        children = [trigger]
        if self.expanded:
            children.append(Calendar(
                value=self.value, min_date=self.min_date, max_date=self.max_date,
                on_change=self._picked, width=self.width, theme=self.theme,
            ).build())
        self._root.children = children

    def build(self):
        self._root = LayoutNode.column(spacing=6, width=self.width,
                                       accessibility_role="group",
                                       accessibility_label="Date picker")
        self._sync()
        return self._root


@dataclass
class FilePicker:
    """Button that launches an SDL-backed open/save/folder dialog service.

    The service can be ``SDL3Window`` or another object implementing the
    corresponding ``show_*_dialog`` method. SDL3 completion callbacks are
    delivered by ``SDL3Window.poll_events()`` on the window thread.
    """
    dialog_service: object
    mode: str = "open"
    label: str = "Choose file"
    filters: Sequence[tuple[str, str]] = ()
    default_location: str | None = None
    allow_many: bool = False
    disabled: bool = False
    on_change: Callable[[tuple[str, ...]], None] | None = None
    on_error: Callable[[], None] | None = None
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.mode not in {"open", "save", "folder"}:
            raise ValueError("FilePicker mode must be open, save or folder")
        if not self.label:
            raise ValueError("FilePicker label must not be empty")
        for item in self.filters:
            if (not isinstance(item, (tuple, list)) or len(item) != 2 or
                    not all(isinstance(value, str) and value for value in item)):
                raise ValueError("filters must be (display_name, extension_pattern) pairs")
        if self.mode == "folder" and self.filters:
            raise ValueError("Folder pickers do not accept file filters")
        self.value: tuple[str, ...] = ()
        self._button: LayoutNode | None = None

    def _completed(self, paths, _filter_index=-1):
        if paths is None:
            if self.on_error is not None:
                self.on_error()
            return
        paths = tuple(paths)
        if not paths:
            return
        self.value = paths
        if self._button is not None:
            self._button.text = ", ".join(paths)
            self._button.accessibility_value = self._button.text
        if self.on_change is not None:
            self.on_change(paths)

    def _open(self, _event=None):
        if self.disabled:
            return
        method_name = {
            "open": "show_open_file_dialog",
            "save": "show_save_file_dialog",
            "folder": "show_open_folder_dialog",
        }[self.mode]
        method = getattr(self.dialog_service, method_name, None)
        if not callable(method):
            raise TypeError(f"dialog_service must implement {method_name}()")
        kwargs = {"default_location": self.default_location}
        if self.mode != "folder":
            kwargs["filters"] = self.filters
        if self.mode == "open":
            kwargs["allow_many"] = self.allow_many
        elif self.mode == "folder":
            kwargs["allow_many"] = self.allow_many
        method(self._completed, **kwargs)

    def build(self):
        from .core import Button
        display = ", ".join(self.value) if self.value else self.label
        self._button = Button(
            display, on_click=self._open, variant="outline",
            disabled=self.disabled, theme=self.theme,
        ).build()
        self._button.accessibility_label = self.label
        self._button.accessibility_value = display if self.value else None
        return self._button


@dataclass(frozen=True)
class TreeItem:
    label: str
    children: Sequence["TreeItem"] = ()
    key: str | None = None
    disabled: bool = False

    def __post_init__(self):
        if not self.label:
            raise ValueError("TreeItem label must not be empty")
        if any(not isinstance(item, TreeItem) for item in self.children):
            raise TypeError("TreeItem children must be TreeItem instances")


@dataclass
class TreeView:
    """Expandable, selectable hierarchical tree with keyboard-ready semantics."""
    items: Sequence[TreeItem]
    selected: str | None = None
    expanded: Sequence[str] = ()
    on_select: Callable[[TreeItem], None] | None = None
    width: float | None = None
    indent: float = 18
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.indent < 0:
            raise ValueError("TreeView indent must be non-negative")
        if any(not isinstance(item, TreeItem) for item in self.items):
            raise TypeError("TreeView items must be TreeItem instances")
        keys = []
        def collect(items, path=""):
            for index, item in enumerate(items):
                item_path = f"{path}/{index}" if path else str(index)
                key = item.key or item_path
                if not isinstance(key, str) or not key:
                    raise ValueError("TreeItem key must be a non-empty string")
                keys.append(key)
                collect(item.children, item_path)
        collect(self.items)
        if len(keys) != len(set(keys)):
            raise ValueError("TreeItem keys must be unique")
        self._expanded = set(self.expanded)
        if not self._expanded.issubset(set(keys)):
            raise ValueError("expanded contains an unknown TreeItem key")
        if self.selected is not None and self.selected not in set(keys):
            raise ValueError("selected contains an unknown TreeItem key")
        self._root: LayoutNode | None = None

    @staticmethod
    def _item_key(item: TreeItem, path: str) -> str:
        return item.key or path

    def _activate(self, item, key):
        if item.disabled:
            return
        if item.children:
            if key in self._expanded:
                self._expanded.remove(key)
            else:
                self._expanded.add(key)
        self.selected = key
        self._sync()
        if self.on_select is not None:
            self.on_select(item)

    def _flatten(self, items, depth=0, path=""):
        nodes = []
        for index, item in enumerate(items):
            item_path = f"{path}/{index}" if path else str(index)
            key = self._item_key(item, item_path)
            has_children = bool(item.children)
            is_expanded = key in self._expanded
            marker = ("▾ " if is_expanded else "▸ ") if has_children else "  "
            selected = self.selected == key
            row = _text_node(
                marker + item.label,
                color=(self.theme.disabled_text if item.disabled else
                       self.theme.primary if selected else self.theme.foreground),
                size=13, padding=Insets(5, 8, 5, 8 + depth * self.indent),
                background=self.theme.primary_soft if selected else None,
                radius=self.theme.radius_small,
                role="treeitem", label=item.label, selected=selected,
                disabled=item.disabled,
                on_click=None if item.disabled else
                         (lambda _event=None, value=item, item_key=key: self._activate(value, item_key)),
            )
            row.accessibility_expanded = is_expanded if has_children else None
            nodes.append(row)
            if has_children and is_expanded:
                nodes.extend(self._flatten(item.children, depth + 1, item_path))
        return nodes

    def _sync(self):
        if self._root is not None:
            self._root.children = self._flatten(self.items)

    def build(self):
        self._root = LayoutNode.column(
            *self._flatten(self.items), spacing=2, width=self.width,
            padding=Insets.all(5), background=self.theme.surface,
            accessibility_role="tree", accessibility_label="Tree view",
        )
        return self._root


__all__ = [
    "AdaptiveLayout", "AdaptiveVariant", "Calendar", "Container", "DatePicker",
    "Grid", "GridItem", "Image", "Responsive", "ResponsiveVariant",
    "NavigationDrawer", "NavigationItem", "NavigationScaffold", "Positioned", "ScrollView", "Table",
    "TreeItem", "TreeView", "FilePicker",
]
