"""Backend-neutral layout tree nodes."""
from __future__ import annotations
from dataclasses import dataclass, field
from math import isfinite
from typing import Callable, Optional
from .geometry import Alignment, Insets, MainAxisAlignment, Rect, Size

@dataclass
class LayoutNode:
    kind: str = "box"
    children: list["LayoutNode"] = field(default_factory=list)
    width: Optional[float | str] = None
    height: Optional[float | str] = None
    min_width: Optional[float | str] = None
    max_width: Optional[float | str] = None
    min_height: Optional[float | str] = None
    max_height: Optional[float | str] = None
    padding: Insets = field(default_factory=Insets)
    spacing: float = 0.0
    weight: float = 0.0
    align: Alignment = Alignment.START
    main_align: MainAxisAlignment = MainAxisAlignment.START
    cross_align: Alignment = Alignment.STRETCH
    align_self: Optional[Alignment] = None
    baseline: Optional[float] = None
    flex_basis: Optional[float | str] = None
    flex_wrap: bool = False
    wrap_spacing: float = 0.0
    align_content: Alignment = Alignment.START
    position: str = "flow"
    left: Optional[float | str] = None
    right: Optional[float | str] = None
    top: Optional[float | str] = None
    bottom: Optional[float | str] = None
    intrinsic_size: Size = field(default_factory=Size)
    background: Optional[object] = None
    radius: float = 0.0
    opacity: float = 1.0
    focus_ring_color: object = 0xFF2563EB
    focus_ring_width: float = 2.0
    border_color: Optional[object] = None
    border_width: float = 0.0
    text: Optional[str] = None
    text_color: object = 0xFF202735
    font_size: float = 14.0
    font_family: str = "Inter"
    font_weight: str = "normal"
    text_selection: Optional[tuple[int, int]] = None
    text_composition: Optional[tuple[int, int]] = None
    text_composition_color: object = 0xFF2563EB
    text_style_spans: tuple = ()
    text_paragraph_styles: tuple = ()
    text_cursor: Optional[int] = None
    text_selection_color: object = 0x663B82F6
    text_caret_color: object = 0xFF2563EB
    text_caret_width: float = 1.5
    text_clip: bool = False
    text_scroll_x: float = 0.0
    text_scroll_y: float = 0.0
    text_wrap: bool = True
    text_align: str = "start"
    text_line_height: Optional[float] = None
    text_max_lines: Optional[int] = None
    text_layout: object = field(default=None, init=False, repr=False)
    scroll_axis: str = "vertical"
    scroll_x: float = 0.0
    scroll_y: float = 0.0
    content_size: Size = field(default_factory=Size, init=False)
    max_scroll_x: float = field(default=0.0, init=False)
    max_scroll_y: float = field(default=0.0, init=False)
    key: Optional[str] = None
    on_click: Optional[Callable] = None
    on_pointer_down: Optional[Callable] = None
    on_pointer_up: Optional[Callable] = None
    on_pointer_move: Optional[Callable] = None
    on_pointer_enter: Optional[Callable] = None
    on_pointer_leave: Optional[Callable] = None
    on_wheel: Optional[Callable] = None
    on_key_down: Optional[Callable] = None
    on_text_input: Optional[Callable] = None
    on_text_editing: Optional[Callable] = None
    on_text_layout: Optional[Callable] = field(default=None, repr=False)
    on_focus: Optional[Callable] = None
    on_blur: Optional[Callable] = None
    paint_callback: Optional[Callable] = field(default=None, repr=False)
    accessibility_role: Optional[str] = None
    accessibility_label: Optional[str] = None
    accessibility_value: Optional[str] = None
    accessibility_hint: Optional[str] = None
    accessibility_disabled: bool = False
    accessibility_checked: Optional[bool] = None
    accessibility_selected: Optional[bool] = None
    accessibility_expanded: Optional[bool] = None
    accessibility_focused: bool = False
    bounds: Rect = field(default_factory=Rect, init=False)
    content_bounds: Rect = field(default_factory=Rect, init=False)
    measured_size: Size = field(default_factory=Size, init=False)
    grid_columns: int = 2
    grid_min_column_width: float | None = None
    grid_column_gap: float = 8.0
    grid_row_gap: float = 8.0
    grid_actual_columns: int = field(default=2, init=False)
    grid_actual_rows: int = field(default=0, init=False)
    grid_column_widths: list[float] = field(default_factory=list, init=False, repr=False)
    grid_row_heights: list[float] = field(default_factory=list, init=False, repr=False)
    grid_row: Optional[int] = None
    grid_column: Optional[int] = None
    grid_row_span: int = 1
    grid_column_span: int = 1
    flex_lines: list = field(default_factory=list, init=False, repr=False)
    grid_placements: list = field(default_factory=list, init=False, repr=False)
    first_baseline: Optional[float] = field(default=None, init=False, repr=False)
    responsive_variants: tuple[tuple[float, "LayoutNode"], ...] = ()
    responsive_active_index: int = field(default=-1, init=False)

    def __post_init__(self):
        self.kind = self.kind.lower()
        if self.kind == "responsive":
            if not self.responsive_variants:
                raise ValueError("responsive nodes require at least one width variant")
            previous_width = -1.0
            for minimum_width, child in self.responsive_variants:
                if (not isinstance(minimum_width, (int, float))
                        or isinstance(minimum_width, bool)
                        or not isfinite(float(minimum_width)) or minimum_width < 0):
                    raise ValueError("responsive variant minimum widths must be finite and non-negative")
                if minimum_width <= previous_width:
                    raise ValueError("responsive variants must have strictly increasing minimum widths")
                if not isinstance(child, LayoutNode):
                    raise TypeError("responsive variant children must be LayoutNode instances")
                previous_width = float(minimum_width)
            if self.children:
                raise ValueError("responsive node children are selected from responsive_variants")
        elif self.responsive_variants:
            raise ValueError("responsive_variants are only valid on responsive nodes")
        if self.kind not in {"box", "row", "column", "stack", "text", "scroll", "grid", "responsive"}:
            raise ValueError(f"unsupported layout node kind: {self.kind}")
        self.align = Alignment(self.align)
        self.cross_align = Alignment(self.cross_align)
        self.main_align = MainAxisAlignment(self.main_align)
        self.align_content = Alignment(self.align_content)
        if self.align_self is not None:
            self.align_self = Alignment(self.align_self)
        if isinstance(self.padding, (int, float)) and not isinstance(self.padding, bool):
            if not isfinite(float(self.padding)) or self.padding < 0:
                raise ValueError("padding must be finite and non-negative")
            self.padding = Insets.all(float(self.padding))
        elif not isinstance(self.padding, Insets):
            raise TypeError("padding must be an Insets value or a non-negative number")
        for name in ("spacing", "weight", "radius", "border_width", "focus_ring_width",
                     "wrap_spacing", "grid_column_gap", "grid_row_gap"):
            raw_value = getattr(self, name)
            if (not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool)
                    or not isfinite(float(raw_value)) or raw_value < 0):
                raise ValueError(f"{name} must be a finite non-negative number")
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("opacity must be between 0 and 1")
        if self.scroll_axis not in {"vertical", "horizontal", "both"}:
            raise ValueError("scroll_axis must be vertical, horizontal or both")
        if self.scroll_x < 0 or self.scroll_y < 0:
            raise ValueError("scroll offsets must be non-negative")
        if self.text_align not in {"start", "center", "end"}:
            raise ValueError("text_align must be start, center or end")
        if self.text_line_height is not None and self.text_line_height <= 0:
            raise ValueError("text_line_height must be positive")
        if self.text_max_lines is not None and self.text_max_lines < 1:
            raise ValueError("text_max_lines must be at least 1")
        if self.font_size <= 0 or not self.font_family:
            raise ValueError("font_size must be positive and font_family non-empty")
        if self.text_caret_width <= 0:
            raise ValueError("text_caret_width must be positive")
        if self.text_scroll_x < 0 or self.text_scroll_y < 0:
            raise ValueError("text scroll offsets must be non-negative")
        if self.text_cursor is not None and self.text_cursor < 0:
            raise ValueError("text_cursor must be non-negative")
        if self.text_selection is not None:
            if len(self.text_selection) != 2 or min(self.text_selection) < 0:
                raise ValueError("text_selection must be a non-negative (start, end) pair")
        if self.text_composition is not None:
            if (len(self.text_composition) != 2 or min(self.text_composition) < 0
                    or self.text_composition[1] < self.text_composition[0]):
                raise ValueError("text_composition must be an ordered non-negative (start, end) pair")
        if self.text_style_spans or self.text_paragraph_styles:
            from ..text.measure import TextMeasurer
            TextMeasurer._normalize_style_spans(self.text or "", self.text_style_spans)
            TextMeasurer._normalize_paragraph_styles(self.text or "", self.text_paragraph_styles)
        for name in ("width", "height", "min_width", "max_width", "min_height", "max_height",
                     "flex_basis", "left", "right", "top", "bottom"):
            _validate_length(getattr(self, name), name)
        for minimum, maximum, axis in ((self.min_width, self.max_width, "width"),
                                       (self.min_height, self.max_height, "height")):
            if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)) and minimum > maximum:
                raise ValueError(f"min_{axis} cannot exceed max_{axis}")
        if self.position not in {"flow", "absolute"}:
            raise ValueError("position must be 'flow' or 'absolute'")
        if self.baseline is not None and (not isfinite(float(self.baseline)) or self.baseline < 0):
            raise ValueError("baseline must be finite and non-negative")
        if not isinstance(self.flex_wrap, bool):
            raise TypeError("flex_wrap must be a bool")
        if self.grid_row is not None and (not isinstance(self.grid_row, int) or self.grid_row < 0):
            raise ValueError("grid_row must be a non-negative integer")
        if self.grid_column is not None and (not isinstance(self.grid_column, int) or self.grid_column < 0):
            raise ValueError("grid_column must be a non-negative integer")
        if (not isinstance(self.grid_row_span, int) or isinstance(self.grid_row_span, bool)
                or not isinstance(self.grid_column_span, int) or isinstance(self.grid_column_span, bool)
                or self.grid_row_span < 1 or self.grid_column_span < 1):
            raise ValueError("grid spans must be positive integers")
        if not isinstance(self.grid_columns, int) or isinstance(self.grid_columns, bool) or self.grid_columns < 1:
            raise ValueError("grid_columns must be a positive integer")
        if self.grid_min_column_width is not None and (
            not isfinite(float(self.grid_min_column_width)) or self.grid_min_column_width <= 0
        ):
            raise ValueError("grid_min_column_width must be finite and positive")
        if self.kind == "text" and self.intrinsic_size == Size():
            self.intrinsic_size = Size(max(0, len(self.text or "") * 8), 18)

    @classmethod
    def box(cls, child=None, **kwargs):
        return cls("box", [child] if child else [], **kwargs)
    @classmethod
    def row(cls, *children, **kwargs):
        return cls("row", list(children), **kwargs)
    @classmethod
    def column(cls, *children, **kwargs):
        return cls("column", list(children), **kwargs)
    @classmethod
    def stack(cls, *children, **kwargs):
        return cls("stack", list(children), **kwargs)
    @classmethod
    def scroll(cls, child=None, **kwargs):
        return cls("scroll", [child] if child else [], **kwargs)

@dataclass(frozen=True)
class LayoutResult:
    size: Size
    bounds: Rect


def _validate_length(value, name: str) -> None:
    """Validate non-negative logical-pixel or percentage lengths."""
    if value is None:
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not isfinite(float(value)) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
        return
    if isinstance(value, str) and value.strip().endswith("%"):
        raw = value.strip()[:-1].strip()
        try:
            number = float(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be a number or percentage") from exc
        if not isfinite(number) or number < 0:
            raise ValueError(f"{name} percentage must be finite and non-negative")
        return
    raise TypeError(f"{name} must be a number, percentage string, or None")
