"""Normalized input events shared by Yuktara UI platform backends."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    QUIT = auto()
    WINDOW_RESIZED = auto()
    WINDOW_PIXEL_SIZE_CHANGED = auto()
    WINDOW_FOCUS_GAINED = auto()
    WINDOW_FOCUS_LOST = auto()
    KEY_DOWN = auto()
    KEY_UP = auto()
    TEXT_INPUT = auto()
    POINTER_MOTION = auto()
    POINTER_DOWN = auto()
    POINTER_UP = auto()
    POINTER_WHEEL = auto()
    UNKNOWN = auto()


@dataclass(frozen=True, slots=True)
class KeyEvent:
    keycode: int
    scancode: int
    modifiers: int
    repeat: bool = False


@dataclass(frozen=True, slots=True)
class PointerEvent:
    x: float
    y: float
    button: int = 0
    buttons: int = 0
    clicks: int = 0
    delta_x: float = 0.0
    delta_y: float = 0.0
    wheel_x: float = 0.0
    wheel_y: float = 0.0
    pointer_id: int = 0
    source: str = "mouse"


@dataclass(frozen=True, slots=True)
class WindowEvent:
    width: int = 0
    height: int = 0
    window_id: int = 0


@dataclass(frozen=True, slots=True)
class InputEvent:
    type: EventType
    timestamp_ns: int = 0
    key: KeyEvent | None = None
    pointer: PointerEvent | None = None
    window: WindowEvent | None = None
    text: str | None = None
    raw_type: int = 0
