"""SDL3 window + texture presentation backend, loaded dynamically with ctypes.

This module intentionally avoids a mandatory Python SDL binding. It talks to
the stable SDL3 C ABI and keeps SDL optional until a window is actually opened.
Frames passed to present() must be tightly packed RGBA8 bytes.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import platform
from dataclasses import dataclass
from typing import Callable


SDL_INIT_VIDEO = 0x00000020
SDL_WINDOW_RESIZABLE = 0x00000020
SDL_TEXTUREACCESS_STREAMING = 1
SDL_EVENT_QUIT = 0x100

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
        return events

    def poll_input_events(self):
        """Poll and decode raw SDL events into backend-neutral Yuktara UI events."""
        from .sdl3_events import SDL3EventDecoder

        decoder = SDL3EventDecoder()
        return [decoder.decode(event.raw) for event in self.poll_events()]

    def run(self, draw_frame: Callable[[], PixelFrame], *, on_event=None) -> None:
        """Run a basic frame loop until SDL_QUIT or the window is closed."""
        self.open()
        running = True
        try:
            while running:
                for event in self.poll_events():
                    if on_event is not None:
                        on_event(event)
                    if event.quit_requested:
                        running = False
                if running:
                    self.present(draw_frame())
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
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
