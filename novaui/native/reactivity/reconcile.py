"""Keyed retained-tree reconciliation for native LayoutNode trees."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Optional

from ..layout.node import LayoutNode


@dataclass(frozen=True)
class ReconcileResult:
    root: LayoutNode
    created: tuple[LayoutNode, ...]
    reused: tuple[LayoutNode, ...]
    removed: tuple[LayoutNode, ...]


# These fields are owned by the live layout/input runtime rather than by a
# component's declarative build function.  They intentionally survive a
# component rebuild when the corresponding node is reused.
_RUNTIME_STATE_FIELDS = frozenset({
    "accessibility_focused",
    "scroll_x", "scroll_y",
    "text_scroll_x", "text_scroll_y",
})

# LayoutNode is the source of truth for declarative fields.  Deriving this list
# from the dataclass prevents new public visual, accessibility, grid or event
# fields from silently being omitted from reconciliation in future releases.
_DERIVED_FIELDS = frozenset({
    "text_layout", "content_size", "max_scroll_x", "max_scroll_y",
    "bounds", "content_bounds", "measured_size", "grid_actual_columns",
})
_RECONCILED_FIELDS = tuple(
    item.name for item in fields(LayoutNode)
    if item.init and item.name not in {"children", *_RUNTIME_STATE_FIELDS, *_DERIVED_FIELDS}
)


def _validate_sibling_keys(nodes):
    seen = set()
    for node in nodes:
        if not isinstance(node, LayoutNode):
            raise TypeError("all children must be LayoutNode instances")
        if node.key is not None:
            try:
                duplicate = node.key in seen
                seen.add(node.key)
            except TypeError as exc:
                raise TypeError("layout node keys must be hashable") from exc
            if duplicate:
                raise ValueError(f"duplicate sibling key: {node.key!r}")


def _compatible(old, new):
    return old.kind == new.kind and (
        (old.key == new.key) if (old.key is not None or new.key is not None)
        else True
    )


def reconcile(old_root: Optional[LayoutNode], new_root: LayoutNode) -> ReconcileResult:
    """Update an existing tree in place where identity can be preserved.

    Keyed siblings match by key regardless of position. Unkeyed siblings match
    by their positional slot and compatible kind. Declarative fields (including
    callbacks, paint hooks, accessibility metadata and newer widget properties)
    are copied from the new tree. Runtime focus and scroll positions remain on
    reused nodes; measured geometry is recomputed by the next layout pass.
    """
    if not isinstance(new_root, LayoutNode):
        raise TypeError("component build must return a LayoutNode")
    created = []
    reused = []
    removed = []

    def collect(node, target):
        target.append(node)
        for child in node.children:
            collect(child, target)

    def walk(old, new):
        if old is None or not _compatible(old, new):
            collect(new, created)
            if old is not None:
                collect(old, removed)
            return new

        reused.append(old)
        old_children = list(old.children)
        new_children = list(new.children)
        _validate_sibling_keys(old_children)
        _validate_sibling_keys(new_children)

        keyed_old = {child.key: child for child in old_children if child.key is not None}
        unkeyed_old = [child for child in old_children if child.key is None]
        used = set()
        result_children = []
        unkeyed_index = 0

        for child in new_children:
            candidate = None
            if child.key is not None:
                candidate = keyed_old.get(child.key)
            else:
                while unkeyed_index < len(unkeyed_old):
                    possible = unkeyed_old[unkeyed_index]
                    unkeyed_index += 1
                    if id(possible) not in used:
                        candidate = possible
                        break
            if candidate is not None and id(candidate) in used:
                candidate = None
            if candidate is not None and not _compatible(candidate, child):
                candidate = None
            if candidate is not None:
                used.add(id(candidate))
            result_children.append(walk(candidate, child))

        for old_child in old_children:
            if id(old_child) not in used:
                collect(old_child, removed)

        # Preserve live interaction state on the retained node. Declarative
        # configuration and every callback are refreshed from the new build.
        runtime_state = {
            name: getattr(old, name) for name in _RUNTIME_STATE_FIELDS
        }
        for name in _RECONCILED_FIELDS:
            setattr(old, name, getattr(new, name))
        for name, value in runtime_state.items():
            setattr(old, name, value)
        old.children = result_children
        # A text/configuration update must not expose a stale text layout to
        # painters or hit-testing before the next measure pass.
        old.text_layout = None
        return old

    root = walk(old_root, new_root)
    return ReconcileResult(root, tuple(created), tuple(reused), tuple(removed))
