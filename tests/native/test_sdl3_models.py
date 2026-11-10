import pytest

from novaui.native.platform.sdl3 import PixelFrame, SDLEvent, SDL_EVENT_QUIT


def test_pixel_frame_accepts_tightly_packed_rgba():
    frame = PixelFrame(2, 2, bytes(16))
    assert frame.row_bytes == 8


def test_pixel_frame_accepts_padded_rows():
    frame = PixelFrame(1, 2, bytes(12), row_bytes=6)
    assert frame.row_bytes == 6


@pytest.mark.parametrize(
    "width,height,pixels,row_bytes",
    [
        (0, 1, b"", None),
        (1, 1, b"abc", None),
        (2, 1, bytes(8), 7),
        (1, 2, bytes(7), 4),
    ],
)
def test_pixel_frame_rejects_invalid_buffers(width, height, pixels, row_bytes):
    with pytest.raises(ValueError):
        PixelFrame(width, height, pixels, row_bytes)


def test_quit_event_model():
    event = SDLEvent(SDL_EVENT_QUIT, quit_requested=True)
    assert event.quit_requested


def test_sdl3_window_exposes_utf8_clipboard_service():
    import ctypes
    import threading
    from novaui.native.platform.sdl3 import SDL3Window

    window = SDL3Window()
    buffer = ctypes.create_string_buffer("युकतारा UI".encode("utf-8"))
    written = []
    freed = []

    class FakeLibrary:
        pass

    fake = FakeLibrary()
    fake.SDL_GetClipboardText = lambda: ctypes.addressof(buffer)
    fake.SDL_free = lambda pointer: freed.append(pointer)
    fake.SDL_SetClipboardText = lambda value: written.append(value) or True
    window._lib = fake
    window._opened = True
    window._thread_id = threading.get_ident()
    assert window.get_text() == "युकतारा UI"
    window.set_text("दस्तावेज")
    assert written == ["दस्तावेज".encode("utf-8")]
    assert freed


def test_sdl3_clipboard_rejects_nul_and_non_string_values():
    import threading
    from novaui.native.platform.sdl3 import SDL3Window

    window = SDL3Window()
    window._opened = True
    window._thread_id = threading.get_ident()
    with pytest.raises(TypeError):
        window.set_text(123)
    with pytest.raises(ValueError):
        window.set_text("bad\0text")


def test_sdl3_window_starts_and_stops_committed_text_input():
    import ctypes
    import threading
    from novaui.native.platform.sdl3 import SDL3Window

    window = SDL3Window()
    calls = []

    class FakeLibrary:
        pass

    fake = FakeLibrary()
    fake.SDL_StartTextInput = lambda target: calls.append(("start", target)) or True
    fake.SDL_StopTextInput = lambda target: calls.append(("stop", target)) or True
    window._lib = fake
    window._opened = True
    window._thread_id = threading.get_ident()
    window._window = 77
    window.start_text_input()
    window.stop_text_input()
    assert calls == [("start", 77), ("stop", 77)]


def test_sdl3_window_reports_logical_and_high_dpi_pixel_sizes():
    import ctypes
    import threading
    from novaui.native.platform.sdl3 import SDL3Window

    def write_size(width, height):
        def callback(_window, width_ptr, height_ptr):
            ctypes.cast(width_ptr, ctypes.POINTER(ctypes.c_int))[0] = width
            ctypes.cast(height_ptr, ctypes.POINTER(ctypes.c_int))[0] = height
        return callback

    class FakeLibrary:
        pass

    fake = FakeLibrary()
    fake.SDL_GetWindowSize = write_size(1280, 720)
    fake.SDL_GetWindowSizeInPixels = write_size(2560, 1440)
    window = SDL3Window()
    window._lib = fake
    window._opened = True
    window._thread_id = threading.get_ident()
    window._window = 5

    logical, pixels = window.get_sizes()

    assert logical == (1280, 720)
    assert pixels == (2560, 1440)
    assert (window.width, window.height) == logical


def test_sdl3_window_pixel_size_falls_back_to_logical_dimensions():
    import ctypes
    import threading
    from novaui.native.platform.sdl3 import SDL3Window

    class FakeLibrary:
        pass

    def logical_size(_window, width_ptr, height_ptr):
        ctypes.cast(width_ptr, ctypes.POINTER(ctypes.c_int))[0] = 800
        ctypes.cast(height_ptr, ctypes.POINTER(ctypes.c_int))[0] = 600

    fake = FakeLibrary()
    fake.SDL_GetWindowSize = logical_size
    window = SDL3Window()
    window._lib = fake
    window._opened = True
    window._thread_id = threading.get_ident()
    window._window = 5

    assert window.get_sizes() == ((800, 600), (800, 600))


