"""Core native widgets for Yuktara UI.

Widgets build the existing retained LayoutNode tree. They do not depend on
SDL3 or Skia directly, so they can be tested with fake renderers and hosted by
any compatible native platform backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..layout import Alignment, Insets, LayoutNode, MainAxisAlignment, Size
from ..theme import NativeTheme


def _node(value) -> LayoutNode:
    if isinstance(value, LayoutNode):
        return value
    build = getattr(value, "build", None)
    if callable(build):
        result = build()
        if isinstance(result, LayoutNode):
            return result
    raise TypeError(
        f"Expected a LayoutNode or Yuktara UI widget, got {type(value).__name__}"
    )


def _text_node(text: str, *, color: int, size: float = 14,
               weight: str = "normal", padding: Insets = Insets(),
               background=None, radius: float = 0, width=None, height=None,
               align: str = "start", role=None, label=None, value=None,
               disabled=False, checked=None, selected=None, hint=None,
               on_click=None) -> LayoutNode:
    return LayoutNode(
        "text", text=text, text_color=color, font_size=size, font_weight=weight,
        padding=padding, background=background, radius=radius,
        width=width, height=height, text_align=align,
        accessibility_role=role, accessibility_label=label or text,
        accessibility_value=value, accessibility_hint=hint,
        accessibility_disabled=disabled, accessibility_checked=checked,
        accessibility_selected=selected, on_click=on_click,
    )


@dataclass
class Label:
    text: str
    size: float = 14
    weight: str = "normal"
    color: int | None = None
    theme: NativeTheme = field(default_factory=NativeTheme)
    max_lines: int | None = None
    wrap: bool = True
    align: str = "start"

    def __post_init__(self):
        if not isinstance(self.text, str):
            raise TypeError("Label text must be a string")
        if self.size <= 0:
            raise ValueError("Label size must be positive")
        if self.align not in {"start", "center", "end"}:
            raise ValueError("align must be start, center or end")
        if self.max_lines is not None and self.max_lines < 1:
            raise ValueError("max_lines must be at least 1")

    def build(self) -> LayoutNode:
        node = _text_node(self.text, color=self.color or self.theme.foreground,
                          size=self.size, weight=self.weight, align=self.align,
                          role="text", label=self.text)
        node.text_wrap = self.wrap
        node.text_max_lines = self.max_lines
        return node


@dataclass
class Button:
    label: str
    on_click: Callable | None = None
    variant: str = "primary"
    size: str = "medium"
    disabled: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)
    accessibility_hint: str | None = None

    VARIANTS = frozenset({"primary", "secondary", "outline", "ghost", "danger", "success"})
    SIZES = frozenset({"small", "medium", "large"})

    def __post_init__(self):
        if self.variant not in self.VARIANTS:
            raise ValueError(f"Unsupported button variant: {self.variant}")
        if self.size not in self.SIZES:
            raise ValueError(f"Unsupported button size: {self.size}")
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("Button label must be a non-empty string")
        if self.on_click is not None and not callable(self.on_click):
            raise TypeError("on_click must be callable")

    def build(self) -> LayoutNode:
        t = self.theme
        palettes = {
            "primary": (t.primary, t.on_primary, None),
            "secondary": (t.surface_variant, t.foreground, t.border),
            "outline": (t.surface, t.primary, t.primary),
            "ghost": (None, t.primary, None),
            "danger": (t.danger, t.on_danger, None),
            "success": (t.success, t.on_success, None),
        }
        background, foreground, border = palettes[self.variant]
        if self.disabled:
            background, foreground, border = t.disabled_surface, t.disabled_text, None
        pads = {
            "small": Insets.symmetric(vertical=6, horizontal=10),
            "medium": Insets.symmetric(vertical=9, horizontal=14),
            "large": Insets.symmetric(vertical=12, horizontal=18),
        }
        sizes = {"small": 13, "medium": 14, "large": 16}
        return LayoutNode(
            "text", text=self.label, text_color=foreground, font_size=sizes[self.size],
            font_weight="semibold", padding=pads[self.size],
            background=background, radius=t.radius_medium,
            border_color=border, border_width=1 if border is not None else 0,
            accessibility_role="button", accessibility_label=self.label,
            accessibility_disabled=self.disabled, accessibility_hint=self.accessibility_hint,
            on_click=None if self.disabled else self.on_click,
        )


@dataclass
class Card:
    children: Sequence[object] = ()
    padding: float | Insets = 16
    spacing: float = 10
    background: int | None = None
    radius: float | None = None
    bordered: bool = True
    theme: NativeTheme = field(default_factory=NativeTheme)

    def build(self) -> LayoutNode:
        insets = self.padding if isinstance(self.padding, Insets) else Insets.all(self.padding)
        if isinstance(self.padding, (int, float)) and self.padding < 0:
            raise ValueError("Card padding must be non-negative")
        children = [_node(child) for child in self.children]
        return LayoutNode.column(
            *children, spacing=self.spacing, padding=insets,
            background=self.background if self.background is not None else self.theme.surface,
            radius=self.radius if self.radius is not None else self.theme.radius_large,
            border_color=self.theme.border if self.bordered else None,
            border_width=1 if self.bordered else 0,
            cross_align=Alignment.STRETCH,
            accessibility_role="group",
        )


@dataclass
class Badge:
    text: str
    variant: str = "neutral"
    theme: NativeTheme = field(default_factory=NativeTheme)

    VARIANTS = frozenset({"neutral", "primary", "success", "warning", "danger", "info"})

    def build(self) -> LayoutNode:
        if self.variant not in self.VARIANTS:
            raise ValueError(f"Unsupported badge variant: {self.variant}")
        t = self.theme
        colors = {
            "neutral": (t.surface_variant, t.foreground),
            "primary": (t.primary_soft, t.primary),
            "success": (t.success_soft, t.success),
            "warning": (t.warning_soft, t.warning_text),
            "danger": (t.danger_soft, t.danger),
            "info": (t.info_soft, t.info),
        }
        bg, fg = colors[self.variant]
        return _text_node(self.text, color=fg, size=12, weight="semibold",
                          padding=Insets.symmetric(vertical=4, horizontal=8),
                          background=bg, radius=t.radius_pill,
                          role="status", label=self.text)


@dataclass
class Divider:
    thickness: float = 1
    color: int | None = None
    vertical: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)

    def build(self) -> LayoutNode:
        if self.thickness <= 0:
            raise ValueError("Divider thickness must be positive")
        return LayoutNode.box(
            width=self.thickness if self.vertical else None,
            height=None if self.vertical else self.thickness,
            intrinsic_size=Size(self.thickness, self.thickness),
            background=self.color if self.color is not None else self.theme.border,
            accessibility_role="separator",
        )


@dataclass
class ProgressBar:
    value: float
    height: float = 8
    color: int | None = None
    track_color: int | None = None
    theme: NativeTheme = field(default_factory=NativeTheme)
    label: str | None = None

    def __post_init__(self):
        if not 0 <= self.value <= 100:
            raise ValueError("Progress value must be between 0 and 100")
        if self.height <= 0:
            raise ValueError("Progress height must be positive")

    def build(self) -> LayoutNode:
        t = self.theme
        filled = LayoutNode.box(
            height=self.height, weight=self.value,
            intrinsic_size=Size(0, self.height),
            background=self.color if self.color is not None else t.primary,
            radius=self.height / 2,
        )
        rest = LayoutNode.box(
            height=self.height, weight=100 - self.value,
            intrinsic_size=Size(0, self.height),
            background=self.track_color if self.track_color is not None else t.border,
            radius=self.height / 2,
        )
        row = LayoutNode.row(filled, rest, height=self.height, spacing=0,
                             accessibility_role="progressbar",
                             accessibility_label=self.label or "Progress",
                             accessibility_value=f"{self.value:g}%")
        return row


@dataclass
class Checkbox:
    label: str
    checked: bool = False
    on_change: Callable[[bool], None] | None = None
    disabled: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)

    def build(self) -> LayoutNode:
        glyph = "☑" if self.checked else "☐"
        node = _text_node(
            f"{glyph}  {self.label}",
            color=self.theme.disabled_text if self.disabled else self.theme.foreground,
            size=14, role="checkbox", label=self.label,
            checked=self.checked, disabled=self.disabled,
            hint="Toggle checkbox", on_click=None if self.disabled else self._toggle,
        )
        self._built_node = node
        return node

    def _toggle(self, _event=None):
        if self.disabled:
            return
        self.checked = not self.checked
        node = getattr(self, "_built_node", None)
        if node is not None:
            node.text = f"{'☑' if self.checked else '☐'}  {self.label}"
            node.accessibility_checked = self.checked
        if self.on_change is not None:
            self.on_change(self.checked)


@dataclass
class Switch:
    label: str
    checked: bool = False
    on_change: Callable[[bool], None] | None = None
    disabled: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)

    def _toggle(self, _event=None):
        if self.disabled:
            return
        self.checked = not self.checked
        if self.on_change is not None:
            self.on_change(self.checked)

    def build(self) -> LayoutNode:
        t = self.theme
        track_color = t.disabled_surface if self.disabled else (t.primary if self.checked else t.border)
        knob = LayoutNode.box(
            width=16, height=16, background=0xFFFFFFFF, radius=8,
            on_click=None if self.disabled else self._toggle,
        )
        track = LayoutNode.box(
            knob, width=38, height=22, padding=Insets.all(3),
            background=track_color, radius=11,
            align=Alignment.END if self.checked else Alignment.START,
            on_click=None if self.disabled else self._toggle,
            accessibility_role="switch", accessibility_label=self.label,
            accessibility_checked=self.checked,
            accessibility_disabled=self.disabled,
        )
        caption = _text_node(
            self.label, color=t.disabled_text if self.disabled else t.foreground,
            size=14, role="text", label=self.label,
            on_click=None if self.disabled else self._toggle,
        )
        self._track_node = track
        return LayoutNode.row(track, caption, spacing=8,
                              cross_align=Alignment.CENTER,
                              accessibility_role="group", accessibility_label=self.label)

    def _toggle(self, _event=None):
        if self.disabled:
            return
        self.checked = not self.checked
        track = getattr(self, "_track_node", None)
        if track is not None:
            track.background = self.theme.primary if self.checked else self.theme.border
            track.align = Alignment.END if self.checked else Alignment.START
            track.accessibility_checked = self.checked
        if self.on_change is not None:
            self.on_change(self.checked)


@dataclass
class RadioGroup:
    options: Sequence[str]
    value: str | None = None
    on_change: Callable[[str], None] | None = None
    direction: str = "column"
    disabled: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.direction not in {"row", "column"}:
            raise ValueError("direction must be row or column")
        if not self.options:
            raise ValueError("RadioGroup requires at least one option")
        if len(set(self.options)) != len(self.options):
            raise ValueError("RadioGroup options must be unique")
        if self.value is not None and self.value not in self.options:
            raise ValueError("RadioGroup value must match an option")

    def _select(self, option: str):
        if self.disabled or option == self.value:
            return
        self.value = option
        for item, node in getattr(self, "_built_nodes", {}).items():
            node.text = f"{'◉' if item == option else '○'}  {item}"
            node.accessibility_selected = item == option
        if self.on_change is not None:
            self.on_change(option)

    def build(self) -> LayoutNode:
        children = []
        self._built_nodes = {}
        for option in self.options:
            selected = option == self.value
            glyph = "◉" if selected else "○"
            node = _text_node(
                f"{glyph}  {option}",
                color=self.theme.disabled_text if self.disabled else self.theme.foreground,
                size=14, role="radio", label=option, selected=selected,
                disabled=self.disabled,
                on_click=None if self.disabled else (lambda event, value=option: self._select(value)),
            )
            self._built_nodes[option] = node
            children.append(node)
        factory = LayoutNode.row if self.direction == "row" else LayoutNode.column
        return factory(*children, spacing=12, accessibility_role="radiogroup")


@dataclass
class Spacer:
    """Flexible empty space for row or column compositions."""
    flex: float = 1
    width: float | None = None
    height: float | None = None

    def build(self) -> LayoutNode:
        if self.flex < 0:
            raise ValueError("Spacer flex must be non-negative")
        return LayoutNode.box(
            width=self.width, height=self.height, weight=self.flex,
            intrinsic_size=Size(self.width or 0, self.height or 0),
        )


def row(*children, spacing: float = 8, **kwargs) -> LayoutNode:
    """Compose widgets or nodes horizontally."""
    return LayoutNode.row(*[_node(child) for child in children], spacing=spacing, **kwargs)


def column(*children, spacing: float = 8, **kwargs) -> LayoutNode:
    """Compose widgets or nodes vertically."""
    return LayoutNode.column(*[_node(child) for child in children], spacing=spacing, **kwargs)


def stack(*children, **kwargs) -> LayoutNode:
    """Overlay widgets or nodes in a native stack."""
    return LayoutNode.stack(*[_node(child) for child in children], **kwargs)


__all__ = [
    "Badge", "Button", "Card", "Checkbox", "Divider", "Label", "ProgressBar",
    "RadioGroup", "Spacer", "Switch", "column", "row", "stack",
]
