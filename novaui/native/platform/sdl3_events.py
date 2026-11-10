"""SDL3 event decoder.

SDL_Event is a C union with a 128-byte ABI size. The structs below intentionally
model only the stable common prefix and fields needed by Yuktara UI. SDL3's
event-specific numeric constants are declared here to avoid importing bindings.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass

from .events import (
    EventType, InputEvent, KeyEvent, PointerEvent, WindowEvent,
)

# SDL3 event type values from SDL_events.h.
SDL_EVENT_QUIT = 0x100
SDL_EVENT_WINDOW_RESIZED = 0x206
SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED = 0x207
SDL_EVENT_WINDOW_FOCUS_GAINED = 0x20B
SDL_EVENT_WINDOW_FOCUS_LOST = 0x20C
SDL_EVENT_KEY_DOWN = 0x300
SDL_EVENT_KEY_UP = 0x301
SDL_EVENT_TEXT_INPUT = 0x303
SDL_EVENT_MOUSE_MOTION = 0x400
SDL_EVENT_MOUSE_BUTTON_DOWN = 0x401
SDL_EVENT_MOUSE_BUTTON_UP = 0x402
SDL_EVENT_MOUSE_WHEEL = 0x403
SDL_EVENT_FINGER_DOWN = 0x700
SDL_EVENT_FINGER_UP = 0x701
SDL_EVENT_FINGER_MOTION = 0x702

SDL_EVENT_SIZE = 128


class _Common(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
    ]


class _Window(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("windowID", ctypes.c_uint32),
        ("data1", ctypes.c_int32),
        ("data2", ctypes.c_int32),
    ]


class _Keyboard(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("windowID", ctypes.c_uint32),
        ("which", ctypes.c_uint32),
        ("scancode", ctypes.c_int32),
        ("key", ctypes.c_int32),
        ("mod", ctypes.c_uint16),
        ("raw", ctypes.c_uint16),
        ("down", ctypes.c_bool),
        ("repeat", ctypes.c_bool),
    ]


class _TextInput(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("windowID", ctypes.c_uint32),
        ("text", ctypes.c_char * 32),
    ]


class _MouseMotion(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("windowID", ctypes.c_uint32),
        ("which", ctypes.c_uint32),
        ("state", ctypes.c_uint32),
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("xrel", ctypes.c_float),
        ("yrel", ctypes.c_float),
    ]


class _MouseButton(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("windowID", ctypes.c_uint32),
        ("which", ctypes.c_uint32),
        ("button", ctypes.c_uint8),
        ("down", ctypes.c_bool),
        ("clicks", ctypes.c_uint8),
        ("padding", ctypes.c_uint8),
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
    ]


class _TouchFinger(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("touchID", ctypes.c_int64),
        ("fingerID", ctypes.c_int64),
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("dx", ctypes.c_float),
        ("dy", ctypes.c_float),
        ("pressure", ctypes.c_float),
        ("windowID", ctypes.c_uint32),
    ]


class _MouseWheel(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("windowID", ctypes.c_uint32),
        ("which", ctypes.c_uint32),
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("direction", ctypes.c_uint32),
        ("mouse_x", ctypes.c_float),
        ("mouse_y", ctypes.c_float),
    ]


@dataclass(frozen=True, slots=True)
class SDL3EventDecoder:
    """Convert raw SDL_Event bytes into stable Yuktara UI InputEvent instances."""

    def decode(self, raw: bytes) -> InputEvent:
        if len(raw) < SDL_EVENT_SIZE:
            raise ValueError(f"SDL event buffer must be {SDL_EVENT_SIZE} bytes.")
        common = _Common.from_buffer_copy(raw)
        kind = int(common.type)
        timestamp = int(common.timestamp)

        if kind == SDL_EVENT_QUIT:
            return InputEvent(EventType.QUIT, timestamp, raw_type=kind)

        if kind in (SDL_EVENT_WINDOW_RESIZED, SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED):
            ev = _Window.from_buffer_copy(raw)
            return InputEvent(
                EventType.WINDOW_RESIZED if kind == SDL_EVENT_WINDOW_RESIZED
                else EventType.WINDOW_PIXEL_SIZE_CHANGED,
                timestamp,
                window=WindowEvent(ev.data1, ev.data2, ev.windowID),
                raw_type=kind,
            )

        if kind in (SDL_EVENT_WINDOW_FOCUS_GAINED, SDL_EVENT_WINDOW_FOCUS_LOST):
            ev = _Window.from_buffer_copy(raw)
            return InputEvent(
                EventType.WINDOW_FOCUS_GAINED if kind == SDL_EVENT_WINDOW_FOCUS_GAINED
                else EventType.WINDOW_FOCUS_LOST,
                timestamp,
                window=WindowEvent(window_id=ev.windowID),
                raw_type=kind,
            )

        if kind in (SDL_EVENT_KEY_DOWN, SDL_EVENT_KEY_UP):
            ev = _Keyboard.from_buffer_copy(raw)
            return InputEvent(
                EventType.KEY_DOWN if kind == SDL_EVENT_KEY_DOWN else EventType.KEY_UP,
                timestamp,
                key=KeyEvent(
                    keycode=ev.key,
                    scancode=ev.scancode,
                    modifiers=ev.mod,
                    repeat=bool(ev.repeat),
                ),
                raw_type=kind,
            )

        if kind == SDL_EVENT_TEXT_INPUT:
            ev = _TextInput.from_buffer_copy(raw)
            value = bytes(ev.text).split(b"\\0", 1)[0].decode("utf-8", "replace")
            return InputEvent(EventType.TEXT_INPUT, timestamp, text=value, raw_type=kind)

        if kind == SDL_EVENT_MOUSE_MOTION:
            ev = _MouseMotion.from_buffer_copy(raw)
            return InputEvent(
                EventType.POINTER_MOTION,
                timestamp,
                pointer=PointerEvent(
                    x=ev.x, y=ev.y, buttons=ev.state,
                    delta_x=ev.xrel, delta_y=ev.yrel, pointer_id=ev.which,
                ),
                raw_type=kind,
            )

        if kind in (SDL_EVENT_MOUSE_BUTTON_DOWN, SDL_EVENT_MOUSE_BUTTON_UP):
            ev = _MouseButton.from_buffer_copy(raw)
            return InputEvent(
                EventType.POINTER_DOWN if kind == SDL_EVENT_MOUSE_BUTTON_DOWN
                else EventType.POINTER_UP,
                timestamp,
                pointer=PointerEvent(
                    x=ev.x, y=ev.y, button=ev.button,
                    clicks=ev.clicks, pointer_id=ev.which,
                ),
                raw_type=kind,
            )

        if kind in (SDL_EVENT_FINGER_DOWN, SDL_EVENT_FINGER_UP, SDL_EVENT_FINGER_MOTION):
            ev = _TouchFinger.from_buffer_copy(raw)
            event_type = {
                SDL_EVENT_FINGER_DOWN: EventType.POINTER_DOWN,
                SDL_EVENT_FINGER_UP: EventType.POINTER_UP,
                SDL_EVENT_FINGER_MOTION: EventType.POINTER_MOTION,
            }[kind]
            # SDL touch coordinates are normalized to [0, 1], unlike mouse
            # coordinates. The adapter retains normalized values; layout/input
            # routing can scale them using the current logical window size.
            return InputEvent(
                event_type,
                timestamp,
                pointer=PointerEvent(
                    x=ev.x, y=ev.y, button=1 if kind == SDL_EVENT_FINGER_DOWN else 0,
                    delta_x=ev.dx, delta_y=ev.dy,
                    pointer_id=ev.fingerID, source="touch",
                ),
                raw_type=kind,
            )

        if kind == SDL_EVENT_MOUSE_WHEEL:
            ev = _MouseWheel.from_buffer_copy(raw)
            # SDL_MOUSEWHEEL_FLIPPED reverses the reported direction.
            sign = -1.0 if ev.direction == 1 else 1.0
            return InputEvent(
                EventType.POINTER_WHEEL,
                timestamp,
                pointer=PointerEvent(
                    x=ev.mouse_x, y=ev.mouse_y,
                    wheel_x=ev.x * sign, wheel_y=ev.y * sign,
                    pointer_id=ev.which,
                ),
                raw_type=kind,
            )

        return InputEvent(EventType.UNKNOWN, timestamp, raw_type=kind)
