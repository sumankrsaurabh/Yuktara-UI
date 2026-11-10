"""Native overlay widgets: dialogs, popovers, tooltips, menus and toasts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..layout import Alignment, Insets, LayoutNode, MainAxisAlignment, Size
from ..theme import NativeTheme


def _as_node(value, color=0xFF202735) -> LayoutNode:
    if isinstance(value, LayoutNode):
        return value
    if isinstance(value, str):
        return LayoutNode("text", text=value, font_size=14, text_color=color,
                          intrinsic_size=Size(max(1, len(value)) * 7.5, 20))
    build = getattr(value, "build", None)
    if callable(build):
        node = build()
        if isinstance(node, LayoutNode):
            return node
    raise TypeError(f"Expected a LayoutNode, string or Yuktara UI widget, got {type(value).__name__}")


def _content_nodes(content, color=0xFF202735) -> list[LayoutNode]:
    if content is None:
        return []
    if isinstance(content, (str, LayoutNode)) or callable(getattr(content, "build", None)):
        return [_as_node(content, color)]
    if isinstance(content, Sequence):
        return [_as_node(item, color) for item in content]
    return [_as_node(content, color)]


@dataclass
class Dialog:
    """A dialog surface. Display it with ``runtime.overlays.show_dialog``."""
    title: str
    content: object = ()
    actions: Sequence[object] = ()
    width: float = 440
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if not self.title:
            raise ValueError("Dialog title must not be empty")
        if self.width <= 0:
            raise ValueError("Dialog width must be positive")

    def build(self) -> LayoutNode:
        t = self.theme
        header = LayoutNode("text", text=self.title, font_size=18,
                            font_weight="semibold", text_color=t.foreground,
                            intrinsic_size=Size(max(1, len(self.title)) * 10, 26),
                            accessibility_role="heading", accessibility_label=self.title)
        body = _content_nodes(self.content, t.foreground)
        action_nodes = _content_nodes(self.actions, t.foreground)
        children = [header, *body]
        if action_nodes:
            children.append(LayoutNode.row(
                *action_nodes, spacing=8, main_align=MainAxisAlignment.END,
                cross_align=Alignment.CENTER,
            ))
        panel = LayoutNode.column(
            *children, spacing=16, padding=Insets.all(22), width=self.width,
            background=t.surface, radius=t.radius_large,
            border_color=t.border, border_width=1,
            accessibility_role="dialog", accessibility_label=self.title,
        )
        return panel


@dataclass
class Popover:
    """A compact anchored surface. Display with ``runtime.overlays.show_popover``."""
    content: object
    width: float = 260
    padding: float = 14
    spacing: float = 8
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.width <= 0 or self.padding < 0 or self.spacing < 0:
            raise ValueError("Popover width must be positive; padding and spacing non-negative")

    def build(self) -> LayoutNode:
        t = self.theme
        return LayoutNode.column(
            *_content_nodes(self.content, t.foreground), spacing=self.spacing,
            padding=Insets.all(self.padding), width=self.width,
            background=t.surface, radius=t.radius_medium,
            border_color=t.border, border_width=1,
            accessibility_role="group", accessibility_label="Popover",
        )


@dataclass
class Tooltip:
    text: str
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if not self.text:
            raise ValueError("Tooltip text must not be empty")

    def build(self) -> LayoutNode:
        t = self.theme
        return LayoutNode("text", text=self.text, font_size=12,
                          text_color=0xFFFFFFFF, padding=Insets.symmetric(7, 10),
                          background=0xFF252B36, radius=t.radius_small,
                          accessibility_role="tooltip", accessibility_label=self.text)


@dataclass
class MenuItem:
    label: str
    on_click: Callable | None = None
    shortcut: str | None = None
    disabled: bool = False

    def __post_init__(self):
        if not self.label:
            raise ValueError("Menu item label must not be empty")
        if self.on_click is not None and not callable(self.on_click):
            raise TypeError("Menu item on_click must be callable")


@dataclass
class ContextMenu:
    items: Sequence[MenuItem]
    width: float = 220
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.width <= 0:
            raise ValueError("ContextMenu width must be positive")
        if not self.items:
            raise ValueError("ContextMenu requires at least one item")
        if any(not isinstance(item, MenuItem) for item in self.items):
            raise TypeError("ContextMenu items must be MenuItem instances")

    def build(self) -> LayoutNode:
        t = self.theme
        nodes = []
        for item in self.items:
            label = item.label
            if item.shortcut:
                label = f"{label}    {item.shortcut}"
            nodes.append(LayoutNode(
                "text", text=label, font_size=13,
                text_color=t.disabled_text if item.disabled else t.foreground,
                padding=Insets.symmetric(vertical=9, horizontal=11),
                radius=t.radius_small,
                accessibility_role="menuitem", accessibility_label=item.label,
                accessibility_disabled=item.disabled,
                on_click=None if item.disabled else item.on_click,
            ))
        return LayoutNode.column(
            *nodes, spacing=2, padding=Insets.all(6), width=self.width,
            background=t.surface, radius=t.radius_medium,
            border_color=t.border, border_width=1,
            accessibility_role="menu", accessibility_label="Context menu",
        )


@dataclass
class Alert:
    """Inline semantic feedback panel for important contextual messages."""
    message: str
    title: str | None = None
    variant: str = "info"
    icon: str | None = None
    theme: NativeTheme = field(default_factory=NativeTheme)

    VARIANTS = frozenset({"info", "success", "warning", "danger"})

    def __post_init__(self):
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Alert message must be a non-empty string")
        if self.title is not None and not isinstance(self.title, str):
            raise TypeError("Alert title must be a string or None")
        if self.variant not in self.VARIANTS:
            raise ValueError(f"Unsupported alert variant: {self.variant}")
        if self.icon is not None and not isinstance(self.icon, str):
            raise TypeError("Alert icon must be a string or None")

    def build(self) -> LayoutNode:
        t = self.theme
        palette = {
            "info": (t.info_soft, t.info, "ⓘ"),
            "success": (t.success_soft, t.success, "✓"),
            "warning": (t.warning_soft, t.warning_text, "!"),
            "danger": (t.danger_soft, t.danger, "×"),
        }
        background, accent, default_icon = palette[self.variant]
        icon = LayoutNode(
            "text",
            text=self.icon or default_icon,
            text_color=accent,
            font_size=t.type_title_medium,
            font_weight="semibold",
            width=28,
            min_width=28,
            text_align="center",
            accessibility_role="image",
            accessibility_label=f"{self.variant.capitalize()}",
        )
        message_nodes = []
        if self.title:
            message_nodes.append(LayoutNode(
                "text", text=self.title, text_color=t.on_surface,
                font_size=t.type_title_medium, font_weight="semibold",
                accessibility_role="heading", accessibility_label=self.title,
            ))
        message_nodes.append(LayoutNode(
            "text", text=self.message, text_color=t.on_surface,
            font_size=t.type_body_medium,
            accessibility_role="text", accessibility_label=self.message,
        ))
        content = LayoutNode.column(
            *message_nodes, spacing=t.space_1,
            cross_align=Alignment.START,
        )
        content.weight = 1.0
        return LayoutNode.row(
            icon,
            content,
            spacing=t.space_3,
            padding=Insets.all(t.space_4),
            background=background,
            radius=t.radius_large,
            border_color=accent,
            border_width=1,
            cross_align=Alignment.CENTER,
            accessibility_role="alert" if self.variant == "danger" else "status",
            accessibility_label=self.title or self.message,
            accessibility_value=self.message if self.title else None,
            accessibility_live="assertive" if self.variant == "danger" else "polite",
        )


@dataclass
class Toast:
    message: str
    variant: str = "info"
    duration_ms: int | None = 3000
    theme: NativeTheme = field(default_factory=NativeTheme)

    VARIANTS = frozenset({"info", "success", "warning", "danger"})

    def __post_init__(self):
        if not self.message:
            raise ValueError("Toast message must not be empty")
        if self.variant not in self.VARIANTS:
            raise ValueError(f"Unsupported toast variant: {self.variant}")
        if self.duration_ms is not None and self.duration_ms <= 0:
            raise ValueError("Toast duration_ms must be positive or None")

    def build(self) -> LayoutNode:
        t = self.theme
        accents = {
            "info": t.info, "success": t.success,
            "warning": t.warning, "danger": t.danger,
        }
        return LayoutNode("text", text=self.message, font_size=13,
                          font_weight="medium", text_color=t.foreground,
                          padding=Insets.symmetric(vertical=12, horizontal=16),
                          background=t.surface, radius=t.radius_medium,
                          border_color=accents[self.variant], border_width=1.5,
                          accessibility_role="status", accessibility_label=self.message)
