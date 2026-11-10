from __future__ import annotations

import ctypes
from threading import get_ident
from types import SimpleNamespace

import pytest

from novaui.native.platform.sdl3 import SDL3Window
from novaui.native.platform.events import EventType
from novaui.native.platform.sdl3_events import (
    SDL3EventDecoder,
    SDL_EVENT_WINDOW_DISPLAY_CHANGED,
    SDL_EVENT_WINDOW_DISPLAY_SCALE_CHANGED,
    SDL_EVENT_WINDOW_FOCUS_GAINED,
    SDL_EVENT_WINDOW_FOCUS_LOST,
)


class _Function:
    def __init__(self, callback):
        self.callback = callback
        self.restype = None
        self.argtypes = None

    def __call__(self, *args):
        return self.callback(*args)


def _write_int(pointer, value):
    ctypes.cast(pointer, ctypes.POINTER(ctypes.c_int)).contents.value = value


@pytest.mark.parametrize(
    "window_size,pixel_size,pixel_density,display_scale,expected_ui",
    [
        ((3840, 2160), (3840, 2160), 1.0, 2.0, (1920, 1080)),
        ((1920, 1080), (3840, 2160), 2.0, 2.0, (1920, 1080)),
        ((1920, 1080), (1920, 1080), 1.0, 1.0, (1920, 1080)),
    ],
)
def test_get_sizes_normalizes_high_dpi_platform_coordinates(
    window_size, pixel_size, pixel_density, display_scale, expected_ui
):
    library = SimpleNamespace(
        SDL_GetWindowSize=_Function(
            lambda _window, w, h: (
                _write_int(w, window_size[0]),
                _write_int(h, window_size[1]),
                True,
            )[-1]
        ),
        SDL_GetWindowSizeInPixels=_Function(
            lambda _window, w, h: (
                _write_int(w, pixel_size[0]),
                _write_int(h, pixel_size[1]),
                True,
            )[-1]
        ),
        SDL_GetWindowPixelDensity=_Function(lambda _window: pixel_density),
        SDL_GetWindowDisplayScale=_Function(lambda _window: display_scale),
    )
    window = SDL3Window()
    window._lib = library
    window._window = 7
    window._opened = True
    window._closed = False
    window._thread_id = get_ident()

    logical, pixels = window.get_sizes()

    assert logical == expected_ui
    assert pixels == pixel_size
    assert window.coordinate_scale == pytest.approx(display_scale / pixel_density)


def test_aspect_fit_uses_letterboxing_instead_of_stretching():
    rect = SDL3Window._aspect_fit_rect(1600, 900, 1200, 1200)

    assert rect == pytest.approx((0.0, 262.5, 1200.0, 675.0))
    assert rect[2] / rect[3] == pytest.approx(16 / 9)


def _window_event(event_type, window_id=9):
    class Event(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_uint32),
            ("reserved", ctypes.c_uint32),
            ("timestamp", ctypes.c_uint64),
            ("windowID", ctypes.c_uint32),
            ("data1", ctypes.c_int32),
            ("data2", ctypes.c_int32),
        ]

    event = Event()
    event.type = event_type
    event.timestamp = 77
    event.windowID = window_id
    raw = ctypes.string_at(ctypes.byref(event), ctypes.sizeof(event))
    return raw + bytes(128 - len(raw))


@pytest.mark.parametrize(
    "raw_type,expected",
    [
        (SDL_EVENT_WINDOW_DISPLAY_CHANGED, EventType.WINDOW_DISPLAY_CHANGED),
        (SDL_EVENT_WINDOW_DISPLAY_SCALE_CHANGED, EventType.WINDOW_DISPLAY_SCALE_CHANGED),
        (SDL_EVENT_WINDOW_FOCUS_GAINED, EventType.WINDOW_FOCUS_GAINED),
        (SDL_EVENT_WINDOW_FOCUS_LOST, EventType.WINDOW_FOCUS_LOST),
    ],
)
def test_sdl3_decoder_recognizes_display_scale_and_focus_events(raw_type, expected):
    decoded = SDL3EventDecoder().decode(_window_event(raw_type))
    assert decoded.type is expected
    assert decoded.window.window_id == 9



def test_poll_input_events_normalizes_mouse_and_window_coordinates():
    from novaui.native.platform.sdl3_events import (
        SDL_EVENT_MOUSE_MOTION,
        SDL_EVENT_WINDOW_RESIZED,
        _MouseMotion,
        _Window,
    )

    motion = _MouseMotion()
    motion.type = SDL_EVENT_MOUSE_MOTION
    motion.x = 100
    motion.y = 60
    motion.xrel = 20
    motion.yrel = 8
    resize = _Window()
    resize.type = SDL_EVENT_WINDOW_RESIZED
    resize.data1 = 1200
    resize.data2 = 800

    motion_raw = ctypes.string_at(ctypes.byref(motion), ctypes.sizeof(motion))
    resize_raw = ctypes.string_at(ctypes.byref(resize), ctypes.sizeof(resize))
    raw_events = [
        motion_raw + bytes(128 - len(motion_raw)),
        resize_raw + bytes(128 - len(resize_raw)),
    ]

    class PollEvent:
        def __init__(self):
            self.index = 0
            self.restype = None
            self.argtypes = None

        def __call__(self, destination):
            if self.index >= len(raw_events):
                return False
            ctypes.memmove(destination, raw_events[self.index], 128)
            self.index += 1
            return True

    window = SDL3Window()
    window._lib = SimpleNamespace(SDL_PollEvent=PollEvent())
    window._opened = True
    window._closed = False
    window._thread_id = get_ident()
    window._coordinate_scale = 2.0

    events = window.poll_input_events()

    assert events[0].pointer.x == pytest.approx(50)
    assert events[0].pointer.y == pytest.approx(30)
    assert events[0].pointer.delta_x == pytest.approx(10)
    assert events[0].pointer.delta_y == pytest.approx(4)
    assert (events[1].window.width, events[1].window.height) == (600, 400)
