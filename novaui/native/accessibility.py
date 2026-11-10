"""Backend-neutral accessibility semantics for the native widget tree."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .layout import LayoutNode, Rect


@dataclass(frozen=True, slots=True)
class SemanticNode:
    role: str
    label: str | None = None
    value: str | None = None
    hint: str | None = None
    disabled: bool = False
    checked: bool | None = None
    selected: bool | None = None
    expanded: bool | None = None
    bounds: Rect = Rect()
    children: tuple["SemanticNode", ...] = ()


def build_accessibility_tree(root: LayoutNode | None) -> SemanticNode | None:
    """Translate layout annotations into an immutable semantic tree.

    This is a platform-neutral representation. OS providers such as Windows
    UI Automation, macOS NSAccessibility and Linux AT-SPI are separate adapters.
    """
    if root is None:
        return None

    def build(node: LayoutNode) -> SemanticNode | None:
        children = tuple(filter(None, (build(child) for child in node.children)))
        role = node.accessibility_role
        if role is None and not children:
            return None
        return SemanticNode(
            role=role or "group",
            label=node.accessibility_label,
            value=node.accessibility_value,
            hint=node.accessibility_hint,
            disabled=node.accessibility_disabled,
            checked=node.accessibility_checked,
            selected=node.accessibility_selected,
            expanded=node.accessibility_expanded,
            bounds=node.bounds,
            children=children,
        )

    return build(root)


__all__ = ["SemanticNode", "build_accessibility_tree"]
