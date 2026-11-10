"""SDL3 window + texture presentation backend, loaded dynamically with ctypes.

This module intentionally avoids a mandatory Python SDL binding. It talks to
the stable SDL3 C ABI and keeps SDL optional until a window is actually opened.
Frames passed to present() must be tightly packed RGBA8 bytes.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import platform
import threading
from time import perf_counter
from collections import deque
from dataclasses import dataclass
from typing import Callable, Sequence


SDL_INIT_VIDEO = 0x00000020
SDL_WINDOW_RESIZABLE = 0x00000020
SDL_TEXTUREACCESS_STREAMING = 1
SDL_EVENT_QUIT = 0x100


class _SDLDialogFileFilter(ctypes.Structure):
    _fields_ = [("name", ctypes.c_char_p), ("pattern", ctypes.c_char_p)]


_SDLDialogCallback = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int
)

def sys_byteorder_little() -> bool:
    return __import__("sys").byteorder == "little"


# SDL_PIXELFORMAT_RGBA32 is an alias for the byte-array order RGBA.
# SDL's packed pixel enum differs by host byte order.
SDL_PIXELFORMAT_RGBA32 = (
    0x16762004 if sys_byteorder_little() else 0x16462004
)


@dataclass(frozen=True, slots=True)
class PixelFrame:
    width: int
    height: int
    pixels: bytes
    row_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Frame dimensions must be positive.")
        stride = self.row_bytes if self.row_bytes is not None else self.width * 4
        if stride < self.width * 4:
            raise ValueError("RGBA row stride cannot be smaller than width * 4.")
        if len(self.pixels) != stride * self.height:
            raise ValueError(
                f"Expected {stride * self.height} pixel bytes, got {len(self.pixels)}."
            )
        object.__setattr__(self, "row_bytes", stride)


@dataclass(frozen=True, slots=True)
class SDLEvent:
    """Minimal normalized event. `raw_type` preserves SDL3 event identity."""

    raw_type: int
    quit_requested: bool = False
    raw: bytes = b""


class SDL3Error(RuntimeError):
    """Raised when SDL3 cannot initialize or complete an operation."""


class SDL3Window:
    """SDL3 window that presents RGBA frames through a streaming texture.

    SDL calls and presentation must remain on the thread that opens the window.
    The event API intentionally exposes raw SDL_Event bytes for the next input
    adapter layer; only the global quit event is normalized in this milestone.
    """

    def __init__(
        self,
        title: str = "Yuktara UI",
        width: int = 1100,
        height: int = 720,
        *,
        resizable: bool = True,
        library_path: str | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Window dimensions must be positive.")
        self.title = title
        self.width = width
        self.height = height
        self.resizable = resizable
        self.library_path = library_path
        self._lib = None
        self._window = None
        self._renderer = None
        self._texture = None
        self._opened = False
        self._closed = False
        self._thread_id = None
        self._dialog_lock = threading.Lock()
        self._dialog_results = deque()
        self._dialog_callbacks = {}
        self._next_dialog_token = 1

    def _load_library(self):
        if self._lib is not None:
            return self._lib

        # Preserve explicit paths, but verify the runtime is at the framework's
        # supported SDL3 baseline. Older system SDL builds are not silently used.
        if self.library_path:
            try:
                candidate = ctypes.CDLL(self.library_path)
                version_fn = candidate.SDL_GetVersion
                version_fn.restype = ctypes.c_int
                version_fn.argtypes = []
                version = int(version_fn())
                if version >= 3_004_020:
                    self._lib = candidate
                    return self._lib
            except (OSError, AttributeError, TypeError, ValueError):
                pass

        try:
            from ..dependencies import ensure_sdl3_runtime

            library_path = ensure_sdl3_runtime()
            self._lib = ctypes.CDLL(library_path)
            return self._lib
        except Exception as exc:
            raise SDL3Error(
                "Yuktara UI could not prepare SDL3 3.4.20 automatically. "
                "Check the network connection and, on Linux, ensure a C "
                "compiler/build toolchain is available. You can override the "
                f"library path with YUKTARA_UI_SDL3_LIBRARY. Details: {exc}"
            ) from exc

    def _bind(self, name, restype, argtypes):
        fn = getattr(self._lib, name)
        fn.restype = restype
        fn.argtypes = argtypes
        return fn

    def _error(self) -> str:
        try:
            self._bind("SDL_GetError", ctypes.c_char_p, []) 
            value = self._lib.SDL_GetError()
            return value.decode("utf-8", "replace") if value else "unknown SDL error"
        except Exception:
            return "unknown SDL error"

    def open(self) -> "SDL3Window":
        if self._opened:
            self._assert_open()
            return self
        if self._closed:
            raise SDL3Error("A closed SDL3Window cannot be reopened.")
        self._lib = self._load_library()
        self._thread_id = __import__("threading").get_ident()

        init = self._bind("SDL_Init", ctypes.c_bool, [ctypes.c_uint])
        if not init(SDL_INIT_VIDEO):
            raise SDL3Error(f"SDL_Init failed: {self._error()}")

        create_window = self._bind(
            "SDL_CreateWindow",
            ctypes.c_void_p,
            [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_uint64],
        )
        flags = SDL_WINDOW_RESIZABLE if self.resizable else 0
        self._window = create_window(
            self.title.encode("utf-8"), self.width, self.height, flags
        )
        if not self._window:
            self.close()
            raise SDL3Error(f"SDL_CreateWindow failed: {self._error()}")

        create_renderer = self._bind(
            "SDL_CreateRenderer",
            ctypes.c_void_p,
            [ctypes.c_void_p, ctypes.c_char_p],
        )
        self._renderer = create_renderer(self._window, None)
        if not self._renderer:
            self.close()
            raise SDL3Error(f"SDL_CreateRenderer failed: {self._error()}")

        self._opened = True
        return self

    def _assert_open(self) -> None:
        if not self._opened or self._closed:
            raise SDL3Error("Open the SDL3 window before using it.")
        current = __import__("threading").get_ident()
        if current != self._thread_id:
            raise SDL3Error("SDL window operations must run on the opening thread.")

    def _ensure_texture(self, width: int, height: int) -> None:
        if self._texture is not None and (width, height) == (
            self._texture_size[0], self._texture_size[1]
        ):
            return
        if self._texture is not None:
            self._bind("SDL_DestroyTexture", None, [ctypes.c_void_p])(self._texture)
            self._texture = None
        create_texture = self._bind(
            "SDL_CreateTexture",
            ctypes.c_void_p,
            [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
        )
        self._texture = create_texture(
            self._renderer,
            SDL_PIXELFORMAT_RGBA32,
            SDL_TEXTUREACCESS_STREAMING,
            width,
            height,
        )
        if not self._texture:
            raise SDL3Error(f"SDL_CreateTexture failed: {self._error()}")
        self._texture_size = (width, height)

    def start_text_input(self) -> None:
        """Activate SDL3 committed text input for this window."""
        self._assert_open()
        start = self._bind("SDL_StartTextInput", ctypes.c_bool, [ctypes.c_void_p])
        if not start(self._window):
            raise SDL3Error(f"SDL_StartTextInput failed: {self._error()}")

    def stop_text_input(self) -> None:
        """Deactivate SDL3 text input for this window."""
        self._assert_open()
        stop = self._bind("SDL_StopTextInput", ctypes.c_bool, [ctypes.c_void_p])
        if not stop(self._window):
            raise SDL3Error(f"SDL_StopTextInput failed: {self._error()}")

    def get_clipboard_text(self) -> str:
        """Read UTF-8 text from the OS clipboard through SDL3."""
        self._assert_open()
        getter = self._bind("SDL_GetClipboardText", ctypes.c_void_p, [])
        free = self._bind("SDL_free", None, [ctypes.c_void_p])
        pointer = getter()
        if not pointer:
            return ""
        try:
            return ctypes.string_at(pointer).decode("utf-8", "replace")
        finally:
            free(pointer)

    def set_clipboard_text(self, text: str) -> None:
        """Write UTF-8 text to the OS clipboard through SDL3."""
        self._assert_open()
        if not isinstance(text, str):
            raise TypeError("clipboard text must be a string")
        if "\0" in text:
            raise ValueError("clipboard text cannot contain a NUL character")
        setter = self._bind("SDL_SetClipboardText", ctypes.c_bool, [ctypes.c_char_p])
        if not setter(text.encode("utf-8")):
            raise SDL3Error(f"SDL_SetClipboardText failed: {self._error()}")

    # TextField accepts a clipboard service with get_text()/set_text().
    def get_text(self) -> str:
        return self.get_clipboard_text()

    def set_text(self, text: str) -> None:
        self.set_clipboard_text(text)

    def _start_file_dialog(self, function_name: str, callback: Callable,
                           filters: Sequence[tuple[str, str]] = (), *,
                           default_location: str | None = None,
                           allow_many: bool = False, folder: bool = False) -> None:
        """Start an SDL native file dialog and marshal completion to the UI thread."""
        self._assert_open()
        if not callable(callback):
            raise TypeError("file dialog callback must be callable")
        encoded_filters = []
        for item in filters:
            if (not isinstance(item, (tuple, list)) or len(item) != 2 or
                    not all(isinstance(value, str) and value for value in item)):
                raise ValueError("filters must be (display_name, extension_pattern) pairs")
            name, pattern = item
            if pattern != "*" and any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.;"
                                       for ch in pattern):
                raise ValueError("filter patterns may contain only extensions separated by semicolons")
            encoded_filters.append((name.encode("utf-8"), pattern.encode("utf-8")))
        filter_array = None
        if encoded_filters:
            filter_array = (_SDLDialogFileFilter * len(encoded_filters))(
                *[_SDLDialogFileFilter(name, pattern) for name, pattern in encoded_filters]
            )
        location = default_location.encode("utf-8") if default_location else None
        with self._dialog_lock:
            token = self._next_dialog_token
            self._next_dialog_token += 1
            # Keep the C callback, filter array and encoded strings alive until
            # SDL reports completion. The callback itself only queues data.
            def completed(_userdata, filelist, selected_filter):
                paths = None
                if filelist:
                    collected = []
                    for index in range(4096):
                        value = filelist[index]
                        if value is None:
                            break
                        collected.append(value.decode("utf-8", "replace"))
                    paths = tuple(collected)
                with self._dialog_lock:
                    pending = self._dialog_callbacks.pop(token, None)
                    if pending is not None:
                        self._dialog_results.append((pending[0], paths, int(selected_filter)))
            c_callback = _SDLDialogCallback(completed)
            self._dialog_callbacks[token] = (callback, c_callback, filter_array, encoded_filters)
        try:
            if folder:
                fn = self._bind(
                    function_name, None,
                    [_SDLDialogCallback, ctypes.c_void_p, ctypes.c_void_p,
                     ctypes.c_char_p, ctypes.c_bool],
                )
                fn(c_callback, None, self._window, location, bool(allow_many))
            else:
                fn = self._bind(
                    function_name, None,
                    [_SDLDialogCallback, ctypes.c_void_p, ctypes.c_void_p,
                     ctypes.POINTER(_SDLDialogFileFilter), ctypes.c_int,
                     ctypes.c_char_p] + ([ctypes.c_bool] if function_name.endswith("OpenFileDialog") else []),
                )
                fn(c_callback, None, self._window,
                   ctypes.cast(filter_array, ctypes.POINTER(_SDLDialogFileFilter)) if filter_array else None,
                   len(encoded_filters), location,
                   *([bool(allow_many)] if function_name.endswith("OpenFileDialog") else []))
        except Exception:
            with self._dialog_lock:
                self._dialog_callbacks.pop(token, None)
            raise

    def show_open_file_dialog(self, callback: Callable, *, filters=(),
                              default_location: str | None = None,
                              allow_many: bool = False) -> None:
        """Open an OS-native file dialog; callback receives (paths, filter_index).

        ``paths`` is ``None`` on an SDL error, an empty tuple on cancellation,
        or a tuple of UTF-8 paths after acceptance. Results are delivered only
        when :meth:`process_file_dialog_results` is called on the window thread.
        """
        self._start_file_dialog(
            "SDL_ShowOpenFileDialog", callback, filters,
            default_location=default_location, allow_many=allow_many,
        )

    def show_save_file_dialog(self, callback: Callable, *, filters=(),
                              default_location: str | None = None) -> None:
        """Open an OS-native save dialog; callback receives (paths, filter_index)."""
        self._start_file_dialog(
            "SDL_ShowSaveFileDialog", callback, filters,
            default_location=default_location,
        )

    def show_open_folder_dialog(self, callback: Callable, *,
                                default_location: str | None = None,
                                allow_many: bool = False) -> None:
        """Open an OS-native folder dialog; callback receives (paths, -1)."""
        self._start_file_dialog(
            "SDL_ShowOpenFolderDialog", callback,
            default_location=default_location, allow_many=allow_many, folder=True,
        )

    def process_file_dialog_results(self) -> int:
        """Deliver completed asynchronous file dialogs on the SDL window thread."""
        self._assert_open()
        results = []
        with self._dialog_lock:
            while self._dialog_results:
                results.append(self._dialog_results.popleft())
        for callback, paths, filter_index in results:
            callback(paths, filter_index)
        return len(results)

    def get_sizes(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """Return ``(logical_size, pixel_size)`` for the opened SDL window.

        SDL3 distinguishes window coordinates from the backing pixel size on
        high-DPI displays. If the pixel-size query is unavailable in a test
        double or older SDL build, the logical size is used as a safe fallback.
        """
        self._assert_open()
        logical_w = ctypes.c_int()
        logical_h = ctypes.c_int()
        self._bind(
            "SDL_GetWindowSize", None,
            [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
        )(self._window, ctypes.byref(logical_w), ctypes.byref(logical_h))
        logical = (int(logical_w.value), int(logical_h.value))
        pixel_w = ctypes.c_int(logical[0])
        pixel_h = ctypes.c_int(logical[1])
        try:
            self._bind(
                "SDL_GetWindowSizeInPixels", None,
                [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
            )(self._window, ctypes.byref(pixel_w), ctypes.byref(pixel_h))
        except AttributeError:
            pass
        if min(logical) <= 0 or min(pixel_w.value, pixel_h.value) <= 0:
            raise SDL3Error("SDL returned an invalid window or pixel size.")
        self.width, self.height = logical
        return logical, (int(pixel_w.value), int(pixel_h.value))

    def present(self, frame: PixelFrame) -> None:
        self._assert_open()
        self._ensure_texture(frame.width, frame.height)
        update = self._bind(
            "SDL_UpdateTexture",
            ctypes.c_bool,
            [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int],
        )
        pixel_buffer = ctypes.create_string_buffer(frame.pixels)
        if not update(
            self._texture, None, ctypes.cast(pixel_buffer, ctypes.c_void_p),
            int(frame.row_bytes)
        ):
            raise SDL3Error(f"SDL_UpdateTexture failed: {self._error()}")

        set_color = self._bind(
            "SDL_SetRenderDrawColor",
            ctypes.c_bool,
            [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8],
        )
        clear = self._bind("SDL_RenderClear", ctypes.c_bool, [ctypes.c_void_p])
        render_texture = self._bind(
            "SDL_RenderTexture",
            ctypes.c_bool,
            [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p],
        )
        present = self._bind("SDL_RenderPresent", None, [ctypes.c_void_p])
        if not set_color(self._renderer, 0, 0, 0, 255):
            raise SDL3Error(f"SDL_SetRenderDrawColor failed: {self._error()}")
        if not clear(self._renderer):
            raise SDL3Error(f"SDL_RenderClear failed: {self._error()}")
        if not render_texture(self._renderer, self._texture, None, None):
            raise SDL3Error(f"SDL_RenderTexture failed: {self._error()}")
        present(self._renderer)

    def poll_events(self) -> list[SDLEvent]:
        self._assert_open()
        # SDL_Event is a tagged union. SDL3 guarantees it is no larger than
        # 128 bytes; reading it as an opaque buffer keeps this layer ABI-safe.
        event_buffer = ctypes.create_string_buffer(128)
        poll = self._bind(
            "SDL_PollEvent", ctypes.c_bool, [ctypes.c_void_p]
        )
        events: list[SDLEvent] = []
        while poll(ctypes.cast(event_buffer, ctypes.c_void_p)):
            raw = bytes(event_buffer.raw)
            event_type = int.from_bytes(raw[:4], byteorder="little", signed=False)
            events.append(
                SDLEvent(
                    raw_type=event_type,
                    quit_requested=(event_type == SDL_EVENT_QUIT),
                    raw=raw,
                )
            )
        self.process_file_dialog_results()
        return events

    def poll_input_events(self):
        """Poll and decode raw SDL events into backend-neutral Yuktara UI events."""
        from .sdl3_events import SDL3EventDecoder

        decoder = SDL3EventDecoder()
        return [decoder.decode(event.raw) for event in self.poll_events()]

    def run(self, draw_frame: Callable[[], PixelFrame], *, on_event=None) -> None:
        """Run a raw SDL event/presentation loop until SDL_QUIT."""
        self.open()
        running = True
        try:
            while running:
                events = self.poll_events()
                for event in events:
                    if on_event is not None:
                        on_event(event)
                    if event.quit_requested:
                        running = False
                if running:
                    self.present(draw_frame())
                    if not events:
                        self._bind("SDL_Delay", None, [ctypes.c_uint32])(1)
        finally:
            self.close()

    def run_runtime(self, runtime, frame_provider: Callable, *,
                    on_event: Callable | None = None,
                    max_frames: int | None = None) -> None:
        """Drive a :class:`NativeRuntime` from the SDL3 window lifecycle.

        ``frame_provider(runtime)`` must return an RGBA :class:`PixelFrame`.
        This keeps pixel readback strategy injectable while SDL owns the event
        pump, logical/pixel resize synchronization, owner thread and teardown.
        ``max_frames`` is intended for deterministic smoke tests.
        """
        if not callable(frame_provider):
            raise TypeError("frame_provider must be callable")
        if max_frames is not None and max_frames < 1:
            raise ValueError("max_frames must be positive")
        self.open()
        runtime_started = False
        frame_count = 0
        previous = perf_counter()
        try:
            logical, pixels = self.get_sizes()
            runtime.resize(*logical, pixel_width=pixels[0], pixel_height=pixels[1])
            runtime.start()
            runtime_started = True
            running = True
            while running and not runtime.quit_requested:
                events = self.poll_input_events()
                for event in events:
                    if on_event is not None:
                        on_event(event)
                    if not runtime.handle_event(event):
                        running = False
                        break
                runtime.process_pending()
                now = perf_counter()
                runtime.advance_time(max(0.0, (now - previous) * 1000.0))
                previous = now
                if not running or runtime.quit_requested:
                    break
                frame = frame_provider(runtime)
                if not isinstance(frame, PixelFrame):
                    raise TypeError("frame_provider must return a PixelFrame")
                self.present(frame)
                frame_count += 1
                if max_frames is not None and frame_count >= max_frames:
                    break
                if not events:
                    self._bind("SDL_Delay", None, [ctypes.c_uint32])(1)
        finally:
            try:
                if runtime_started:
                    runtime.stop()
            finally:
                # Window resources must still be released if runtime teardown
                # encounters an application callback or renderer exception.
                self.close()

    def close(self) -> None:
        if self._closed:
            return
        # SDL window, renderer and texture destruction are thread-affine. A
        # partially opened window still records the thread that called open().
        if self._thread_id is not None and threading.get_ident() != self._thread_id:
            raise SDL3Error("SDL window resources must be closed on the opening thread.")
        if self._lib is not None:
            if self._texture:
                self._bind("SDL_DestroyTexture", None, [ctypes.c_void_p])(self._texture)
                self._texture = None
            if self._renderer:
                self._bind("SDL_DestroyRenderer", None, [ctypes.c_void_p])(self._renderer)
                self._renderer = None
            if self._window:
                self._bind("SDL_DestroyWindow", None, [ctypes.c_void_p])(self._window)
                self._window = None
            try:
                self._bind("SDL_Quit", None, [])()
            except AttributeError:
                pass
        self._opened = False
        self._closed = True

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
