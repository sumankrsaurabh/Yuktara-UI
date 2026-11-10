"""Backend-neutral layout tree nodes."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
from .geometry import Alignment, Insets, MainAxisAlignment, Rect, Size

@dataclass
class LayoutNode:
    kind: str = "box"
    children: list["LayoutNode"] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    padding: Insets = field(default_factory=Insets)
    spacing: float = 0.0
    weight: float = 0.0
    align: Alignment = Alignment.START
    main_align: MainAxisAlignment = MainAxisAlignment.START
    cross_align: Alignment = Alignment.STRETCH
    intrinsic_size: Size = field(default_factory=Size)
    background: Optional[object] = None
    radius: float = 0.0
    border_color: Optional[object] = None
    border_width: float = 0.0
    text: Optional[str] = None
    text_color: object = 0xFF202735
    font_size: float = 14.0
    font_weight: str = "normal"
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
    accessibility_role: Optional[str] = None
    accessibility_label: Optional[str] = None
    accessibility_value: Optional[str] = None
    accessibility_hint: Optional[str] = None
    accessibility_disabled: bool = False
    accessibility_checked: Optional[bool] = None
    accessibility_selected: Optional[bool] = None
    accessibility_expanded: Optional[bool] = None
    bounds: Rect = field(default_factory=Rect, init=False)
    content_bounds: Rect = field(default_factory=Rect, init=False)
    measured_size: Size = field(default_factory=Size, init=False)

    def __post_init__(self):
        self.kind = self.kind.lower()
        if self.kind not in {"box", "row", "column", "stack", "text", "scroll"}:
            raise ValueError(f"unsupported layout node kind: {self.kind}")
        if self.spacing < 0 or self.weight < 0 or self.radius < 0 or self.border_width < 0:
            raise ValueError("spacing, weight, radius and border_width must be non-negative")
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
        if self.font_size <= 0:
            raise ValueError("font_size must be positive")
        if self.width is not None and self.width < 0:
            raise ValueError("width must be non-negative")
        if self.height is not None and self.height < 0:
            raise ValueError("height must be non-negative")
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
