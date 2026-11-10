"""Orchestration layer joining component, layout, paint and native input."""
from __future__ import annotations

from dataclasses import replace
from math import isfinite
from threading import get_ident

from .layout import LayoutEngine, Rect
from .rendering import LayoutTreePainter
from .platform.dispatcher import InputDispatcher
from .reactivity import Component, Scheduler
from .text import TextMeasurer
from .renderer import RenderSize, SkiaRenderer
from .platform.events import EventType
from .overlays import OverlayManager
from .animations import AnimationManager, AnimationHandle


def _positive_finite_dimension(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite positive number")
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return number


def _positive_integer_dimension(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be a positive integer")
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


class NativeRuntime:
    """Own one native component tree and its UI-thread lifecycle.

    Layout and input coordinates are expressed in logical window pixels.
    Touch events from SDL3 are normalized to [0, 1] and converted here. Pixel
    dimensions and device scale are tracked separately so a high-DPI surface
    can be resized without changing component layout coordinates.
    """

    def __init__(self, build, renderer, width: float, height: float, *,
                 scheduler: Scheduler | None = None, clear_color="#FFFFFF",
                 text_measurer: TextMeasurer | None = None,
                 reduced_motion: bool = False):
        width = _positive_finite_dimension(width, "runtime width")
        height = _positive_finite_dimension(height, "runtime height")
        self.width = width
        self.height = height
        self.renderer = renderer
        self.clear_color = clear_color
        renderer_size = getattr(renderer, "size", None)
        self.scale_x = float(getattr(renderer_size, "scale", 1.0))
        self.scale_y = float(getattr(renderer_size, "scale_y", None) or self.scale_x)
        self.pixel_width = int(round(self.width * self.scale_x))
        self.pixel_height = int(round(self.height * self.scale_y))
        if text_measurer is None and isinstance(renderer, SkiaRenderer):
            text_measurer = TextMeasurer(renderer._skia, renderer._fonts)
        self.layout_engine = LayoutEngine(text_measurer=text_measurer)
        self.painter = LayoutTreePainter(renderer)
        self.scheduler = scheduler or Scheduler()
        self.component = Component(build, scheduler=self.scheduler,
                                   on_invalidate=self._component_changed)
        self.overlays = OverlayManager(on_change=self._overlay_changed)
        self.overlay_manager = self.overlays
        self.animations = AnimationManager(on_change=self._animation_changed,
                                           reduced_motion=reduced_motion)
        self.animation_manager = self.animations
        self._last_overlay_handle = None
        self._known_overlay_handles = set()
        self.dispatcher = None
        self.frame_count = 0
        self.reconcile_count = 0
        self._rendering = False
        self._dispatching = False
        self._pending_render = False
        self._owner_thread_id: int | None = None
        self._started = False
        self.quit_requested = False
        self.window_focused = True

    @property
    def root(self):
        return self.component.node

    @property
    def owner_thread_id(self):
        return self._owner_thread_id

    def _assert_owner_thread(self):
        if self._owner_thread_id is not None and get_ident() != self._owner_thread_id:
            raise RuntimeError("native runtime operations must run on its UI owner thread")

    def start(self):
        if self._started:
            self._assert_owner_thread()
            return self
        if self._owner_thread_id is not None and get_ident() != self._owner_thread_id:
            raise RuntimeError("a stopped native runtime must be restarted on its original UI thread")
        owner_thread_id = get_ident()
        # Binding can fail when an application supplies a scheduler already
        # owned by another thread. Do not leave the runtime half-initialized.
        self.scheduler.bind_owner_thread(owner_thread_id)
        self._owner_thread_id = owner_thread_id
        # stop() detaches callbacks; restore them for a same-thread restart.
        self.overlays.on_change = self._overlay_changed
        self.animations.on_change = self._animation_changed
        self.quit_requested = False
        self.window_focused = True
        self._started = True
        try:
            self.component.mount()
        except Exception:
            self.component.unmount()
            if self.dispatcher is not None:
                self.dispatcher.reset()
            self.dispatcher = None
            self._started = False
            raise
        return self

    def _component_changed(self, component):
        self._assert_owner_thread()
        if component.node is not None:
            if self.dispatcher is None:
                self.dispatcher = InputDispatcher(component.node, overlays=self.overlays)
            else:
                # Keep focus, hover, pointer capture and scroll gestures when a
                # state-driven build reconciles to retained nodes in place.
                self.dispatcher.update_root(component.node)
        if self._dispatching or self._rendering:
            self._pending_render = True
        else:
            self.render()

    def _overlay_changed(self):
        self._assert_owner_thread()
        if self.root is None:
            return
        current_entries = self.overlays.entries
        current_handles = {entry.handle for entry in current_entries}
        newly_added = [entry for entry in current_entries
                       if entry.handle not in self._known_overlay_handles]
        if self.dispatcher is not None:
            self.dispatcher._normalize_focus()
            if newly_added and newly_added[-1].kind in {"dialog", "context_menu"}:
                self.dispatcher._focus_first_in_root(newly_added[-1].root)
        self._known_overlay_handles = current_handles
        self._last_overlay_handle = self.overlays.top.handle if self.overlays.top else None
        if self._dispatching or self._rendering:
            self._pending_render = True
        else:
            self.render()

    def _animation_changed(self):
        self._assert_owner_thread()
        if self.root is None:
            return
        if self._dispatching or self._rendering:
            self._pending_render = True
        else:
            self.render()

    def animate(self, target, attribute: str, to_value, *, duration_ms=220,
                easing="ease_in_out", on_complete=None) -> AnimationHandle:
        """Animate a numeric property and repaint on each host-clock update."""
        self._assert_owner_thread()
        return self.animations.animate(
            target, attribute, to_value, duration_ms=duration_ms,
            easing=easing, on_complete=on_complete,
        )

    def set_reduced_motion(self, enabled: bool):
        self._assert_owner_thread()
        self.animations.set_reduced_motion(enabled)

    def render(self):
        self._assert_owner_thread()
        if self.root is None:
            return
        if self._rendering:
            self._pending_render = True
            return
        self._rendering = True
        passes = 0
        try:
            # A callback may invalidate the component while a frame is being
            # painted. Consume that invalidation in another bounded pass rather
            # than accidentally clearing the pending-render flag.
            while True:
                self._pending_render = False
                self.layout_engine.layout(self.root, Rect(0, 0, self.width, self.height))
                self.overlays.layout(self.layout_engine, self.width, self.height)
                self.painter.paint(self.root, clear_color=self.clear_color)
                for entry in self.overlays.entries:
                    self.painter.paint(entry.root)
                self.frame_count += 1
                passes += 1
                if not self._pending_render or passes >= 8:
                    break
        finally:
            self._rendering = False

    def process_pending(self) -> int:
        """Apply cross-thread invalidations on the UI thread and render them."""
        self._assert_owner_thread()
        flushed = self.scheduler.flush()
        if self._pending_render and not self._rendering and self.root is not None:
            self.render()
        return flushed

    def _normalize_input_event(self, event):
        pointer = event.pointer
        if pointer is None or pointer.source != "touch":
            return event
        # SDL_FingerEvent positions and deltas are normalized fractions of the
        # logical window dimensions. All other pointer sources use logical px.
        scaled = replace(
            pointer,
            x=pointer.x * self.width,
            y=pointer.y * self.height,
            delta_x=pointer.delta_x * self.width,
            delta_y=pointer.delta_y * self.height,
        )
        return replace(event, pointer=scaled)

    def dispatch(self, event):
        self._assert_owner_thread()
        if self.dispatcher is None:
            return None
        event = self._normalize_input_event(event)
        self._dispatching = True
        try:
            result = self.dispatcher.dispatch(event)
        finally:
            self._dispatching = False
        pointer = event.pointer
        should_render = self._pending_render
        if pointer is not None:
            should_render = should_render or event.type in {
                EventType.POINTER_UP, EventType.POINTER_WHEEL
            }
            should_render = should_render or (
                event.type == EventType.POINTER_MOTION and
                (pointer.source == "touch" or self.dispatcher.has_capture)
            )
        elif event.type in {EventType.KEY_DOWN, EventType.TEXT_INPUT, EventType.TEXT_EDITING}:
            should_render = True
        if should_render:
            self._pending_render = False
            if self.dispatcher is not None:
                self.dispatcher._normalize_focus()
            self.render()
        return result

    def handle_event(self, event):
        """Handle a normalized SDL/backend event and return whether to continue."""
        self._assert_owner_thread()
        if event.type == EventType.QUIT:
            self.quit_requested = True
            return False
        if event.type == EventType.WINDOW_RESIZED and event.window is not None:
            if event.window.width > 0 and event.window.height > 0:
                self.resize(event.window.width, event.window.height)
            return True
        if event.type == EventType.WINDOW_PIXEL_SIZE_CHANGED and event.window is not None:
            if event.window.width > 0 and event.window.height > 0:
                self.resize(self.width, self.height,
                            pixel_width=event.window.width,
                            pixel_height=event.window.height)
            return True
        if event.type == EventType.WINDOW_FOCUS_LOST:
            self.window_focused = False
            if self.dispatcher is not None:
                self.dispatcher.reset()
            self.render()
            return True
        if event.type == EventType.WINDOW_FOCUS_GAINED:
            self.window_focused = True
            return True
        if event.type in {
            EventType.KEY_DOWN, EventType.KEY_UP, EventType.TEXT_INPUT,
            EventType.TEXT_EDITING,
            EventType.POINTER_MOTION, EventType.POINTER_DOWN,
            EventType.POINTER_UP, EventType.POINTER_WHEEL,
        }:
            self.dispatch(event)
        return True

    def advance_time(self, delta_ms: float):
        """Advance animations and timed overlays by a host-supplied delta."""
        self._assert_owner_thread()
        self.animations.advance_time(delta_ms)
        return self.overlays.advance_time(delta_ms)

    def resize(self, width: float, height: float, *,
               pixel_width: int | None = None,
               pixel_height: int | None = None):
        """Resize logical layout and optionally update the backing pixel size.

        Dimensions are validated before mutating runtime state. A failed resize
        therefore leaves the previous logical and backing sizes intact.
        """
        self._assert_owner_thread()
        width = _positive_finite_dimension(width, "runtime width")
        height = _positive_finite_dimension(height, "runtime height")

        if pixel_width is None:
            pixel_width = max(1, int(round(width * self.scale_x)))
        else:
            pixel_width = _positive_integer_dimension(pixel_width, "pixel width")
        if pixel_height is None:
            pixel_height = max(1, int(round(height * self.scale_y)))
        else:
            pixel_height = _positive_integer_dimension(pixel_height, "pixel height")
        pixel_width = _positive_integer_dimension(pixel_width, "pixel width")
        pixel_height = _positive_integer_dimension(pixel_height, "pixel height")

        scale_x = pixel_width / width
        scale_y = pixel_height / height
        self.width = width
        self.height = height
        self.pixel_width = pixel_width
        self.pixel_height = pixel_height
        self.scale_x = scale_x
        self.scale_y = scale_y
        if isinstance(self.renderer, SkiaRenderer):
            self.renderer.resize(RenderSize(
                max(1, int(round(self.width))),
                max(1, int(round(self.height))),
                self.scale_x,
                self.scale_y,
            ))
        self.render()

    def stop(self):
        self._assert_owner_thread()
        if not self._started and self.component.node is None:
            return
        if self.dispatcher is not None:
            self.dispatcher.reset()
        self.dispatcher = None
        self.overlays.on_change = None
        self.overlays.dismiss_all(reason="runtime-stop")
        self.animations.cancel_all()
        self.animations.on_change = None
        self.component.unmount()
        self._known_overlay_handles.clear()
        self._last_overlay_handle = None
        self._pending_render = False
        self._started = False
