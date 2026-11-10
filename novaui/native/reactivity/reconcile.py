"""Keyed retained-tree reconciliation for native LayoutNode trees."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from ..layout.node import LayoutNode

@dataclass(frozen=True)
class ReconcileResult:
    root: LayoutNode
    created: tuple[LayoutNode, ...]
    reused: tuple[LayoutNode, ...]
    removed: tuple[LayoutNode, ...]

_VISUAL_FIELDS = (
    "kind", "width", "height", "padding", "spacing", "weight", "align",
    "main_align", "cross_align", "intrinsic_size", "background", "radius",
    "text", "text_color", "font_size", "font_weight", "text_wrap",
    "text_align", "text_line_height", "text_max_lines", "scroll_axis", "scroll_x", "scroll_y", "key",
    "on_click", "on_pointer_down", "on_pointer_up", "on_pointer_move",
    "on_pointer_enter", "on_pointer_leave", "on_wheel",
)

def _validate_sibling_keys(nodes):
    seen=set()
    for node in nodes:
        if not isinstance(node, LayoutNode):
            raise TypeError("all children must be LayoutNode instances")
        if node.key is not None:
            if node.key in seen:
                raise ValueError(f"duplicate sibling key: {node.key!r}")
            seen.add(node.key)

def _compatible(old, new):
    return old.kind == new.kind and (
        (old.key == new.key) if (old.key is not None or new.key is not None)
        else True
    )

def reconcile(old_root: Optional[LayoutNode], new_root: LayoutNode) -> ReconcileResult:
    """Update an existing tree in place where identity can be preserved.

    Keyed siblings match by key regardless of position. Unkeyed siblings match
    by their positional slot and compatible kind. Bounds and measured geometry
    stay attached to reused instances until the next layout pass.
    """
    if not isinstance(new_root, LayoutNode):
        raise TypeError("component build must return a LayoutNode")
    created=[]; reused=[]; removed=[]

    def walk(old, new):
        if old is None or not _compatible(old,new):
            collect(new,created)
            if old is not None: collect(old,removed)
            return new
        reused.append(old)
        old_children=list(old.children)
        new_children=list(new.children)
        _validate_sibling_keys(old_children)
        _validate_sibling_keys(new_children)

        keyed_old={c.key:c for c in old_children if c.key is not None}
        unkeyed_old=[c for c in old_children if c.key is None]
        used=set()
        result_children=[]
        unkeyed_index=0
        for child in new_children:
            candidate=None
            if child.key is not None:
                candidate=keyed_old.get(child.key)
            else:
                while unkeyed_index < len(unkeyed_old):
                    possible=unkeyed_old[unkeyed_index]
                    unkeyed_index += 1
                    if id(possible) not in used:
                        candidate=possible
                        break
            if candidate is not None and id(candidate) in used:
                candidate=None
            if candidate is not None and not _compatible(candidate,child):
                candidate=None
            if candidate is not None:
                used.add(id(candidate))
            result_children.append(walk(candidate,child))
        for old_child in old_children:
            if id(old_child) not in used:
                collect(old_child,removed)
        for field in _VISUAL_FIELDS:
            setattr(old,field,getattr(new,field))
        old.children=result_children
        return old

    def collect(node,target):
        target.append(node)
        for child in node.children:
            collect(child,target)

    root=walk(old_root,new_root)
    return ReconcileResult(root,tuple(created),tuple(reused),tuple(removed))
