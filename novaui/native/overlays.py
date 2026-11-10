"""Overlay lifecycle and placement for the native Yuktara UI runtime."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import Callable

from .layout import Alignment, Constraints, LayoutEngine, LayoutNode, Rect
from .widgets.overlays import ContextMenu, Dialog, Popover, Toast, Tooltip


@dataclass(frozen=True, slots=True)
class OverlayHandle:
    id: int


@dataclass
class OverlayEntry:
    handle: OverlayHandle
    kind: str
    node: LayoutNode
    root: LayoutNode
    anchor: LayoutNode | Rect | None = None
    position: tuple[float, float] | None = None
    placement: str = "bottom"
    modal: bool = False
    dismiss_on_outside: bool = True
    dismiss_on_escape: bool = True
    pointer_events: bool = True
    on_dismiss: Callable | None = None
    remaining_ms: float | None = None


class OverlayManager:
    """Owns floating native surfaces above the application layout tree.

    The host advances timed entries through ``advance_time``; no background
    timer, event loop or browser primitive is created by this manager.
    """
    PLACEMENTS = frozenset({"bottom", "top", "left", "right"})

    def __init__(self, *, on_change: Callable | None = None, scrim_color=0x66000000):
        self._ids = count(1)
        self._entries: list[OverlayEntry] = []
        self.on_change = on_change
        self.scrim_color = scrim_color
        self.width = 0.0
        self.height = 0.0

    @property
    def entries(self):
        return tuple(self._entries)

    @property
    def roots(self):
        return tuple(entry.root for entry in self._entries)

    @property
    def top(self):
        return self._entries[-1] if self._entries else None

    @property
    def has_modal(self):
        return any(entry.modal for entry in self._entries)

    def _changed(self):
        if self.on_change is not None:
            self.on_change()

    @staticmethod
    def _build(value):
        if isinstance(value, LayoutNode):
            return value
        build = getattr(value, "build", None)
        if callable(build):
            node = build()
            if isinstance(node, LayoutNode):
                return node
        raise TypeError("Overlay content must be a LayoutNode or buildable widget")

    def show(self, content, *, kind="popover", anchor=None, position=None,
             placement=None, modal=None, dismiss_on_outside=None,
             dismiss_on_escape=True, pointer_events=None, duration_ms=None,
             on_dismiss=None) -> OverlayHandle:
        if kind not in {"dialog", "popover", "tooltip", "context_menu", "toast", "custom"}:
            raise ValueError(f"Unsupported overlay kind: {kind}")
        if placement is None:
            placement = "top" if kind == "tooltip" else "bottom"
        if placement not in self.PLACEMENTS:
            raise ValueError(f"placement must be one of {sorted(self.PLACEMENTS)}")
        if position is not None:
            if len(position) != 2:
                raise ValueError("position must be an (x, y) pair")
            position = (float(position[0]), float(position[1]))
        if anchor is not None and not isinstance(anchor, (LayoutNode, Rect)):
            raise TypeError("anchor must be a LayoutNode or Rect")
        node = self._build(content)
        modal = (kind == "dialog") if modal is None else bool(modal)
        dismiss_on_outside = (modal or kind in {"popover", "context_menu"}) if dismiss_on_outside is None else bool(dismiss_on_outside)
        pointer_events = (kind not in {"tooltip", "toast"}) if pointer_events is None else bool(pointer_events)
        if duration_ms is None and kind == "toast":
            duration_ms = getattr(content, "duration_ms", None)
        if duration_ms is not None and duration_ms <= 0:
            raise ValueError("duration_ms must be positive or None")
        handle = OverlayHandle(next(self._ids))
        root = node
        if modal:
            root = LayoutNode.stack(
                node, width=self.width or None, height=self.height or None,
                align=Alignment.CENTER, background=self.scrim_color,
                on_click=(lambda _event, h=handle: self.dismiss(h, reason="outside"))
                         if dismiss_on_outside else None,
                accessibility_role="dialog-overlay",
            )
        entry = OverlayEntry(
            handle=handle, kind=kind, node=node, root=root, anchor=anchor,
            position=position, placement=placement, modal=modal,
            dismiss_on_outside=dismiss_on_outside,
            dismiss_on_escape=bool(dismiss_on_escape), pointer_events=pointer_events,
            on_dismiss=on_dismiss,
            remaining_ms=float(duration_ms) if duration_ms is not None else None,
        )
        self._entries.append(entry)
        if kind == "context_menu":
            self._wrap_context_menu_actions(node, handle)
        self._changed()
        return handle

    def show_dialog(self, dialog: Dialog | LayoutNode, *, on_dismiss=None,
                    dismiss_on_escape=True, dismiss_on_outside=True) -> OverlayHandle:
        return self.show(dialog, kind="dialog", modal=True,
                         dismiss_on_outside=dismiss_on_outside,
                         dismiss_on_escape=dismiss_on_escape,
                         on_dismiss=on_dismiss)

    def show_popover(self, popover: Popover | LayoutNode, *, anchor,
                     placement="bottom", on_dismiss=None) -> OverlayHandle:
        return self.show(popover, kind="popover", anchor=anchor,
                         placement=placement, modal=False,
                         dismiss_on_outside=True, on_dismiss=on_dismiss)

    def show_tooltip(self, tooltip: Tooltip | LayoutNode, *, anchor,
                     placement="top") -> OverlayHandle:
        return self.show(tooltip, kind="tooltip", anchor=anchor,
                         placement=placement, pointer_events=False,
                         dismiss_on_outside=False, dismiss_on_escape=False)

    def show_context_menu(self, menu: ContextMenu | LayoutNode, *, position,
                         on_dismiss=None) -> OverlayHandle:
        return self.show(menu, kind="context_menu", position=position,
                         placement="bottom", dismiss_on_outside=True,
                         on_dismiss=on_dismiss)

    def show_toast(self, toast: Toast | LayoutNode, *, duration_ms=None) -> OverlayHandle:
        if duration_ms is None and isinstance(toast, Toast):
            duration_ms = toast.duration_ms
        return self.show(toast, kind="toast", placement="top",
                         pointer_events=False, dismiss_on_outside=False,
                         dismiss_on_escape=False, duration_ms=duration_ms)

    def _wrap_context_menu_actions(self, root: LayoutNode, handle: OverlayHandle) -> None:
        stack = [root]
        while stack:
            node = stack.pop()
            stack.extend(node.children)
            if (node.accessibility_role or "").lower() != "menuitem" or node.on_click is None:
                continue
            callback = node.on_click
            def invoke(event, callback=callback, handle=handle):
                try:
                    callback(event)
                finally:
                    self.dismiss(handle, reason="select")
            node.on_click = invoke

    def dismiss(self, handle: OverlayHandle | None = None, *, reason="programmatic") -> bool:
        if not self._entries:
            return False
        entry = self._entries[-1] if handle is None else next(
            (item for item in self._entries if item.handle == handle), None
        )
        if entry is None:
            return False
        self._entries.remove(entry)
        try:
            if entry.on_dismiss is not None:
                entry.on_dismiss(reason)
        finally:
            self._changed()
        return True

    def dismiss_all(self, *, reason="programmatic") -> int:
        removed = 0
        while self._entries:
            self.dismiss(self._entries[-1].handle, reason=reason)
            removed += 1
        return removed

    def handle_escape(self) -> bool:
        # Passive overlays (tooltips and toasts) must not shield a dialog or
        # popover beneath them from Escape.
        for entry in reversed(self._entries):
            if entry.dismiss_on_escape:
                self.dismiss(entry.handle, reason="escape")
                return True
            if entry.modal:
                return True
        return False

    def advance_time(self, delta_ms: float) -> int:
        if delta_ms < 0:
            raise ValueError("delta_ms must be non-negative")
        expired = []
        for entry in self._entries:
            if entry.remaining_ms is not None:
                entry.remaining_ms -= delta_ms
                if entry.remaining_ms <= 0:
                    expired.append(entry.handle)
        for handle in expired:
            self.dismiss(handle, reason="timeout")
        return len(expired)

    def layout(self, engine: LayoutEngine, width: float, height: float) -> None:
        self.width, self.height = float(width), float(height)
        for index, entry in enumerate(self._entries):
            if entry.modal:
                entry.root.width = self.width
                entry.root.height = self.height
                engine.layout(entry.root, Rect(0, 0, self.width, self.height))
                continue
            engine.measure(entry.root, Constraints(0, self.width, 0, self.height))
            size = entry.root.measured_size
            if entry.position is not None:
                x, y = entry.position
            elif entry.anchor is not None:
                anchor = entry.anchor.bounds if isinstance(entry.anchor, LayoutNode) else entry.anchor
                x, y = self._anchored_position(anchor, size.width, size.height, entry.placement)
            elif entry.kind == "toast":
                x = self.width - size.width - 20
                y = 20 + sum(
                    item.root.measured_size.height + 10
                    for item in self._entries[:index] if item.kind == "toast"
                )
            else:
                x, y = 20, 20
            x = min(max(0.0, x), max(0.0, self.width - size.width))
            y = min(max(0.0, y), max(0.0, self.height - size.height))
            engine.arrange(entry.root, Rect(x, y, size.width, size.height))

    def _anchored_position(self, anchor: Rect, width: float, height: float, placement: str):
        gap = 8.0
        if placement == "bottom":
            x, y = anchor.x, anchor.bottom + gap
            if y + height > self.height:
                y = anchor.y - height - gap
        elif placement == "top":
            x, y = anchor.x, anchor.y - height - gap
            if y < 0:
                y = anchor.bottom + gap
        elif placement == "right":
            x, y = anchor.right + gap, anchor.y
            if x + width > self.width:
                x = anchor.x - width - gap
        else:
            x, y = anchor.x - width - gap, anchor.y
            if x < 0:
                x = anchor.right + gap
        return x, y

    def hit_test(self, x: float, y: float):
        from .layout.engine import hit_test
        for entry in reversed(self._entries):
            if not entry.pointer_events:
                continue
            target = hit_test(entry.root, x, y)
            if target is not None:
                return target, entry
        return None, None

    def dismiss_outside(self, x: float, y: float) -> bool:
        from .layout.engine import hit_test
        for entry in reversed(self._entries):
            if entry.modal:
                return False
            if not entry.dismiss_on_outside:
                continue
            if hit_test(entry.root, x, y) is None:
                return self.dismiss(entry.handle, reason="outside")
            return False
        return False

    def focus_roots(self, base_root: LayoutNode):
        modal_index = next(
            (index for index in range(len(self._entries) - 1, -1, -1)
             if self._entries[index].modal),
            None,
        )
        if modal_index is not None:
            # Keep the modal as the focus boundary, while allowing an
            # interactive popover/menu layered above it to receive focus.
            return [self._entries[modal_index].root, *[
                entry.root for entry in self._entries[modal_index + 1:]
                if entry.pointer_events
            ]]
        return [base_root, *[entry.root for entry in self._entries if entry.pointer_events]]
