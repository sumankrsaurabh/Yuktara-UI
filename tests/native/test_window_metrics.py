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



def test_open_treats_initial_window_size_as_ui_units_on_high_dpi_windows():
    from novaui.native.platform.sdl3 import SDL_WINDOW_HIGH_PIXEL_DENSITY

    calls = {}
    current_size = [1100, 720]

    class FakeFunction:
        def __init__(self, callback):
            self.callback = callback
            self.restype = None
            self.argtypes = None

        def __call__(self, *args):
            return self.callback(*args)

    def write_size(_window, width_ptr, height_ptr):
        _write_int(width_ptr, current_size[0])
        _write_int(height_ptr, current_size[1])
        return True

    library = SimpleNamespace(
        SDL_SetHint=FakeFunction(lambda *_args: True),
        SDL_Init=FakeFunction(lambda *_args: True),
        SDL_CreateWindow=FakeFunction(
            lambda _title, width, height, flags: (
                calls.update(create=(width, height), flags=flags) or 101
            )
        ),
        SDL_GetWindowPixelDensity=FakeFunction(lambda _window: 1.0),
        SDL_GetWindowDisplayScale=FakeFunction(lambda _window: 2.0),
        SDL_SetWindowSize=FakeFunction(
            lambda _window, width, height: (
                calls.update(size=(width, height)),
                current_size.__setitem__(slice(None), [width, height]),
                True,
            )[-1]
        ),
        SDL_SyncWindow=FakeFunction(lambda _window: True),
        SDL_SetWindowMinimumSize=FakeFunction(
            lambda _window, width, height: calls.update(minimum=(width, height)) or True
        ),
        SDL_CreateRenderer=FakeFunction(lambda *_args: 202),
        SDL_GetWindowSize=FakeFunction(write_size),
        SDL_GetWindowSizeInPixels=FakeFunction(write_size),
        SDL_DestroyRenderer=FakeFunction(lambda *_args: None),
        SDL_DestroyWindow=FakeFunction(lambda *_args: None),
        SDL_Quit=FakeFunction(lambda *_args: None),
    )
    window = SDL3Window(width=1100, height=720)
    window._lib = library

    window.open()
    try:
        assert calls["create"] == (1100, 720)
        assert calls["flags"] & SDL_WINDOW_HIGH_PIXEL_DENSITY
        assert calls["size"] == (2200, 1440)
        assert calls["minimum"] == (640, 480)
        logical, pixels = window.get_sizes()
        assert logical == (1100, 720)
        assert pixels == (2200, 1440)
    finally:
        window.close()


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"width": 0}, ValueError),
        ({"height": -1}, ValueError),
        ({"width": True}, TypeError),
        ({"height": 720.5}, TypeError),
        ({"min_width": True}, TypeError),
        ({"min_height": -1}, ValueError),
        ({"resizable": 1}, TypeError),
    ],
)
def test_sdl3_window_rejects_invalid_dimension_and_flag_types(kwargs, error):
    with pytest.raises(error):
        SDL3Window(**kwargs)


def test_get_display_metrics_reads_active_resolution_and_fractional_refresh_rate():
    from novaui.native.platform.sdl3 import _SDLDisplayMode

    mode = _SDLDisplayMode()
    mode.displayID = 12
    mode.w = 2560
    mode.h = 1440
    mode.pixel_density = 1.5
    mode.refresh_rate = 143.97
    mode.refresh_rate_numerator = 143970
    mode.refresh_rate_denominator = 1000
    library = SimpleNamespace(
        SDL_GetDisplayForWindow=_Function(lambda _window: 12),
        SDL_GetCurrentDisplayMode=_Function(lambda _display: ctypes.pointer(mode)),
    )
    window = SDL3Window()
    window._lib = library
    window._window = 7
    window._opened = True
    window._closed = False
    window._thread_id = get_ident()

    metrics = window.get_display_metrics()

    assert metrics.display_id == 12
    assert (metrics.width, metrics.height) == (2560, 1440)
    assert metrics.pixel_density == pytest.approx(1.5)
    assert metrics.refresh_rate == pytest.approx(143.97)
    assert metrics.refresh_rate_numerator == 143970
    assert metrics.refresh_rate_denominator == 1000


@pytest.mark.parametrize("vsync", [-1, 0, 1, 2, 3])
def test_window_accepts_supported_vsync_intervals(vsync):
    assert SDL3Window(vsync=vsync).requested_vsync == vsync


@pytest.mark.parametrize("vsync,error", [(True, TypeError), (1.5, TypeError), (-2, ValueError)])
def test_window_rejects_invalid_vsync_intervals(vsync, error):
    with pytest.raises(error):
        SDL3Window(vsync=vsync)


def test_unsynchronized_loop_yields_but_vsync_loop_does_not_sleep():
    calls = []
    window = SDL3Window()
    window._lib = SimpleNamespace(SDL_Delay=_Function(lambda ms: calls.append(ms)))
    window.actual_vsync = 1
    window._idle_if_unsynchronized()
    assert calls == []

    window.actual_vsync = 0
    window._idle_if_unsynchronized()
    assert calls == [1]


def test_run_runtime_coalesces_resize_and_pixel_size_events(monkeypatch):
    from types import SimpleNamespace
    from novaui.native.platform.sdl3 import PixelFrame

    events = [
        SimpleNamespace(type=EventType.WINDOW_RESIZED, window=SimpleNamespace(width=900, height=650)),
        SimpleNamespace(type=EventType.WINDOW_PIXEL_SIZE_CHANGED, window=SimpleNamespace(width=1800, height=1300)),
    ]
    sync_calls = []
    monkeypatch.setattr(SDL3Window, "open", lambda self: self)
    monkeypatch.setattr(SDL3Window, "close", lambda self: None)
    monkeypatch.setattr(SDL3Window, "poll_input_events", lambda self: events)
    monkeypatch.setattr(SDL3Window, "sync_runtime_size", lambda self, runtime: sync_calls.append(runtime))
    monkeypatch.setattr(SDL3Window, "present", lambda self, frame: None)

    class Runtime:
        quit_requested = False

        def __init__(self):
            self.handled = []
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def handle_event(self, event):
            self.handled.append(event)
            return True

        def process_pending(self):
            pass

        def advance_time(self, _delta):
            pass

        def stop(self):
            self.stopped = True

    runtime = Runtime()
    window = SDL3Window()
    window.run_runtime(
        runtime,
        lambda _runtime: PixelFrame(1, 1, bytes((0, 0, 0, 255))),
        max_frames=1,
    )

    # One initial size synchronization plus exactly one coalesced resize-batch sync.
    assert sync_calls == [runtime, runtime]
    assert runtime.handled == []
    assert runtime.started and runtime.stopped
