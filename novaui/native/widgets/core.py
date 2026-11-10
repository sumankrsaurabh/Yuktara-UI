"""Core native widgets for Yuktara UI.

Widgets build the existing retained LayoutNode tree. They do not depend on
SDL3 or Skia directly, so they can be tested with fake renderers and hosted by
any compatible native platform backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Callable, Sequence

from ..layout import Alignment, Insets, LayoutNode, MainAxisAlignment, Size
from ..theme import NativeTheme
from ..text.measure import (ParagraphStyle, TextMeasurer, TextStyleSpan, grapheme_spans,
                            next_grapheme_boundary, normalize_grapheme_boundary,
                            previous_grapheme_boundary)


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

    def _update_text_input_area(self, _node=None):
        """Keep SDL's native IME candidate window aligned with the laid-out caret."""
        node = self._built_node
        set_input_area = getattr(self.clipboard, "set_text_input_area", None)
        if not self._focused or node is None or not callable(set_input_area):
            return
        layout = node.text_layout
        if layout is None or not callable(getattr(layout, "caret_position", None)):
            return
        visual_cursor = min(len(node.text or ""), self._visual_cursor())
        caret_x, caret_y, line_index = layout.caret_position(visual_cursor)
        line_height = layout.lines[line_index].height or layout.line_height
        area = node.content_bounds
        if area.width <= 0 or area.height <= 0:
            return
        geometry = (
            round(area.x),
            round(area.y + caret_y - node.text_scroll_y),
            max(1, round(area.width)),
            max(1, round(line_height)),
            min(max(0, round(caret_x - node.text_scroll_x)), max(1, round(area.width))),
        )
        if geometry == getattr(self, "_last_text_input_area", None):
            return
        set_input_area(*geometry)
        self._last_text_input_area = geometry

    def build(self) -> LayoutNode:
        node = _text_node(self.text, color=self.color or self.theme.foreground,
                          size=self.size, weight=self.weight, align=self.align,
                          role="text", label=self.text)
        node.text_wrap = self.wrap
        node.text_max_lines = self.max_lines
        return node


@dataclass
class RichText:
    """A native text node with source-indexed inline style spans."""
    text: str
    spans: Sequence[TextStyleSpan] = ()
    size: float = 14
    weight: str = "normal"
    color: int | None = None
    theme: NativeTheme = field(default_factory=NativeTheme)
    wrap: bool = True
    align: str = "start"
    max_lines: int | None = None
    line_height: float | None = None
    paragraph_styles: Sequence[ParagraphStyle] = ()

    def __post_init__(self):
        if not isinstance(self.text, str):
            raise TypeError("RichText text must be a string")
        if not isfinite(float(self.size)) or self.size <= 0:
            raise ValueError("RichText size must be finite and positive")
        if self.align not in {"start", "center", "end"}:
            raise ValueError("align must be start, center or end")
        if self.max_lines is not None and self.max_lines < 1:
            raise ValueError("max_lines must be at least 1")
        if self.line_height is not None and (not isfinite(float(self.line_height)) or self.line_height <= 0):
            raise ValueError("line_height must be finite and positive")
        TextMeasurer._normalize_style_spans(self.text, self.spans)
        TextMeasurer._normalize_paragraph_styles(self.text, self.paragraph_styles)

    def build(self) -> LayoutNode:
        node = _text_node(
            self.text,
            color=self.color if self.color is not None else self.theme.foreground,
            size=self.size, weight=self.weight, align=self.align,
            role="text", label=self.text,
        )
        node.text_style_spans = tuple(self.spans)
        node.text_paragraph_styles = tuple(self.paragraph_styles)
        node.text_wrap = self.wrap
        node.text_max_lines = self.max_lines
        node.text_line_height = self.line_height
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


# SDL keycodes used by the controls below. SDL3 uses ASCII keycodes for
# printable keys and 1<<30 | scancode for non-printable navigation keys.
_KEY_BACKSPACE = 8
_KEY_TAB = 9
_KEY_RETURN = 13
_KEY_ESCAPE = 27
_KEY_DELETE = 127
_KEY_LEFT = (1 << 30) | 80
_KEY_RIGHT = (1 << 30) | 79
_KEY_HOME = (1 << 30) | 74
_KEY_END = (1 << 30) | 77
_KEY_UP = (1 << 30) | 82
_KEY_DOWN = (1 << 30) | 81
_KEY_PAGE_UP = (1 << 30) | 75
_KEY_PAGE_DOWN = (1 << 30) | 78
_MOD_SHIFT = 0x0003
_MOD_CTRL = 0x00C0


