"""Diagnostics for layout bounds that escape their parent's content area.

Run diagnostics after LayoutEngine.layout(). Scroll content and descendants
explicitly clipped by their parent are classified as intentional overflow.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Optional

from .node import LayoutNode
from .geometry import Rect


@dataclass(frozen=True)
class LayoutOverflow:
    """A child whose arranged bounds extend beyond its parent's content box.

    overflow stores distances in left, top, right, bottom order.
    path contains child indices from the supplied root to the child.
    """

    path: tuple[int, ...]
    parent_key: Optional[str]
    child_key: Optional[str]
    parent_kind: str
    child_kind: str
    parent_bounds: Rect
    child_bounds: Rect
    overflow: tuple[float, float, float, float]
    intentional_reason: Optional[str] = None

    @property
    def intentional(self) -> bool:
        """Whether overflow is explained by an explicit clipping/scroll contract."""
        return self.intentional_reason is not None

    @property
    def sides(self) -> tuple[str, ...]:
        names = ("left", "top", "right", "bottom")
        return tuple(name for name, amount in zip(names, self.overflow) if amount > 0)


def diagnose_overflow(
    root: LayoutNode,
    *,
    tolerance: float = 0.0,
    include_intentional: bool = False,
) -> tuple[LayoutOverflow, ...]:
    """Find children extending outside parent content bounds.

    Call after layout. By default, expected scroll-content overflow and
    overflow explicitly hidden by clip_children are omitted. Set
    include_intentional=True to inspect those cases as well.

    Absolute-positioned children are still checked: absolute positioning
    controls placement, but does not itself guarantee that overflow is safe.
    """
    if not isinstance(root, LayoutNode):
        raise TypeError("root must be a LayoutNode")
    if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
            or not isfinite(float(tolerance)) or tolerance < 0):
        raise ValueError("tolerance must be a finite non-negative number")
    if not isinstance(include_intentional, bool):
        raise TypeError("include_intentional must be a bool")

    issues: list[LayoutOverflow] = []

    def visit(parent: LayoutNode, path: tuple[int, ...]) -> None:
        area = parent.content_bounds
        reason = ("scroll-content" if parent.kind == "scroll" else
                  "clipped-container" if parent.clip_children else None)
        for index, child in enumerate(parent.children):
            bounds = child.bounds
            overflow = (
                max(0.0, area.x - bounds.x),
                max(0.0, area.y - bounds.y),
                max(0.0, bounds.right - area.right),
                max(0.0, bounds.bottom - area.bottom),
            )
            if any(amount > tolerance for amount in overflow):
                if reason is None or include_intentional:
                    issues.append(LayoutOverflow(
                        path=path + (index,),
                        parent_key=parent.key,
                        child_key=child.key,
                        parent_kind=parent.kind,
                        child_kind=child.kind,
                        parent_bounds=area,
                        child_bounds=bounds,
                        overflow=overflow,
                        intentional_reason=reason,
                    ))
            visit(child, path + (index,))

    visit(root, ())
    return tuple(issues)