def test_sdl3_run_runtime_starts_handles_quit_and_stops_runtime():
    from novaui.native.platform.events import EventType, InputEvent
    from novaui.native.platform.sdl3 import SDL3Window
    from novaui.native.runtime import NativeRuntime
    from novaui.native.layout import LayoutNode

    class FakeRenderer:
        def clear(self, color):
            pass
        def draw_rect(self, *args, **kwargs):
            pass
        def draw_text(self, *args, **kwargs):
            pass

    class FakeWindow(SDL3Window):
        def __init__(self):
            super().__init__(width=100, height=80)
            self.did_close = False
        def open(self):
            self._opened = True
            return self
        def get_sizes(self):
            return (100, 80), (200, 160)
        def poll_input_events(self):
            return [InputEvent(EventType.QUIT)]
        def close(self):
            self.did_close = True
            self._opened = False

    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 100, 80)
    window = FakeWindow()
    window.run_runtime(runtime, lambda _runtime: None)

    assert runtime.root is None  # runtime.stop() unmounted the component
    assert runtime.quit_requested is True
    assert window.did_close is True


def test_run_runtime_closes_window_even_when_runtime_stop_raises():
    from novaui.native.platform.sdl3 import SDL3Window
    from novaui.native.runtime import NativeRuntime
    from novaui.native.layout import LayoutNode
    from novaui.native.platform.events import EventType, InputEvent

    window = SDL3Window("test", 80, 60)
    closed = []
    window.open = lambda: window
    window.get_sizes = lambda: ((80, 60), (80, 60))
    window.poll_input_events = lambda: [InputEvent(EventType.QUIT)]
    window.close = lambda: closed.append(True)

    class FakeRenderer:
        def clear(self, color): pass
        def draw_rect(self, *args, **kwargs): pass
        def draw_text(self, *args, **kwargs): pass

    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 80, 60)
    original_stop = runtime.stop

    def failing_stop():
        original_stop()
        raise RuntimeError("simulated teardown failure")

    runtime.stop = failing_stop
    with pytest.raises(RuntimeError, match="simulated teardown failure"):
        window.run_runtime(runtime, lambda _runtime: None)
    assert closed == [True]


def test_sdl3_window_rejects_close_from_non_owner_thread():
    import threading
    from novaui.native.platform.sdl3 import SDL3Error, SDL3Window

    window = SDL3Window()
    window._opened = True
    window._thread_id = threading.get_ident()
    errors = []

    def close_from_worker():
        try:
            window.close()
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=close_from_worker)
    worker.start()
    worker.join()

    assert len(errors) == 1
    assert isinstance(errors[0], SDL3Error)
    assert "opening thread" in str(errors[0])
    assert window._closed is False


def test_sdl3_open_on_already_open_window_checks_thread_affinity():
    import threading
    from novaui.native.platform.sdl3 import SDL3Error, SDL3Window

    window = SDL3Window()
    window._opened = True
    window._thread_id = threading.get_ident()
    errors = []

    def open_from_worker():
        try:
            window.open()
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=open_from_worker)
    worker.start()
    worker.join()

    assert len(errors) == 1
    assert isinstance(errors[0], SDL3Error)
    assert "opening thread" in str(errors[0])


def test_run_runtime_presents_frames_with_negotiated_high_dpi_dimensions():
    import threading
    from novaui.native.platform.events import EventType
    from novaui.native.platform.sdl3 import PixelFrame, SDL3Window
    from novaui.native.runtime import NativeRuntime
    from novaui.native.layout import LayoutNode

    class FakeRenderer:
        def clear(self, color): pass
        def draw_rect(self, *args, **kwargs): pass
        def draw_text(self, *args, **kwargs): pass

    class FakeWindow(SDL3Window):
        def __init__(self):
            super().__init__(width=80, height=60)
            self.presented = []
            self.did_close = False

        def open(self):
            self._opened = True
            self._thread_id = threading.get_ident()
            return self

        def get_sizes(self):
            return (80, 60), (160, 120)

        def poll_input_events(self):
            return []

        def present(self, frame):
            self.presented.append(frame)

        def close(self):
            self.did_close = True
            self._opened = False
            self._closed = True

    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 20, 20)
    window = FakeWindow()
    frame = PixelFrame(2, 2, bytes(16))
    window.run_runtime(runtime, lambda _runtime: frame, max_frames=1)

    assert len(window.presented) == 1
    assert window.presented[0] is frame
    assert runtime.pixel_width == 160
    assert runtime.pixel_height == 120
    assert runtime.scale_x == 2.0
    assert runtime.scale_y == 2.0
    assert runtime.root is None
    assert window.did_close is True


def test_run_runtime_tears_down_when_frame_provider_returns_invalid_value():
    import threading
    import pytest
    from novaui.native.platform.sdl3 import SDL3Window
    from novaui.native.runtime import NativeRuntime
    from novaui.native.layout import LayoutNode

    class FakeRenderer:
        def clear(self, color): pass
        def draw_rect(self, *args, **kwargs): pass
        def draw_text(self, *args, **kwargs): pass

    class FakeWindow(SDL3Window):
        def __init__(self):
            super().__init__(width=80, height=60)
            self.did_close = False

        def open(self):
            self._opened = True
            self._thread_id = threading.get_ident()
            return self

        def get_sizes(self):
            return (80, 60), (80, 60)

        def poll_input_events(self):
            return []

        def close(self):
            self.did_close = True
            self._opened = False
            self._closed = True

    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 80, 60)
    window = FakeWindow()
    with pytest.raises(TypeError, match="PixelFrame"):
        window.run_runtime(runtime, lambda _runtime: b"not a frame", max_frames=1)

    assert runtime.root is None
    assert window.did_close is True