@dataclass
class TextField:
    """Single-line native text input with keyboard focus and editing.

    Text is delivered by SDL3's committed text-input events, so keyboard
    layouts and OS input methods remain the platform's responsibility.
    Clipboard and rich IME pre-edit composition are intentionally separate
    platform services and are not simulated by this control.
    """
    value: str = ""
    placeholder: str = ""
    width: float = 240
    height: float = 40
    on_change: Callable[[str], None] | None = None
    on_submit: Callable[[str], None] | None = None
    max_length: int | None = None
    disabled: bool = False
    read_only: bool = False
    font_size: float = 14
    font_family: str = "Inter"
    theme: NativeTheme = field(default_factory=NativeTheme)
    multiline: bool = False
    clipboard: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.value, str) or not isinstance(self.placeholder, str):
            raise TypeError("TextField value and placeholder must be strings")
        if self.width <= 0 or self.height <= 0 or self.font_size <= 0 or not self.font_family:
            raise ValueError("TextField dimensions/font_size must be positive and font_family non-empty")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("max_length must be non-negative")
        self.cursor = len(self.value)
        self.anchor = self.cursor
        self._focused = False
        self._selecting = False
        self._composition_text = ""
        self._composition_range = (self.cursor, self.cursor)
        self._composition_original_selection = (self.anchor, self.cursor)
        self._composition_cursor = 0
        self._composition_selection_length = 0
        self._built_node: LayoutNode | None = None

    @property
    def selection(self) -> tuple[int, int]:
        return (min(self.anchor, self.cursor), max(self.anchor, self.cursor))

    def _display_text(self) -> str:
        if self._composition_text:
            start, end = self._composition_range
            return self.value[:start] + self._composition_text + self.value[end:]
        if not self.value and not self._focused:
            return self.placeholder
        return self.value

    def _visual_cursor(self) -> int:
        if self._composition_text:
            return self._composition_range[0] + self._composition_cursor
        return self.cursor

    def _clear_composition(self, *, restore_selection: bool = True) -> bool:
        if not self._composition_text:
            return False
        if restore_selection:
            self.anchor, self.cursor = self._composition_original_selection
        self._composition_text = ""
        self._composition_range = (self.cursor, self.cursor)
        self._composition_original_selection = (self.anchor, self.cursor)
        self._composition_cursor = 0
        self._composition_selection_length = 0
        if self._built_node is not None:
            self._built_node.text_composition = None
        return True

    def _sync_node(self):
        node = self._built_node
        if node is None:
            return
        node.text = self._display_text()
        node.text_color = (self.theme.disabled_text if self.disabled else
                           self.theme.muted if not self.value else self.theme.foreground)
        node.accessibility_value = self.value
        node.accessibility_focused = self._focused

        visual_cursor = min(len(node.text or ""), self._visual_cursor())
        if self._composition_text:
            composition_start = self._composition_range[0]
            node.text_composition = (
                composition_start, composition_start + len(self._composition_text)
            )
            if self._composition_selection_length:
                selection_start = composition_start + self._composition_cursor
                node.text_selection = (
                    selection_start, selection_start + self._composition_selection_length
                )
            else:
                node.text_selection = None
        else:
            node.text_composition = None
            node.text_selection = (
                self.selection if self._focused and self.selection[0] != self.selection[1]
                else None
            )
        node.text_cursor = visual_cursor if self._focused else None

        layout = node.text_layout
        caret_x = visual_cursor * self.font_size * 0.55
        caret_y = 0.0
        line_height = max(self.font_size * 1.35, 1.0)
        if layout is not None and callable(getattr(layout, "caret_position", None)):
            caret_x, caret_y, line_index = layout.caret_position(visual_cursor)
            if getattr(layout, "lines", None):
                line_height = layout.lines[line_index].height or layout.line_height
        if self._focused:
            visible_width = node.content_bounds.width
            visible_height = node.content_bounds.height
            if caret_x - node.text_scroll_x > visible_width - 3:
                node.text_scroll_x = max(0.0, caret_x - visible_width + 3)
            elif caret_x < node.text_scroll_x:
                node.text_scroll_x = caret_x
            if self.multiline:
                if caret_y + line_height - node.text_scroll_y > visible_height:
                    node.text_scroll_y = max(0.0, caret_y + line_height - visible_height)
                elif caret_y < node.text_scroll_y:
                    node.text_scroll_y = caret_y

    def build(self) -> LayoutNode:
        node = LayoutNode(
            "text", text=self._display_text(), width=self.width, height=self.height,
            padding=Insets.symmetric(horizontal=11, vertical=8),
            background=self.theme.disabled_surface if self.disabled else self.theme.surface,
            radius=self.theme.radius_medium,
            border_color=self.theme.focus if self._focused else self.theme.border,
            border_width=1,
            text_color=(self.theme.disabled_text if self.disabled else
                        self.theme.muted if not self.value else self.theme.foreground),
            font_size=self.font_size,
            font_family=self.font_family,
            text_wrap=self.multiline,
            text_clip=True,
            accessibility_role="textbox",
            accessibility_label=self.placeholder or ("Text area" if self.multiline else "Text field"),
            accessibility_value=self.value,
            accessibility_disabled=self.disabled,
            on_pointer_down=self._pointer_down,
            on_pointer_move=self._pointer_move,
            on_pointer_up=self._pointer_up,
            on_key_down=self._key_down,
            on_text_input=self._text_input,
            on_text_editing=self._text_editing,
            on_text_layout=self._update_text_input_area,
            on_focus=self._focus,
            on_blur=self._blur,
        )
        if self.disabled:
            node.on_pointer_down = None
            node.on_pointer_move = None
            node.on_pointer_up = None
            node.on_key_down = None
            node.on_text_input = None
            node.on_text_editing = None
        self._built_node = node
        return node

    def _focus(self, _event=None):
        self._focused = True
        self._last_text_input_area = None
        start_text_input = getattr(self.clipboard, "start_text_input", None)
        if callable(start_text_input):
            start_text_input()
        self._sync_node()
        if self._built_node is not None:
            self._built_node.border_color = self.theme.focus

    def _blur(self, _event=None):
        self._clear_composition(restore_selection=True)
        self._focused = False
        self._last_text_input_area = None
        stop_text_input = getattr(self.clipboard, "stop_text_input", None)
        if callable(stop_text_input):
            stop_text_input()
        clear_composition = getattr(self.clipboard, "clear_composition", None)
        if callable(clear_composition):
            clear_composition()
        self.anchor = self.cursor
        self._sync_node()
        if self._built_node is not None:
            self._built_node.border_color = self.theme.border

    def _offset_from_pointer(self, event):
        pointer = getattr(event, "pointer", None)
        node = self._built_node
        if pointer is None or node is None:
            return self.cursor
        local_x = pointer.x - node.content_bounds.x + node.text_scroll_x
        local_y = pointer.y - node.content_bounds.y + node.text_scroll_y
        layout = node.text_layout
        if layout is not None and callable(getattr(layout, "offset_at", None)):
            return normalize_grapheme_boundary(
                self.value, layout.offset_at(local_x, local_y), forward=False
            )
        char_width = max(1.0, self.font_size * 0.55)
        line_height = max(self.font_size * 1.35, 1.0)
        spans = grapheme_spans(self.value)
        if self.multiline:
            line_index = max(0, int(local_y // line_height))
            lines = self.value.split("\n")
            line_index = min(line_index, max(0, len(lines) - 1))
            line_start = sum(len(part) + 1 for part in lines[:line_index])
            line_text = lines[line_index] if lines else ""
            clusters = [(a, b) for a, b in grapheme_spans(line_text)]
            column_x = max(0.0, local_x)
            for a, b in clusters:
                if column_x < (a + b) * 0.5 * char_width:
                    return line_start + a
            return line_start + len(line_text)
        column_x = max(0.0, local_x)
        for a, b in spans:
            if column_x < ((a + b) / 2) * char_width:
                return a
        return len(self.value)

    def _pointer_down(self, event):
        if self.disabled:
            return
        self._clear_composition(restore_selection=True)
        self.cursor = self._offset_from_pointer(event)
        self.anchor = self.cursor
        self._selecting = True
        self._sync_node()

    def _pointer_move(self, event):
        if not getattr(self, "_selecting", False) or self.disabled:
            return
        self.cursor = self._offset_from_pointer(event)
        self._sync_node()

    def _pointer_up(self, _event=None):
        self._selecting = False

    def _clipboard_get(self):
        getter = getattr(self.clipboard, "get_text", None)
        return getter() if callable(getter) else None

    def _clipboard_set(self, value: str):
        setter = getattr(self.clipboard, "set_text", None)
        if callable(setter):
            setter(value)
            return True
        return False

    def _replace_selection(self, inserted: str):
        if self.disabled or self.read_only:
            return False
        start, end = self.selection
        start = normalize_grapheme_boundary(self.value, start)
        end = normalize_grapheme_boundary(self.value, end, forward=True)
        room = None if self.max_length is None else max(0, self.max_length - (len(self.value) - (end - start)))
        if room is not None and len(inserted) > room:
            inserted = inserted[:normalize_grapheme_boundary(inserted, room, forward=False)]
        if not inserted and start == end:
            return False
        self.value = self.value[:start] + inserted + self.value[end:]
        self.cursor = start + len(inserted)
        self.anchor = self.cursor
        self._sync_node()
        if self.on_change is not None:
            self.on_change(self.value)
        return True

    def _text_editing(self, event):
        """Update the temporary IME pre-edit string without mutating the value."""
        if self.disabled or self.read_only:
            return False
        text = getattr(event, "text", None) or ""
        if not text:
            changed = self._clear_composition(restore_selection=True)
            if changed:
                self._sync_node()
            return True

        if not self._composition_text:
            self._composition_original_selection = (self.anchor, self.cursor)
            self._composition_range = self.selection

        try:
            start = int(getattr(event, "text_start", -1))
        except (TypeError, ValueError):
            start = -1
        try:
            length = int(getattr(event, "text_length", -1))
        except (TypeError, ValueError):
            length = -1
        if start < 0:
            start = len(text)
        start = normalize_grapheme_boundary(
            text, min(len(text), start), forward=False
        )
        end = start if length <= 0 else min(len(text), start + length)
        end = normalize_grapheme_boundary(text, end, forward=True)
        self._composition_text = text
        self._composition_cursor = start
        self._composition_selection_length = max(0, end - start)
        self._sync_node()
        return True

    def _text_input(self, event):
        if self.disabled or self.read_only:
            return False
        self._clear_composition(restore_selection=True)
        text = getattr(event, "text", None) or ""
        if not self.multiline:
            text = text.replace("\r", "").replace("\n", "")
        return self._replace_selection(text)

    def _key_down(self, event):
        if self.disabled:
            return False
        key = getattr(event, "key", None)
        if key is None:
            return False
        code = key.keycode
        if self._composition_text:
            if code == _KEY_ESCAPE:
                self._clear_composition(restore_selection=True)
                clear_composition = getattr(self.clipboard, "clear_composition", None)
                if callable(clear_composition):
                    clear_composition()
                self._sync_node()
                return True
            self._clear_composition(restore_selection=True)
            self._sync_node()
        shift = bool(key.modifiers & _MOD_SHIFT)
        control = bool(key.modifiers & _MOD_CTRL)
        if control and code in (ord("a"), ord("A")):
            self.anchor, self.cursor = 0, len(self.value)
            self._sync_node()
            return True
        if control and code in (ord("c"), ord("C")):
            start, end = self.selection
            if start != end:
                self._clipboard_set(self.value[start:end])
            return True
        if control and code in (ord("x"), ord("X")):
            start, end = self.selection
            if start != end and not self.read_only:
                if self._clipboard_set(self.value[start:end]):
                    return self._replace_selection("")
            return True
        if control and code in (ord("v"), ord("V")):
            if not self.read_only:
                value = self._clipboard_get()
                return self._replace_selection(value) if isinstance(value, str) else True
            return True
        if code == _KEY_RETURN:
            if self.multiline:
                return self._replace_selection("\n")
            if self.on_submit is not None:
                self.on_submit(self.value)
            return True
        if code == _KEY_ESCAPE:
            return True
        if code == _KEY_BACKSPACE:
            if self.read_only:
                return True
            if self.selection[0] == self.selection[1] and self.cursor > 0:
                self.anchor = previous_grapheme_boundary(self.value, self.cursor)
            return self._replace_selection("")
        if code == _KEY_DELETE:
            if self.read_only:
                return True
            if self.selection[0] == self.selection[1] and self.cursor < len(self.value):
                self.anchor = next_grapheme_boundary(self.value, self.cursor)
            return self._replace_selection("")
        if code in (_KEY_LEFT, _KEY_RIGHT, _KEY_HOME, _KEY_END):
            if code == _KEY_LEFT:
                if not shift and self.selection[0] != self.selection[1]:
                    next_cursor = self.selection[0]
                elif control:
                    next_cursor = self.cursor
                    while next_cursor > 0 and self.value[next_cursor - 1].isspace():
                        next_cursor = previous_grapheme_boundary(self.value, next_cursor)
                    while next_cursor > 0 and not self.value[next_cursor - 1].isspace():
                        next_cursor = previous_grapheme_boundary(self.value, next_cursor)
                else:
                    next_cursor = previous_grapheme_boundary(self.value, self.cursor)
            elif code == _KEY_RIGHT:
                if not shift and self.selection[0] != self.selection[1]:
                    next_cursor = self.selection[1]
                elif control:
                    next_cursor = self.cursor
                    while next_cursor < len(self.value) and self.value[next_cursor].isspace():
                        next_cursor = next_grapheme_boundary(self.value, next_cursor)
                    while next_cursor < len(self.value) and not self.value[next_cursor].isspace():
                        next_cursor = next_grapheme_boundary(self.value, next_cursor)
                else:
                    next_cursor = next_grapheme_boundary(self.value, self.cursor)
            elif code == _KEY_HOME:
                next_cursor = self.value.rfind("\n", 0, self.cursor) + 1 if self.multiline else 0
            else:
                next_cursor = self.value.find("\n", self.cursor) if self.multiline else len(self.value)
                if next_cursor < 0:
                    next_cursor = len(self.value)
            if not shift:
                self.anchor = next_cursor
            self.cursor = next_cursor
            self._sync_node()
            return True
        if self.multiline and code in (_KEY_UP, _KEY_DOWN):
            layout = self._built_node.text_layout if self._built_node is not None else None
            if layout is not None and callable(getattr(layout, "caret_position", None)):
                x, y, _line = layout.caret_position(self.cursor)
                target_y = y - layout.line_height if code == _KEY_UP else y + layout.line_height
                next_cursor = normalize_grapheme_boundary(
                    self.value, layout.offset_at(x, max(0.0, target_y)), forward=False
                )
            else:
                current_line_start = self.value.rfind("\n", 0, self.cursor) + 1
                column = self.cursor - current_line_start
                if code == _KEY_UP:
                    previous_end = current_line_start - 1
                    previous_start = self.value.rfind("\n", 0, max(0, previous_end)) + 1
                    previous_text = self.value[previous_start:max(previous_start, previous_end)]
                    boundaries = [0] + [b for _, b in grapheme_spans(previous_text)]
                    next_cursor = previous_start + max((b for b in boundaries if b <= column), default=0)
                else:
                    current_end = self.value.find("\n", self.cursor)
                    current_end = len(self.value) if current_end < 0 else current_end
                    next_start = current_end + 1
                    if next_start > len(self.value):
                        return True
                    next_end = self.value.find("\n", next_start)
                    next_end = len(self.value) if next_end < 0 else next_end
                    target_text = self.value[next_start:next_end]
                    boundaries = [0] + [b for _, b in grapheme_spans(target_text)]
                    next_cursor = next_start + max((b for b in boundaries if b <= column), default=0)
            if not shift:
                self.anchor = next_cursor
            self.cursor = next_cursor
            self._sync_node()
            return True
        return False


@dataclass
class TextArea(TextField):
    """Multi-line text editor with basic line and cursor navigation."""
    height: float = 128
    multiline: bool = True


@dataclass
class Dropdown:
    options: Sequence[str]
    value: str | None = None
    placeholder: str = "Select an option"
    width: float = 240
    disabled: bool = False
    on_change: Callable[[str], None] | None = None
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        self.options = tuple(self.options)
        if not self.options:
            raise ValueError("Dropdown requires at least one option")
        if len(set(self.options)) != len(self.options):
            raise ValueError("Dropdown options must be unique")
        if self.value is not None and self.value not in self.options:
            raise ValueError("Dropdown value must match an option")
        if self.width <= 0:
            raise ValueError("Dropdown width must be positive")
        self.is_open = False
        self._active_index = self.options.index(self.value) if self.value in self.options else 0
        self._root: LayoutNode | None = None
        self._header: LayoutNode | None = None

    def _header_text(self):
        return f"{self.value if self.value is not None else self.placeholder}  ▾"

    def _set_open(self, opened):
        if self.disabled:
            return
        self.is_open = bool(opened)
        if self._root is not None:
            self._root.children = [self._header] + (self._option_nodes() if self.is_open else [])
            self._header.accessibility_expanded = self.is_open

    def _toggle(self, _event=None):
        self._set_open(not self.is_open)

    def _select(self, option):
        if self.disabled:
            return
        changed = option != self.value
        self.value = option
        self._active_index = self.options.index(option)
        if self._header is not None:
            self._header.text = self._header_text()
            self._header.accessibility_value = option
        self._set_open(False)
        if changed and self.on_change is not None:
            self.on_change(option)

    def _update_option_visuals(self):
        if self._root is None:
            return
        for index, node in enumerate(self._root.children[1:]):
            option = self.options[index]
            active = index == self._active_index
            selected = option == self.value
            node.background = (self.theme.primary_soft if active else
                               self.theme.surface_variant if selected else self.theme.surface)
            node.accessibility_focused = active
            node.accessibility_selected = selected

    def _option_nodes(self):
        nodes = []
        for index, option in enumerate(self.options):
            selected = option == self.value
            node = _text_node(
                ("✓  " if selected else "    ") + option,
                color=self.theme.primary if selected else self.theme.foreground,
                size=14, padding=Insets.symmetric(horizontal=12, vertical=8),
                background=(self.theme.primary_soft if index == self._active_index else
                            self.theme.surface_variant if selected else self.theme.surface),
                radius=self.theme.radius_small, role="option", label=option,
                selected=selected,
                on_click=lambda event, item=option: self._select(item),
            )
            node.width = self.width
            node.on_key_down = lambda event, idx=index: self._key_down(event, idx)
            node.accessibility_focused = index == self._active_index
            nodes.append(node)
        return nodes

    def _key_down(self, event, index=None):
        key = getattr(event, "key", None)
        if key is None:
            return False
        code = key.keycode
        if code in (_KEY_RETURN, 32, _KEY_DOWN, _KEY_UP):
            if not self.is_open:
                self._set_open(True)
            else:
                if code == _KEY_DOWN:
                    self._active_index = min(len(self.options) - 1, self._active_index + 1)
                    self._update_option_visuals()
                elif code == _KEY_UP:
                    self._active_index = max(0, self._active_index - 1)
                    self._update_option_visuals()
                elif code in (_KEY_RETURN, 32):
                    self._select(self.options[self._active_index])
            return True
        if code == _KEY_ESCAPE and self.is_open:
            self._set_open(False)
            return True
        return False

    def build(self):
        self._header = _text_node(
            self._header_text(), color=self.theme.foreground, size=14,
            padding=Insets.symmetric(horizontal=12, vertical=10),
            background=self.theme.disabled_surface if self.disabled else self.theme.surface,
            radius=self.theme.radius_medium, role="combobox",
            label=self.placeholder, value=self.value,
            disabled=self.disabled, on_click=None if self.disabled else self._toggle,
        )
        self._header.width = self.width
        self._header.border_color = self.theme.border
        self._header.border_width = 1
        self._header.accessibility_expanded = self.is_open
        self._header.on_key_down = None if self.disabled else self._key_down
        self._root = LayoutNode.column(
            self._header, *(self._option_nodes() if self.is_open else []),
            spacing=3, width=self.width,
            accessibility_role="group", accessibility_label=self.placeholder,
        )
        return self._root


@dataclass
class Slider:
    """Accessible single-value slider supporting pointer drag and arrow keys."""
    value: float = 0
    minimum: float = 0
    maximum: float = 100
    step: float = 1
    width: float = 240
    disabled: bool = False
    on_change: Callable[[float], None] | None = None
    label: str = "Value"
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        if self.maximum <= self.minimum:
            raise ValueError("Slider maximum must be greater than minimum")
        if self.step <= 0 or self.width <= 32:
            raise ValueError("Slider step must be positive and width must exceed 32")
        if not self.minimum <= self.value <= self.maximum:
            raise ValueError("Slider value must be within minimum and maximum")
        self._node: LayoutNode | None = None

    @property
    def percentage(self):
        return (self.value - self.minimum) / (self.maximum - self.minimum)

    def _set_value(self, value):
        if self.disabled:
            return False
        value = min(self.maximum, max(self.minimum, value))
        steps = round((value - self.minimum) / self.step)
        value = min(self.maximum, max(self.minimum, self.minimum + steps * self.step))
        if value == self.value:
            return False
        self.value = value
        if self._node is not None:
            self._node.accessibility_value = f"{self.value:g}"
        if self.on_change is not None:
            self.on_change(self.value)
        return True

    def _pointer_value(self, event):
        pointer = getattr(event, "pointer", None)
        node = self._node
        if pointer is None or node is None:
            return False
        usable = max(1.0, node.bounds.width - 20)
        ratio = min(1.0, max(0.0, (pointer.x - node.bounds.x - 10) / usable))
        return self._set_value(self.minimum + ratio * (self.maximum - self.minimum))

    def _key_down(self, event):
        if self.disabled or getattr(event, "key", None) is None:
            return False
        code = event.key.keycode
        if code in (_KEY_LEFT, _KEY_DOWN):
            self._set_value(self.value - self.step)
        elif code in (_KEY_RIGHT, _KEY_UP):
            self._set_value(self.value + self.step)
        elif code == _KEY_HOME:
            self._set_value(self.minimum)
        elif code == _KEY_END:
            self._set_value(self.maximum)
        else:
            return False
        return True

    def _paint(self, renderer, node):
        if not hasattr(renderer, "draw_rect"):
            return
        r = node.bounds
        left, right = r.x + 10, r.right - 10
        center = r.y + r.height / 2
        track_width = max(1.0, right - left)
        renderer.draw_rect(left, center - 2, track_width, 4,
                           self.theme.border, radius=2)
        thumb_x = left + track_width * self.percentage
        if self.percentage > 0:
            renderer.draw_rect(left, center - 2, max(0.0, thumb_x - left), 4,
                               self.theme.primary, radius=2)
        renderer.draw_rect(thumb_x - 9, center - 9, 18, 18,
                           self.theme.surface, radius=9)
        if hasattr(renderer, "draw_stroke_rect"):
            renderer.draw_stroke_rect(thumb_x - 9, center - 9, 18, 18,
                                      self.theme.disabled_text if self.disabled else self.theme.primary,
                                      stroke_width=2, radius=9)

    def build(self):
        node = LayoutNode.box(
            width=self.width, height=28, intrinsic_size=Size(self.width, 28),
            accessibility_role="slider", accessibility_label=self.label,
            accessibility_value=f"{self.value:g}",
            accessibility_disabled=self.disabled,
            on_pointer_down=None if self.disabled else self._pointer_value,
            on_pointer_move=None if self.disabled else self._pointer_value,
            on_key_down=None if self.disabled else self._key_down,
        )
        node.paint_callback = self._paint
        self._node = node
        return node


@dataclass
class TabItem:
    label: str
    content: object | None = None
    disabled: bool = False


@dataclass
class Tabs:
    """Horizontal tab navigation with optional panel content."""
    tabs: Sequence[TabItem | str]
    value: str | None = None
    on_change: Callable[[str], None] | None = None
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        self.tabs = tuple(item if isinstance(item, TabItem) else TabItem(str(item)) for item in self.tabs)
        labels = [item.label for item in self.tabs]
        if not labels or len(set(labels)) != len(labels):
            raise ValueError("Tabs require unique labels")
        if self.value is None:
            self.value = labels[0]
        if self.value not in labels:
            raise ValueError("Tabs value must match a tab label")
        self._root: LayoutNode | None = None
        self._tab_nodes: dict[str, LayoutNode] = {}

    def _select(self, label):
        item = next(tab for tab in self.tabs if tab.label == label)
        if item.disabled or label == self.value:
            return
        self.value = label
        self._sync()
        if self.on_change is not None:
            self.on_change(label)

    def _move(self, index, direction):
        enabled = [tab for tab in self.tabs if not tab.disabled]
        if not enabled:
            return
        current = next((i for i, tab in enumerate(enabled) if tab.label == self.value), 0)
        self._select(enabled[(current + direction) % len(enabled)].label)

    def _tab_key(self, event, _index=None):
        key = getattr(event, "key", None)
        if key is None:
            return False
        if key.keycode == _KEY_LEFT:
            self._move(0, -1)
            return True
        if key.keycode == _KEY_RIGHT:
            self._move(0, 1)
            return True
        return False

    def _content_node(self):
        current = next(tab for tab in self.tabs if tab.label == self.value)
        if current.content is None:
            return LayoutNode.box(height=1, intrinsic_size=Size(1, 1))
        if isinstance(current.content, str):
            return Label(current.content, theme=self.theme).build()
        return _node(current.content)

    def _sync(self):
        for item in self.tabs:
            node = self._tab_nodes.get(item.label)
            if node is not None:
                selected = item.label == self.value
                node.background = self.theme.primary_soft if selected else None
                node.text_color = self.theme.primary if selected else self.theme.muted
                node.accessibility_selected = selected
                node.accessibility_disabled = item.disabled
        if self._root is not None:
            self._root.children[1] = self._content_node()

    def build(self):
        self._tab_nodes = {}
        nodes = []
        for index, item in enumerate(self.tabs):
            selected = item.label == self.value
            node = _text_node(
                item.label, color=self.theme.primary if selected else self.theme.muted,
                size=14, weight="semibold" if selected else "medium",
                padding=Insets.symmetric(horizontal=14, vertical=9),
                background=self.theme.primary_soft if selected else None,
                radius=self.theme.radius_small, role="tab", label=item.label,
                selected=selected, disabled=item.disabled,
                on_click=None if item.disabled else lambda event, label=item.label: self._select(label),
            )
            node.on_key_down = self._tab_key
            self._tab_nodes[item.label] = node
            nodes.append(node)
        tablist = LayoutNode.row(*nodes, spacing=3, cross_align=Alignment.CENTER,
                                 accessibility_role="tablist")
        self._root = LayoutNode.column(tablist, self._content_node(), spacing=10,
                                       accessibility_role="group")
        return self._root


@dataclass
class SegmentedControl:
    """Compact mutually-exclusive options rendered as a native segmented row."""
    options: Sequence[str]
    value: str | None = None
    on_change: Callable[[str], None] | None = None
    disabled: bool = False
    theme: NativeTheme = field(default_factory=NativeTheme)

    def __post_init__(self):
        self.options = tuple(self.options)
        if not self.options or len(set(self.options)) != len(self.options):
            raise ValueError("SegmentedControl requires unique options")
        if self.value is None:
            self.value = self.options[0]
        if self.value not in self.options:
            raise ValueError("SegmentedControl value must match an option")
        self._nodes: dict[str, LayoutNode] = {}

    def _select(self, option):
        if self.disabled or option == self.value:
            return
        self.value = option
        for label, node in self._nodes.items():
            selected = label == option
            node.background = self.theme.surface if selected else self.theme.surface_variant
            node.text_color = self.theme.primary if selected else self.theme.foreground
            node.accessibility_selected = selected
        if self.on_change is not None:
            self.on_change(option)

    def _key_down(self, event):
        key = getattr(event, "key", None)
        if self.disabled or key is None:
            return False
        if key.keycode in (_KEY_LEFT, _KEY_UP):
            step = -1
        elif key.keycode in (_KEY_RIGHT, _KEY_DOWN):
            step = 1
        else:
            return False
        index = self.options.index(self.value)
        self._select(self.options[(index + step) % len(self.options)])
        return True

    def build(self):
        self._nodes = {}
        nodes = []
        for option in self.options:
            selected = option == self.value
            node = _text_node(
                option, color=self.theme.primary if selected else self.theme.foreground,
                size=13, weight="semibold" if selected else "medium",
                padding=Insets.symmetric(horizontal=12, vertical=8),
                background=self.theme.surface if selected else self.theme.surface_variant,
                radius=self.theme.radius_small, role="radio", label=option,
                selected=selected, disabled=self.disabled,
                on_click=None if self.disabled else lambda event, item=option: self._select(item),
            )
            node.on_key_down = None if self.disabled else self._key_down
            self._nodes[option] = node
            nodes.append(node)
        return LayoutNode.row(
            *nodes, spacing=3, padding=Insets.all(3),
            background=self.theme.surface_variant, radius=self.theme.radius_medium,
            accessibility_role="radiogroup", accessibility_label="Selection",
        )


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


def row(*children, spacing: float = 8, wrap: bool = False,
        wrap_spacing: float = 0, **kwargs) -> LayoutNode:
    """Compose widgets horizontally, optionally wrapping into new rows."""
    if "flex_wrap" in kwargs:
        wrap = bool(kwargs.pop("flex_wrap"))
    return LayoutNode.row(*[_node(child) for child in children], spacing=spacing,
                          flex_wrap=wrap, wrap_spacing=wrap_spacing, **kwargs)


def column(*children, spacing: float = 8, wrap: bool = False,
           wrap_spacing: float = 0, **kwargs) -> LayoutNode:
    """Compose widgets vertically, optionally wrapping into new columns."""
    if "flex_wrap" in kwargs:
        wrap = bool(kwargs.pop("flex_wrap"))
    return LayoutNode.column(*[_node(child) for child in children], spacing=spacing,
                             flex_wrap=wrap, wrap_spacing=wrap_spacing, **kwargs)


def stack(*children, **kwargs) -> LayoutNode:
    """Overlay widgets or nodes in a native stack."""
    return LayoutNode.stack(*[_node(child) for child in children], **kwargs)


__all__ = [
    "Badge", "Button", "Card", "Checkbox", "Divider", "Label", "ProgressBar",
    "RadioGroup", "Spacer", "Switch", "TextField", "TextArea", "Dropdown",
    "Slider", "Tabs", "TabItem", "SegmentedControl", "column", "row", "stack",
]
