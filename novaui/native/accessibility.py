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
    focused: bool = False
    bounds: Rect = Rect()
    children: tuple["SemanticNode", ...] = ()


def build_accessibility_tree(root: LayoutNode | None, *, overlays=()) -> SemanticNode | None:
    """Translate app and optional overlay trees into immutable semantics.

    Pass ``runtime.overlays.roots`` to include active floating surfaces. This is
    a platform-neutral representation; OS providers such as Windows UI
    Automation, macOS NSAccessibility and Linux AT-SPI remain separate adapters.
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
            focused=node.accessibility_focused,
            bounds=node.bounds,
            children=children,
        )

    base = build(root)
    overlay_items = tuple(overlays)
    modal_active = any(
        bool(getattr(item, "modal", False)) or
        (getattr(item.root if hasattr(item, "root") else item,
                 "accessibility_role", None) == "dialog-overlay")
        for item in overlay_items
    )
    overlay_nodes = tuple(
        filter(None, (build(item.root if hasattr(item, "root") else item)
                      for item in overlay_items))
    )
    if not overlay_nodes:
        return base
    # A modal dialog owns the active accessibility scope. Do not expose the
    # obscured application tree as a sibling to screen readers.
    children = overlay_nodes if modal_active else (((base,) if base is not None else ()) + overlay_nodes)
    return SemanticNode(
        role="application", label=root.accessibility_label, bounds=root.bounds,
        children=children,
    )


__all__ = ["SemanticNode", "build_accessibility_tree"]
