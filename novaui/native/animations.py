"""Deterministic, host-clock-driven animation primitives for native widgets.

No timers or worker threads are created. The application host advances time
through ``NativeRuntime.advance_time`` and the runtime repaints when animated
properties change.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import count
import math
from typing import Callable


@dataclass(frozen=True, slots=True)
class AnimationHandle:
    id: int


@dataclass
class _Animation:
    handle: AnimationHandle
    target: object
    attribute: str
    start: float
    end: float
    duration_ms: float
    elapsed_ms: float
    easing: Callable[[float], float]
    on_complete: Callable | None = None


class AnimationManager:
    """Interpolate numeric object properties using an explicit host clock."""

    EASINGS = {
        "linear": lambda t: t,
        "ease_in": lambda t: t * t,
        "ease_out": lambda t: 1 - (1 - t) * (1 - t),
        "ease_in_out": lambda t: 3 * t * t - 2 * t * t * t,
        "ease_out_cubic": lambda t: 1 - (1 - t) ** 3,
    }

    def __init__(self, *, on_change: Callable | None = None,
                 reduced_motion: bool = False):
        self._ids = count(1)
        self._animations: list[_Animation] = []
        self.on_change = on_change
        self.reduced_motion = bool(reduced_motion)

    @property
    def active_count(self) -> int:
        return len(self._animations)

    @property
    def handles(self) -> tuple[AnimationHandle, ...]:
        return tuple(item.handle for item in self._animations)

    def _changed(self):
        if self.on_change is not None:
            self.on_change()

    @staticmethod
    def _number(value, label):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{label} must be an int or float")
        if not math.isfinite(float(value)):
            raise ValueError(f"{label} must be finite")
        return float(value)

    def animate(self, target, attribute: str, to_value, *, duration_ms: float = 220,
                easing: str = "ease_in_out", on_complete: Callable | None = None
                ) -> AnimationHandle:
        """Animate ``target.attribute`` to a numeric value.

        A new animation for the same target/property replaces the previous
        one without firing its completion callback.
        """
        if target is None or not isinstance(attribute, str) or not attribute:
            raise ValueError("target and a non-empty attribute name are required")
        if not hasattr(target, attribute):
            raise AttributeError(f"{type(target).__name__} has no attribute {attribute!r}")
        start = self._number(getattr(target, attribute), "starting value")
        end = self._number(to_value, "to_value")
        if attribute == "opacity" and not 0.0 <= end <= 1.0:
            raise ValueError("opacity animation targets must be between 0 and 1")
        duration = self._number(duration_ms, "duration_ms")
        if duration < 0:
            raise ValueError("duration_ms must be non-negative")
        if easing not in self.EASINGS:
            raise ValueError(f"easing must be one of {sorted(self.EASINGS)}")
        if on_complete is not None and not callable(on_complete):
            raise TypeError("on_complete must be callable")

        self._animations = [
            item for item in self._animations
            if not (item.target is target and item.attribute == attribute)
        ]
        handle = AnimationHandle(next(self._ids))
        if self.reduced_motion or duration == 0 or start == end:
            setattr(target, attribute, end)
            self._changed()
            if on_complete is not None:
                on_complete()
            return handle
        self._animations.append(_Animation(
            handle, target, attribute, start, end, duration, 0.0,
            self.EASINGS[easing], on_complete,
        ))
        return handle

    def cancel(self, handle: AnimationHandle, *, finish: bool = False) -> bool:
        item = next((entry for entry in self._animations if entry.handle == handle), None)
        if item is None:
            return False
        self._animations.remove(item)
        if finish:
            setattr(item.target, item.attribute, item.end)
            self._changed()
            if item.on_complete is not None:
                item.on_complete()
        return True

    def cancel_all(self) -> int:
        """Discard every active animation without applying final values."""
        count = len(self._animations)
        self._animations.clear()
        return count

    def set_reduced_motion(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.reduced_motion:
            return
        self.reduced_motion = enabled
        if enabled:
            self.finish_all()

    def finish_all(self) -> int:
        items, self._animations = self._animations, []
        for item in items:
            setattr(item.target, item.attribute, item.end)
        if items:
            self._changed()
        for item in items:
            if item.on_complete is not None:
                item.on_complete()
        return len(items)

    def advance_time(self, delta_ms: float) -> int:
        delta = self._number(delta_ms, "delta_ms")
        if delta < 0:
            raise ValueError("delta_ms must be non-negative")
        if not self._animations or delta == 0:
            return 0
        completed = []
        changed = 0
        for item in tuple(self._animations):
            item.elapsed_ms = min(item.duration_ms, item.elapsed_ms + delta)
            progress = item.elapsed_ms / item.duration_ms
            eased = item.easing(progress)
            value = item.start + (item.end - item.start) * eased
            if progress >= 1:
                value = item.end
                completed.append(item)
            setattr(item.target, item.attribute, value)
            changed += 1
        for item in completed:
            if item in self._animations:
                self._animations.remove(item)
        if changed:
            self._changed()
        for item in completed:
            if item.on_complete is not None:
                item.on_complete()
        return changed


__all__ = ["AnimationHandle", "AnimationManager"]
