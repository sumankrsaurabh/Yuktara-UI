"""Backend-neutral accessibility semantics for the native widget tree."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .layout import LayoutNode, Rect
from .layout.node import ACCESSIBILITY_ACTIONS


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
    identifier: str | None = None
    role_description: str | None = None
    orientation: str | None = None
    live: str | None = None
    read_only: bool | None = None
    required: bool | None = None
    invalid: bool | None = None
    range_min: float | None = None
    range_max: float | None = None
    range_value: float | None = None
    actions: tuple[str, ...] = ()


def build_accessibility_tree(root: LayoutNode | None, *, overlays=()) -> SemanticNode | None:
    """Translate app and optional overlay trees into an immutable semantic snapshot.

    Hidden nodes prune their entire subtree. Identifiers must be unique within
    the *exposed* snapshot. When a modal overlay is active, content behind the
    topmost modal is removed before the identifiers are checked.
    """
    if root is None:
        return None

    overlay_items = tuple(overlays)
    modal_index = next(
        (index for index in range(len(overlay_items) - 1, -1, -1)
         if bool(getattr(overlay_items[index], "modal", False)) or
         getattr(overlay_items[index].root if hasattr(overlay_items[index], "root") else overlay_items[index],
                 "accessibility_role", None) == "dialog-overlay"),
        None,
    )
    active_overlays = overlay_items[modal_index:] if modal_index is not None else overlay_items
    identifiers: set[str] = set()

    def build(node: LayoutNode) -> SemanticNode | None:
        if node.accessibility_hidden:
            return None
        children = tuple(filter(None, (build(child) for child in node.children)))
        role = node.accessibility_role
        if role is None and not children:
            return None
        identifier = node.accessibility_identifier
        if identifier is not None:
            if identifier in identifiers:
                raise ValueError(f"duplicate accessibility identifier: {identifier}")
            identifiers.add(identifier)
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
            identifier=identifier,
            role_description=node.accessibility_role_description,
            orientation=node.accessibility_orientation,
            live=node.accessibility_live,
            read_only=node.accessibility_read_only,
            required=node.accessibility_required,
            invalid=node.accessibility_invalid,
            range_min=node.accessibility_range_min,
            range_max=node.accessibility_range_max,
            range_value=node.accessibility_range_value,
            actions=node.accessibility_actions,
        )

    overlay_nodes = tuple(
        filter(None, (build(item.root if hasattr(item, "root") else item)
                      for item in active_overlays))
    )
    base = None if modal_index is not None else build(root)
    if not overlay_nodes:
        return base
    children = overlay_nodes if modal_index is not None else (((base,) if base is not None else ()) + overlay_nodes)
    return SemanticNode(
        role="application", label=root.accessibility_label, bounds=root.bounds,
        children=children,
    )


__all__ = ["SemanticNode", "build_accessibility_tree", "ACCESSIBILITY_ACTIONS"]
