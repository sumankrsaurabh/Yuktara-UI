"""Pointer and keyboard dispatch for backend-neutral Yuktara UI trees."""
from __future__ import annotations

from dataclasses import dataclass

from ..layout.engine import hit_test
from ..layout.node import LayoutNode
from .events import EventType, InputEvent

SDLK_TAB = 9
SDLK_RETURN = 13
SDLK_ESCAPE = 27
SDLK_SPACE = 32
SDLK_LEFT = (1 << 30) | 80
SDLK_RIGHT = (1 << 30) | 79
SDLK_DOWN = (1 << 30) | 81
SDLK_UP = (1 << 30) | 82
KMOD_SHIFT = 0x0003


@dataclass(frozen=True, slots=True)
class DispatchResult:
    target: LayoutNode | None = None
    previous_hover: LayoutNode | None = None
    current_hover: LayoutNode | None = None
    handled: bool = False


class InputDispatcher:
    """Route normalized pointer, keyboard and committed-text events.

    Pointer-down captures the target until pointer-up, enabling controls such
    as sliders to keep receiving drag motion even when the pointer leaves their
    bounds. Keyboard focus is retained on the deepest focusable node.
    """

    FOCUS_ROLES = frozenset({
        "button", "checkbox", "switch", "radio", "slider", "textbox",
        "combobox", "tab", "radio-group", "radiogroup", "segment",
    })

    def __init__(self, root: LayoutNode, overlays=None):
        self.root = root
        self.overlays = overlays
        self._pressed: dict[tuple[str, int], LayoutNode] = {}
        self._hover: dict[tuple[str, int], LayoutNode] = {}
        self._touch_scroll: dict[tuple[str, int], LayoutNode] = {}
        self._touch_positions: dict[tuple[str, int], tuple[float, float]] = {}
        self.focused: LayoutNode | None = None
        self._had_modal = bool(overlays.has_modal) if overlays is not None else False
        self._modal_restore_focus: LayoutNode | None = None
        self._focus_history: list[LayoutNode] = []

    @property
    def has_capture(self) -> bool:
        return bool(self._pressed)

    def update_root(self, root: LayoutNode) -> None:
        """Adopt a reconciled root while preserving only live interaction state."""
        if not isinstance(root, LayoutNode):
            raise TypeError("dispatcher root must be a LayoutNode")
        self.root = root
        live = {id(node) for tree in self._roots() for node in self._walk(tree)}
        for mapping in (self._pressed, self._hover, self._touch_scroll):
            for key, node in tuple(mapping.items()):
                if id(node) not in live:
                    mapping.pop(key, None)
                    self._touch_positions.pop(key, None)
        # Do not retain detached nodes through the back-navigation history.
        self._focus_history = [node for node in self._focus_history if id(node) in live]
        if self._modal_restore_focus is not None and id(self._modal_restore_focus) not in live:
            self._modal_restore_focus = None
        self._normalize_focus()

    @staticmethod
    def _key(event):
        p = event.pointer
        return (p.source, p.pointer_id)

    @staticmethod
    def _invoke(node, name, event):
        callback = getattr(node, name, None) if node is not None else None
        if callback is not None:
            callback(event)
            return True
        return False

    @staticmethod
    def _walk(root):
        stack = [root]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def _roots(self):
        if self.overlays is not None:
            return self.overlays.focus_roots(self.root)
        return [self.root]

    def _focusables(self):
        result = []
        for root in self._roots():
            for node in self._walk(root):
                if node.accessibility_disabled:
                    continue
                role = (node.accessibility_role or "").lower()
                if (node.on_key_down is not None or node.on_text_input is not None
                        or (node.on_click is not None and role != "dialog-overlay")
                        or role in self.FOCUS_ROLES):
                    result.append(node)
        return result

    def _set_focus(self, node, *, remember=True):
        if node is self.focused:
            return
        previous = self.focused
        if remember and previous is not None and node is not None:
            self._focus_history.append(previous)
            self._focus_history = self._focus_history[-64:]
        self.focused = node
        if previous is not None:
            previous.accessibility_focused = False
            self._invoke(previous, "on_blur", None)
        if node is not None:
            node.accessibility_focused = True
            self._invoke(node, "on_focus", None)

    def _focus_from_target(self, target):
        if target is None:
            self._set_focus(None)
            return
        focusables = self._focusables()
        # A click on a text child inside a focusable wrapper focuses its nearest
        # focusable ancestor. Usually the target itself is the control node.
        parent = {}
        stack = list(self._roots())
        while stack:
            current = stack.pop()
            for child in current.children:
                parent[id(child)] = current
                stack.append(child)
        focusable_ids = {id(item) for item in focusables}
        current = target
        while current is not None:
            if id(current) in focusable_ids:
                self._set_focus(current)
                return
            current = parent.get(id(current))
        self._set_focus(None)

    def _normalize_focus(self):
        has_modal = bool(self.overlays is not None and self.overlays.has_modal)
        if has_modal and not self._had_modal:
            self._modal_restore_focus = self.focused
        restore = None
        if not has_modal and self._had_modal:
            restore = self._modal_restore_focus
            self._modal_restore_focus = None
        self._had_modal = has_modal
        focusables = self._focusables()
        if restore is not None and any(item is restore for item in focusables):
            self._set_focus(restore, remember=False)
            return
        if self.focused is not None and not any(item is self.focused for item in focusables):
            candidate = next((item for item in reversed(self._focus_history)
                              if any(item is valid for valid in focusables)), None)
            if candidate is not None:
                self._focus_history = [item for item in self._focus_history if item is not candidate]
            self._set_focus(candidate or (focusables[0] if focusables else None), remember=False)

    def _focus_first_in_root(self, root):
        focusables = []
        for node in self._walk(root):
            if node.accessibility_disabled:
                continue
            role = (node.accessibility_role or "").lower()
            if (node.on_key_down is not None or node.on_text_input is not None
                    or (node.on_click is not None and role != "dialog-overlay")
                    or role in self.FOCUS_ROLES):
                focusables.append(node)
        if focusables:
            self._set_focus(focusables[0])
            return True
        return False

    def _focus_adjacent_menu_item(self, direction):
        if self.focused is None:
            return False
        parent = {}
        menu_root = None
        stack = list(self._roots())
        while stack:
            current = stack.pop()
            if (current.accessibility_role or "").lower() == "menu":
                for child in current.children:
                    parent[id(child)] = current
                # Find the menu that contains the current focus node.
                descendants = {id(item) for item in self._walk(current)}
                if id(self.focused) in descendants:
                    menu_root = current
                    break
            for child in current.children:
                parent[id(child)] = current
                stack.append(child)
        if menu_root is None:
            return False
        items = [node for node in self._walk(menu_root)
                 if (node.accessibility_role or "").lower() == "menuitem"
                 and not node.accessibility_disabled and node.on_click is not None]
        if not items:
            return False
        index = next((i for i, node in enumerate(items) if node is self.focused), None)
        if index is None:
            index = 0 if direction > 0 else len(items) - 1
        else:
            index = (index + direction) % len(items)
        self._set_focus(items[index])
        return True

    def _focus_next(self, backwards=False):
        focusables = self._focusables()
        if not focusables:
            self._set_focus(None)
            return False
        index = next((i for i, item in enumerate(focusables) if item is self.focused), None)
        if index is None:
            index = 0 if backwards else -1
        next_index = (index - 1 if backwards else index + 1) % len(focusables)
        self._set_focus(focusables[next_index])
        return True

    def _scroll_ancestor(self, target):
        if target is None:
            return None
        if target.kind == "scroll":
            return target
        found = None

        def walk(node):
            nonlocal found
            if node is target:
                return True
            for child in node.children:
                if walk(child):
                    if node.kind == "scroll" and found is None:
                        found = node
                    return True
            return False

        for root in self._roots():
            if walk(root):
                break
        return found

    @staticmethod
    def _scroll_by(node, dx, dy):
        if node is None:
            return False
        old = (node.scroll_x, node.scroll_y)
        node.scroll_x = min(node.max_scroll_x, max(0.0, node.scroll_x + dx))
        node.scroll_y = min(node.max_scroll_y, max(0.0, node.scroll_y + dy))
        return old != (node.scroll_x, node.scroll_y)

    def dispatch(self, event: InputEvent) -> DispatchResult:
        if event.type == EventType.KEY_DOWN and event.key is not None:
            self._normalize_focus()
            key = event.key
            if key.keycode == SDLK_ESCAPE and self.overlays is not None:
                if self.overlays.handle_escape():
                    self._normalize_focus()
                    return DispatchResult(target=self.focused, handled=True)
            if key.keycode == SDLK_TAB:
                return DispatchResult(target=self.focused,
                                      handled=self._focus_next(bool(key.modifiers & KMOD_SHIFT)))
            if key.keycode in (SDLK_UP, SDLK_DOWN):
                direction = -1 if key.keycode == SDLK_UP else 1
                if self._focus_adjacent_menu_item(direction):
                    return DispatchResult(target=self.focused, handled=True)
            if self.focused is not None:
                handled = self._invoke(self.focused, "on_key_down", event)
                if not handled and key.keycode in (SDLK_RETURN, SDLK_SPACE):
                    handled = self._invoke(self.focused, "on_click", event)
                return DispatchResult(target=self.focused, handled=handled)
            return DispatchResult()

        if event.type in (EventType.TEXT_INPUT, EventType.TEXT_EDITING):
            self._normalize_focus()
            callback = "on_text_input" if event.type == EventType.TEXT_INPUT else "on_text_editing"
            handled = self._invoke(self.focused, callback, event)
            return DispatchResult(target=self.focused, handled=handled)

        if event.pointer is None:
            return DispatchResult()

        p = event.pointer
        key = self._key(event)
        overlay_entry = None
        target = None
        if self.overlays is not None:
            target, overlay_entry = self.overlays.hit_test(p.x, p.y)
        if target is None:
            if event.type == EventType.POINTER_DOWN and self.overlays is not None:
                if self.overlays.dismiss_outside(p.x, p.y):
                    target, overlay_entry = self.overlays.hit_test(p.x, p.y)
            if target is None:
                target = hit_test(self.root, p.x, p.y)
        previous = self._hover.get(key)

        if event.type == EventType.POINTER_MOTION:
            # During a drag, continue delivering motion to the captured node.
            captured = self._pressed.get(key)
            dispatch_target = captured or target
            if p.source == "touch" and key in self._touch_scroll:
                previous_pos = self._touch_positions.get(key, (p.x, p.y))
                dx = previous_pos[0] - p.x
                dy = previous_pos[1] - p.y
                self._scroll_by(self._touch_scroll[key], dx, dy)
                self._touch_positions[key] = (p.x, p.y)
            if captured is None and target is not previous:
                if previous:
                    self._invoke(previous, "on_pointer_leave", event)
                if target:
                    self._invoke(target, "on_pointer_enter", event)
                if target:
                    self._hover[key] = target
                else:
                    self._hover.pop(key, None)
            handled = self._invoke(dispatch_target, "on_pointer_move", event) if dispatch_target else False
            return DispatchResult(dispatch_target, previous, target, handled or target is not None)

        if event.type == EventType.POINTER_DOWN:
            if target:
                self._pressed[key] = target
            self._focus_from_target(target)
            if p.source == "touch":
                scroll = self._scroll_ancestor(target)
                if scroll is not None:
                    self._touch_scroll[key] = scroll
                    self._touch_positions[key] = (p.x, p.y)
            handled = self._invoke(target, "on_pointer_down", event) if target else False
            return DispatchResult(target, previous, previous, handled or target is not None)

        if event.type == EventType.POINTER_UP:
            pressed = self._pressed.pop(key, None)
            self._touch_scroll.pop(key, None)
            self._touch_positions.pop(key, None)
            handled = False
            if pressed is not None:
                handled = self._invoke(pressed, "on_pointer_up", event) or handled
            if target is not None and target is not pressed:
                handled = self._invoke(target, "on_pointer_up", event) or handled
            if target is not None and target is pressed:
                handled = self._invoke(target, "on_click", event) or handled
            return DispatchResult(target or pressed, previous, previous, handled or target is not None)

        if event.type == EventType.POINTER_WHEEL:
            scroll = self._scroll_ancestor(target)
            changed = self._scroll_by(scroll, -p.wheel_x * 40.0, -p.wheel_y * 40.0)
            handled = self._invoke(target, "on_wheel", event) if target else False
            return DispatchResult(target, previous, previous, handled or changed)

        return DispatchResult(target, previous, previous, False)

    def reset(self):
        self._pressed.clear()
        self._hover.clear()
        self._touch_scroll.clear()
        self._touch_positions.clear()
        self._focus_history.clear()
        self._modal_restore_focus = None
        self._had_modal = bool(self.overlays.has_modal) if self.overlays is not None else False
        self._set_focus(None, remember=False)
