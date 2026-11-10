"""SDL3 window + texture presentation backend, loaded dynamically with ctypes.

This module intentionally avoids a mandatory Python SDL binding. It talks to
the stable SDL3 C ABI and keeps SDL optional until a window is actually opened.
Frames passed to present() must be tightly packed RGBA8 bytes.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import platform
from math import isfinite
import threading
from time import perf_counter
from collections import deque
from dataclasses import dataclass
from typing import Callable, Sequence


SDL_INIT_VIDEO = 0x00000020
SDL_WINDOW_OPENGL = 0x00000002
SDL_WINDOW_RESIZABLE = 0x00000020
SDL_WINDOW_HIGH_PIXEL_DENSITY = 0x00002000
SDL_TEXTUREACCESS_STREAMING = 1
SDL_EVENT_QUIT = 0x100
SDL_RENDERER_VSYNC_DISABLED = 0
SDL_RENDERER_VSYNC_ADAPTIVE = -1
SDL_HINT_IME_IMPLEMENTED_UI = b"SDL_IME_IMPLEMENTED_UI"


class _SDLDialogFileFilter(ctypes.Structure):
    _fields_ = [("name", ctypes.c_char_p), ("pattern", ctypes.c_char_p)]


class _SDLRect(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("w", ctypes.c_int),
        ("h", ctypes.c_int),
    ]


class _SDLFRect(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("w", ctypes.c_float),
        ("h", ctypes.c_float),
    ]


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
class DisplayMetrics:
    """Current display characteristics for the monitor hosting a window."""

    display_id: int
    width: int
    height: int
    pixel_density: float
    refresh_rate: float
    refresh_rate_numerator: int = 0
    refresh_rate_denominator: int = 0


class _SDLDisplayMode(ctypes.Structure):
    _fields_ = [
        ("displayID", ctypes.c_uint32),
        ("format", ctypes.c_uint32),
        ("w", ctypes.c_int),
        ("h", ctypes.c_int),
        ("pixel_density", ctypes.c_float),
        ("refresh_rate", ctypes.c_float),
        ("refresh_rate_numerator", ctypes.c_int),
        ("refresh_rate_denominator", ctypes.c_int),
        ("internal", ctypes.c_void_p),
    ]


@dataclass(frozen=True, slots=True)
class SDLEvent:
    """Minimal normalized event. `raw_type` preserves SDL3 event identity."""

    raw_type: int
    quit_requested: bool = False
    raw: bytes = b""


class SDL3Error(RuntimeError):
    """Raised when SDL3 cannot initialize or complete an operation."""


class SDL3Window:
    """SDL3 window using either a streaming texture or an OpenGL context.

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
        high_dpi: bool = True,
        min_width: int = 320,
        min_height: int = 240,
        preserve_aspect: bool = True,
        vsync: int = 1,
        graphics_backend: str = "sdl",
        library_path: str | None = None,
    ) -> None:
        for name, value in (("width", width), ("height", height),
                            ("min_width", min_width), ("min_height", min_height)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if width <= 0 or height <= 0:
            raise ValueError("Window dimensions must be positive.")
        if min_width < 0 or min_height < 0 or (min_width == 0) != (min_height == 0):
            raise ValueError("minimum window dimensions must both be zero or positive")
        if not isinstance(resizable, bool):
            raise TypeError("resizable must be a boolean")
        if not isinstance(high_dpi, bool) or not isinstance(preserve_aspect, bool):
            raise TypeError("high_dpi and preserve_aspect must be booleans")
        if isinstance(vsync, bool) or not isinstance(vsync, int):
            raise TypeError("vsync must be an integer interval")
        if vsync < -1:
            raise ValueError("vsync must be -1 (adaptive), 0 (off), or a positive interval")
        if graphics_backend not in {"sdl", "opengl"}:
            raise ValueError("graphics_backend must be 'sdl' or 'opengl'")
        self.title = title
        self.width = width
        self.height = height
        self.resizable = resizable
        self.high_dpi = high_dpi
        self.min_width = min_width
        self.min_height = min_height
        self.preserve_aspect = preserve_aspect
        self.requested_vsync = vsync
        self.graphics_backend = graphics_backend
        self.actual_vsync: int | None = None
        self.display_metrics: DisplayMetrics | None = None
        self.letterbox_color = (0, 0, 0, 255)
        self.library_path = library_path
        self._coordinate_scale = 1.0
        self._pixel_density = 1.0
        self._display_scale = 1.0
        self._lib = None
        self._window = None
        self._renderer = None
        self._texture = None
        self._gl_context = None
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

        # The framework paints SDL text-editing pre-edit strings itself;
        # keep candidate-list presentation native to the operating system.
        try:
            set_hint = self._bind(
                "SDL_SetHint", ctypes.c_bool, [ctypes.c_char_p, ctypes.c_char_p]
            )
        except AttributeError:
            set_hint = None
        if set_hint is not None and not set_hint(
            SDL_HINT_IME_IMPLEMENTED_UI, b"composition"
        ):
            raise SDL3Error(f"SDL_SetHint for IME composition failed: {self._error()}")

        init = self._bind("SDL_Init", ctypes.c_bool, [ctypes.c_uint])
        if not init(SDL_INIT_VIDEO):
            raise SDL3Error(f"SDL_Init failed: {self._error()}")

        if self.graphics_backend == "opengl":
            set_gl_attribute = self._bind(
                "SDL_GL_SetAttribute", ctypes.c_bool, [ctypes.c_int, ctypes.c_int]
            )
            # SDL_GL_CONTEXT_MAJOR_VERSION=17, MINOR_VERSION=18,
            # PROFILE_MASK=21, CORE_PROFILE=1. Request a conservative 3.3 core
            # context supported by the Skia OpenGL backend.
            for attribute, value in ((17, 3), (18, 3), (21, 1), (5, 1)):
                if not set_gl_attribute(attribute, value):
                    error = self._error()
                    self.close()
                    raise SDL3Error(f"SDL_GL_SetAttribute({attribute}) failed: {error}")

        create_window = self._bind(
            "SDL_CreateWindow",
            ctypes.c_void_p,
            [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_uint64],
        )
        flags = SDL_WINDOW_RESIZABLE if self.resizable else 0
        if self.high_dpi:
            flags |= SDL_WINDOW_HIGH_PIXEL_DENSITY
        if self.graphics_backend == "opengl":
            flags |= SDL_WINDOW_OPENGL
        self._window = create_window(
            self.title.encode("utf-8"), self.width, self.height, flags
        )
        if not self._window:
            self.close()
            raise SDL3Error(f"SDL_CreateWindow failed: {self._error()}")
        if self.graphics_backend == "opengl":
            create_context = self._bind(
                "SDL_GL_CreateContext", ctypes.c_void_p, [ctypes.c_void_p]
            )
            self._gl_context = create_context(self._window)
            if not self._gl_context:
                self.close()
                raise SDL3Error(f"SDL_GL_CreateContext failed: {self._error()}")
            set_swap_interval = self._bind(
                "SDL_GL_SetSwapInterval", ctypes.c_bool, [ctypes.c_int]
            )
            if set_swap_interval(self.requested_vsync):
                self.actual_vsync = self.requested_vsync
            elif self.requested_vsync == -1 and set_swap_interval(1):
                self.actual_vsync = 1
            elif self.requested_vsync != 0 and set_swap_interval(0):
                self.actual_vsync = 0
            else:
                self.actual_vsync = None
        try:
            pixel_density = float(self._bind(
                "SDL_GetWindowPixelDensity", ctypes.c_float, [ctypes.c_void_p]
            )(self._window))
            display_scale = float(self._bind(
                "SDL_GetWindowDisplayScale", ctypes.c_float, [ctypes.c_void_p]
            )(self._window))
            if (isfinite(pixel_density) and pixel_density > 0
                    and isfinite(display_scale) and display_scale > 0):
                self._coordinate_scale = display_scale / pixel_density
        except AttributeError:
            pass

        # Width/height are public UI-unit dimensions. SDL window coordinates
        # are physical pixels on Windows/X11 but logical points on macOS/
        # Wayland, so convert the initial request using the same display scale.
        if self._coordinate_scale != 1.0:
            set_size = self._bind(
                "SDL_SetWindowSize", ctypes.c_bool,
                [ctypes.c_void_p, ctypes.c_int, ctypes.c_int],
            )
            if not set_size(
                self._window,
                round(self.width * self._coordinate_scale),
                round(self.height * self._coordinate_scale),
            ):
                self.close()
                raise SDL3Error(f"SDL_SetWindowSize failed: {self._error()}")
            try:
                sync_window = self._bind(
                    "SDL_SyncWindow", ctypes.c_bool, [ctypes.c_void_p]
                )
                sync_window(self._window)
            except AttributeError:
                pass

        if self.min_width and self.min_height:
            set_minimum = self._bind(
                "SDL_SetWindowMinimumSize", ctypes.c_bool,
                [ctypes.c_void_p, ctypes.c_int, ctypes.c_int],
            )
            if not set_minimum(
                self._window,
                round(self.min_width * self._coordinate_scale),
                round(self.min_height * self._coordinate_scale),
            ):
                self.close()
                raise SDL3Error(f"SDL_SetWindowMinimumSize failed: {self._error()}")

        if self.graphics_backend == "sdl":
            create_renderer = self._bind(
                "SDL_CreateRenderer",
                ctypes.c_void_p,
                [ctypes.c_void_p, ctypes.c_char_p],
            )
            self._renderer = create_renderer(self._window, None)
            if not self._renderer:
                self.close()
                raise SDL3Error(f"SDL_CreateRenderer failed: {self._error()}")

        # SDL renderers default to VSync disabled. Request synchronization with
        # the monitor's vertical refresh so presentation follows 60/90/120/144Hz
        # displays without a hard-coded frame-rate assumption. Drivers may
        # reject a mode; in that case retain a usable unsynchronized renderer.
        try:
            set_vsync = self._bind(
                "SDL_SetRenderVSync", ctypes.c_bool,
                [ctypes.c_void_p, ctypes.c_int],
            )
            if set_vsync(self._renderer, self.requested_vsync):
                self.actual_vsync = self.requested_vsync
            elif self.requested_vsync != SDL_RENDERER_VSYNC_DISABLED and set_vsync(
                self._renderer, SDL_RENDERER_VSYNC_DISABLED
            ):
                self.actual_vsync = SDL_RENDERER_VSYNC_DISABLED
        except AttributeError:
            self.actual_vsync = None

        self._opened = True
        try:
            self.display_metrics = self.get_display_metrics()
        except (AttributeError, SDL3Error):
            self.display_metrics = None
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

    def set_text_input_area(
        self, x: int, y: int, width: int, height: int, cursor: int = 0
    ) -> None:
        """Position the native IME candidate window near the current text caret.

        Coordinates are logical window coordinates as required by SDL3.
        The cursor is the horizontal offset from the input rectangle's x edge.
        """
        self._assert_open()
        values = (x, y, width, height, cursor)
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise TypeError("text input area coordinates and cursor must be integers")
        if width <= 0 or height <= 0 or cursor < 0:
            raise ValueError("text input area must have positive dimensions and a non-negative cursor")
        scale = self._coordinate_scale
        rect = _SDLRect(
            round(x * scale), round(y * scale),
            max(1, round(width * scale)), max(1, round(height * scale)),
        )
        set_area = self._bind(
            "SDL_SetTextInputArea", ctypes.c_bool,
            [ctypes.c_void_p, ctypes.POINTER(_SDLRect), ctypes.c_int],
        )
        if not set_area(self._window, ctypes.byref(rect), round(cursor * scale)):
            raise SDL3Error(f"SDL_SetTextInputArea failed: {self._error()}")

    def clear_composition(self) -> None:
        """Ask SDL3 to dismiss the active platform input-method composition."""
        self._assert_open()
        clear = self._bind("SDL_ClearComposition", ctypes.c_bool, [ctypes.c_void_p])
        if not clear(self._window):
            raise SDL3Error(f"SDL_ClearComposition failed: {self._error()}")

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

    @property
    def coordinate_scale(self) -> float:
        """Scale native window coordinates into device-independent UI units."""
        return self._coordinate_scale

    def get_sizes(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """Return UI logical dimensions and backing pixel dimensions.

        SDL window coordinates are physical pixels on some platforms and
        logical points on others. SDL display scale and pixel density are
        combined to normalize both cases into a stable UI coordinate space.
        The resulting renderer scale is the SDL window display scale.
        """
        self._assert_open()
        logical_w = ctypes.c_int()
        logical_h = ctypes.c_int()
        self._bind(
            "SDL_GetWindowSize", ctypes.c_bool,
            [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
        )(self._window, ctypes.byref(logical_w), ctypes.byref(logical_h))
        window_size = (int(logical_w.value), int(logical_h.value))

        pixel_w = ctypes.c_int(window_size[0])
        pixel_h = ctypes.c_int(window_size[1])
        try:
            get_pixel_size = self._bind(
                "SDL_GetWindowSizeInPixels", ctypes.c_bool,
                [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
            )
            result = get_pixel_size(
                self._window, ctypes.byref(pixel_w), ctypes.byref(pixel_h)
            )
            if result is False:
                pixel_w.value, pixel_h.value = window_size
        except AttributeError:
            # Older SDL test doubles/custom hosts may expose logical size only.
            pixel_w.value, pixel_h.value = window_size
        pixel_size = (int(pixel_w.value), int(pixel_h.value))
        if min(*window_size, *pixel_size) <= 0:
            raise SDL3Error("SDL returned an invalid window or pixel size.")

        try:
            get_pixel_density = self._bind(
                "SDL_GetWindowPixelDensity", ctypes.c_float, [ctypes.c_void_p]
            )
            pixel_density = float(get_pixel_density(self._window))
        except AttributeError:
            pixel_density = pixel_size[0] / window_size[0]
        try:
            get_display_scale = self._bind(
                "SDL_GetWindowDisplayScale", ctypes.c_float, [ctypes.c_void_p]
            )
            display_scale = float(get_display_scale(self._window))
        except AttributeError:
            display_scale = pixel_density
        if not isfinite(pixel_density) or pixel_density <= 0:
            pixel_density = pixel_size[0] / window_size[0]
        if not isfinite(display_scale) or display_scale <= 0:
            display_scale = pixel_density
        coordinate_scale = display_scale / pixel_density
        if not isfinite(coordinate_scale) or coordinate_scale <= 0:
            coordinate_scale = 1.0

        self._pixel_density = pixel_density
        self._display_scale = display_scale
        self._coordinate_scale = coordinate_scale
        ui_size = (
            max(1, round(window_size[0] / coordinate_scale)),
            max(1, round(window_size[1] / coordinate_scale)),
        )
        self.width, self.height = ui_size
        return ui_size, pixel_size

    def get_display_metrics(self) -> DisplayMetrics:
        """Return the active monitor's current resolution and refresh rate.

        The refresh rate is informational: SDL's renderer VSync controls
        presentation cadence and automatically follows the active display.
        """
        self._assert_open()
        get_display = self._bind(
            "SDL_GetDisplayForWindow", ctypes.c_uint32, [ctypes.c_void_p]
        )
        display_id = int(get_display(self._window))
        if display_id == 0:
            raise SDL3Error(f"SDL_GetDisplayForWindow failed: {self._error()}")
        get_mode = self._bind(
            "SDL_GetCurrentDisplayMode", ctypes.POINTER(_SDLDisplayMode),
            [ctypes.c_uint32],
        )
        mode = get_mode(display_id)
        if not mode:
            raise SDL3Error(f"SDL_GetCurrentDisplayMode failed: {self._error()}")
        value = mode.contents
        metrics = DisplayMetrics(
            display_id=display_id,
            width=int(value.w),
            height=int(value.h),
            pixel_density=float(value.pixel_density),
            refresh_rate=float(value.refresh_rate),
            refresh_rate_numerator=int(value.refresh_rate_numerator),
            refresh_rate_denominator=int(value.refresh_rate_denominator),
        )
        if (metrics.width <= 0 or metrics.height <= 0
                or not isfinite(metrics.refresh_rate) or metrics.refresh_rate < 0
                or not isfinite(metrics.pixel_density) or metrics.pixel_density <= 0):
            raise SDL3Error("SDL returned invalid active display metrics.")
        self.display_metrics = metrics
        return metrics

    def sync_runtime_size(self, runtime) -> None:
        """Synchronize logical layout, backing pixels and active display metrics."""
        logical, pixels = self.get_sizes()
        runtime.resize(
            *logical, pixel_width=pixels[0], pixel_height=pixels[1]
        )
        try:
            self.get_display_metrics()
        except (AttributeError, SDL3Error):
            # Display metadata is diagnostic; logical/pixel resize must still
            # succeed on older SDL builds and injected window test doubles.
            self.display_metrics = None

    @staticmethod
    def _aspect_fit_rect(
        frame_width: int, frame_height: int, output_width: int, output_height: int
    ) -> tuple[float, float, float, float]:
        """Return a centered destination rectangle without distorting a frame."""
        if min(frame_width, frame_height, output_width, output_height) <= 0:
            raise ValueError("frame and output dimensions must be positive")
        scale = min(output_width / frame_width, output_height / frame_height)
        width = frame_width * scale
        height = frame_height * scale
        return (
            (output_width - width) / 2,
            (output_height - height) / 2,
            width,
            height,
        )

    def present(self, frame: PixelFrame) -> None:
        self._assert_open()
        if self.graphics_backend != "sdl":
            raise SDL3Error("present(PixelFrame) is only available with graphics_backend='sdl'.")
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
            [ctypes.c_void_p, ctypes.c_void_p,
             ctypes.POINTER(_SDLFRect), ctypes.POINTER(_SDLFRect)],
        )
        present = self._bind("SDL_RenderPresent", None, [ctypes.c_void_p])
        if not set_color(self._renderer, *self.letterbox_color):
            raise SDL3Error(f"SDL_SetRenderDrawColor failed: {self._error()}")
        if not clear(self._renderer):
            raise SDL3Error(f"SDL_RenderClear failed: {self._error()}")

        destination = None
        if self.preserve_aspect:
            output_width = ctypes.c_int()
            output_height = ctypes.c_int()
            get_output_size = self._bind(
                "SDL_GetRenderOutputSize", ctypes.c_bool,
                [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
            )
            if not get_output_size(
                self._renderer, ctypes.byref(output_width), ctypes.byref(output_height)
            ):
                raise SDL3Error(f"SDL_GetRenderOutputSize failed: {self._error()}")
            x, y, width, height = self._aspect_fit_rect(
                frame.width, frame.height, output_width.value, output_height.value
            )
            destination_rect = _SDLFRect(x, y, width, height)
            destination = ctypes.byref(destination_rect)

        if not render_texture(self._renderer, self._texture, None, destination):
            raise SDL3Error(f"SDL_RenderTexture failed: {self._error()}")
        present(self._renderer)

    def create_gpu_renderer(self, *, skia_module=None):
        """Create a Skia surface that draws directly into this window's GL backbuffer."""
        self._assert_open()
        if self.graphics_backend != "opengl" or not self._gl_context:
            raise SDL3Error("Open the window with graphics_backend='opengl' first.")
        width = ctypes.c_int()
        height = ctypes.c_int()
        get_pixels = self._bind(
            "SDL_GetWindowSizeInPixels", ctypes.c_bool,
            [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
        )
        if not get_pixels(self._window, ctypes.byref(width), ctypes.byref(height)):
            raise SDL3Error(f"SDL_GetWindowSizeInPixels failed: {self._error()}")
        from ..renderer import RenderSize
        from ..gpu import SkiaGpuRenderer
        logical_width = max(1, self.width)
        logical_height = max(1, self.height)
        size = RenderSize(
            logical_width, logical_height,
            scale=width.value / logical_width,
            scale_y=height.value / logical_height,
        )
        return SkiaGpuRenderer(size, skia_module=skia_module, framebuffer=True)

    def present_gpu(self, renderer) -> None:
        """Submit a direct-framebuffer Skia frame and swap the SDL OpenGL window."""
        self._assert_open()
        if self.graphics_backend != "opengl" or not self._gl_context:
            raise SDL3Error("present_gpu requires graphics_backend='opengl'.")
        if getattr(renderer, "backend", None) != "opengl" or not getattr(renderer, "framebuffer", False):
            raise TypeError("renderer must be a framebuffer-backed SkiaGpuRenderer.")
        renderer.flush()
        swap = self._bind("SDL_GL_SwapWindow", ctypes.c_bool, [ctypes.c_void_p])
        if not swap(self._window):
            raise SDL3Error(f"SDL_GL_SwapWindow failed: {self._error()}")

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
        """Poll SDL events and normalize pointer/window coordinates to UI units."""
        from dataclasses import replace
        from .events import EventType
        from .sdl3_events import SDL3EventDecoder

        decoder = SDL3EventDecoder()
        decoded = []
        for raw_event in self.poll_events():
            event = decoder.decode(raw_event.raw)
            if event.type in {
                EventType.WINDOW_PIXEL_SIZE_CHANGED,
                EventType.WINDOW_DISPLAY_CHANGED,
                EventType.WINDOW_DISPLAY_SCALE_CHANGED,
            }:
                self.get_sizes()
                # A backing-size transition can accompany a desktop mode or
                # refresh change even when the window remains on the same display.
                try:
                    self.get_display_metrics()
                except AttributeError:
                    pass
            coordinate_scale = self._coordinate_scale
            if event.type == EventType.WINDOW_RESIZED and event.window is not None:
                event = replace(
                    event,
                    window=replace(
                        event.window,
                        width=max(1, round(event.window.width / coordinate_scale)),
                        height=max(1, round(event.window.height / coordinate_scale)),
                    ),
                )
            elif event.pointer is not None and event.pointer.source != "touch":
                event = replace(
                    event,
                    pointer=replace(
                        event.pointer,
                        x=event.pointer.x / coordinate_scale,
                        y=event.pointer.y / coordinate_scale,
                        delta_x=event.pointer.delta_x / coordinate_scale,
                        delta_y=event.pointer.delta_y / coordinate_scale,
                    ),
                )
            decoded.append(event)
        return decoded

    def _idle_if_unsynchronized(self) -> None:
        """Yield only when VSync is unavailable; a synced present is the frame clock."""
        if self.actual_vsync in (None, SDL_RENDERER_VSYNC_DISABLED):
            self._bind("SDL_Delay", None, [ctypes.c_uint32])(1)

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
                        self._idle_if_unsynchronized()
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
            self.sync_runtime_size(runtime)
            runtime.start()
            runtime_started = True
            running = True
            while running and not runtime.quit_requested:
                events = self.poll_input_events()
                from .events import EventType
                metrics_dirty = False
                display_changed = False
                metrics_events = {
                    EventType.WINDOW_RESIZED,
                    EventType.WINDOW_PIXEL_SIZE_CHANGED,
                    EventType.WINDOW_DISPLAY_CHANGED,
                    EventType.WINDOW_DISPLAY_SCALE_CHANGED,
                }
                for event in events:
                    if on_event is not None:
                        on_event(event)
                    if event.type in metrics_events:
                        # Coalesce every resize/DPI/display event in this SDL
                        # batch. Query the final window metrics once, then do
                        # one surface recreation and one layout/render pass.
                        metrics_dirty = True
                        display_changed = display_changed or event.type in {
                            EventType.WINDOW_DISPLAY_CHANGED,
                            EventType.WINDOW_DISPLAY_SCALE_CHANGED,
                        }
                        continue
                    if not runtime.handle_event(event):
                        running = False
                        break
                if running and metrics_dirty:
                    self.sync_runtime_size(runtime)
                if running and display_changed:
                    # Re-apply after monitor migration; drivers can differ.
                    try:
                        set_vsync = self._bind(
                            "SDL_SetRenderVSync", ctypes.c_bool,
                            [ctypes.c_void_p, ctypes.c_int],
                        )
                        if set_vsync(self._renderer, self.requested_vsync):
                            self.actual_vsync = self.requested_vsync
                        elif self.requested_vsync != SDL_RENDERER_VSYNC_DISABLED and set_vsync(
                            self._renderer, SDL_RENDERER_VSYNC_DISABLED
                        ):
                            self.actual_vsync = SDL_RENDERER_VSYNC_DISABLED
                        else:
                            self.actual_vsync = None
                    except AttributeError:
                        self.actual_vsync = None
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
                    self._idle_if_unsynchronized()
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
            if self._gl_context:
                self._bind("SDL_GL_DestroyContext", ctypes.c_bool, [ctypes.c_void_p])(self._gl_context)
                self._gl_context = None
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
