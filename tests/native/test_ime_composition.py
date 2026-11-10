from __future__ import annotations

import ctypes
from threading import get_ident
from types import SimpleNamespace

from novaui.native import NativeRuntime, TextField
from novaui.native.platform.events import EventType, InputEvent, PointerEvent
from novaui.native.platform.sdl3 import SDL3Window
from novaui.native.platform.sdl3_events import (
    SDL3EventDecoder,
    SDL_EVENT_TEXT_EDITING,
)


class _SDLTextEditingEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("windowID", ctypes.c_uint32),
        ("text", ctypes.c_void_p),
        ("start", ctypes.c_int32),
        ("length", ctypes.c_int32),
    ]


def test_sdl3_text_editing_event_decodes_utf8_and_selection():
    composition = ctypes.create_string_buffer("かな".encode("utf-8"))
    event = _SDLTextEditingEvent()
    event.type = SDL_EVENT_TEXT_EDITING
    event.timestamp = 123456
    event.windowID = 9
    event.text = ctypes.cast(composition, ctypes.c_void_p)
    event.start = 1
    event.length = 1
    raw = ctypes.string_at(ctypes.byref(event), ctypes.sizeof(event)).ljust(128, b"\0")

    decoded = SDL3EventDecoder().decode(raw)

    assert decoded.type is EventType.TEXT_EDITING
    assert decoded.timestamp_ns == 123456
    assert decoded.text == "かな"
    assert decoded.text_start == 1
    assert decoded.text_length == 1


def test_text_field_shows_preedit_without_mutating_committed_value():
    field = TextField("hello")
    node = field.build()
    field._focus()
    field.anchor, field.cursor = 1, 4

    handled = field._text_editing(
        InputEvent(
            EventType.TEXT_EDITING,
            text="かな",
            text_start=1,
            text_length=1,
        )
    )

    assert handled is True
    assert field.value == "hello"
    assert node.text == "hかなo"
    assert node.text_composition == (1, 3)
    assert node.text_selection == (2, 3)
    assert node.text_cursor == 2


def test_committed_text_replaces_original_selection_after_composition():
    field = TextField("hello")
    node = field.build()
    field._focus()
    field.anchor, field.cursor = 1, 4
    field._text_editing(
        InputEvent(EventType.TEXT_EDITING, text="かな", text_start=2, text_length=0)
    )

    field._text_input(InputEvent(EventType.TEXT_INPUT, text="仮名"))

    assert field.value == "h仮名o"
    assert node.text == "h仮名o"
    assert node.text_composition is None
    assert node.text_cursor == 3


def test_escape_cancels_preedit_and_restores_original_selection():
    class Clipboard:
        def __init__(self):
            self.cleared = 0

        def clear_composition(self):
            self.cleared += 1

    clipboard = Clipboard()
    field = TextField("abc", clipboard=clipboard)
    node = field.build()
    field._focus()
    field.anchor, field.cursor = 1, 2
    field._text_editing(
        InputEvent(EventType.TEXT_EDITING, text="に", text_start=1, text_length=0)
    )

    handled = field._key_down(
        SimpleNamespace(key=SimpleNamespace(keycode=27, modifiers=0))
    )

    assert handled is True
    assert field.value == "abc"
    assert node.text == "abc"
    assert node.text_composition is None
    assert field.selection == (1, 2)
    assert clipboard.cleared == 1


def test_text_field_updates_native_ime_area_from_measured_caret():
    class Clipboard:
        def __init__(self):
            self.area = None

        def set_text_input_area(self, *values):
            self.area = values

    class Layout:
        line_height = 18

        class Line:
            height = 18

        lines = [Line()]

        @staticmethod
        def caret_position(_offset):
            return 42.0, 3.0, 0

    clipboard = Clipboard()
    field = TextField("sample", clipboard=clipboard)
    node = field.build()
    field._built_node = node
    field._focused = True
    field.cursor = 4
    node.content_bounds.x = 10
    node.content_bounds.y = 20
    node.content_bounds.width = 180
    node.content_bounds.height = 32
    node.text_layout = Layout()

    field._update_text_input_area(node)

    assert clipboard.area == (10, 23, 180, 18, 42)



def test_native_runtime_routes_text_editing_event_to_focused_text_field():
    class RecordingRenderer:
        size = SimpleNamespace(scale=1.0, scale_y=None)

        def clear(self, *_args, **_kwargs):
            pass

        def draw_rect(self, *_args, **_kwargs):
            pass

        def draw_stroke_rect(self, *_args, **_kwargs):
            pass

        def draw_text(self, *_args, **_kwargs):
            pass

    field = TextField("start")
    runtime = NativeRuntime(lambda: field.build(), RecordingRenderer(), 320, 120)
    runtime.start()
    try:
        runtime.dispatcher._set_focus(runtime.root)
        runtime.handle_event(
            InputEvent(
                EventType.TEXT_EDITING,
                text="かな",
                text_start=1,
                text_length=1,
            )
        )

        assert field.value == "start"
        assert runtime.root.text == "startかな"
        assert runtime.root.text_composition == (5, 7)
        assert runtime.frame_count >= 2
    finally:
        runtime.stop()



def test_sdl3_window_sets_candidate_area_using_window_coordinates():
    captured = {}

    class SDLFunction:
        restype = None
        argtypes = None

        def __call__(self, window, rect_pointer, cursor):
            class Rect(ctypes.Structure):
                _fields_ = [
                    ("x", ctypes.c_int),
                    ("y", ctypes.c_int),
                    ("w", ctypes.c_int),
                    ("h", ctypes.c_int),
                ]

            rect = ctypes.cast(rect_pointer, ctypes.POINTER(Rect)).contents
            captured.update(
                window=window,
                rect=(rect.x, rect.y, rect.w, rect.h),
                cursor=cursor,
            )
            return True

    window = SDL3Window()
    window._lib = SimpleNamespace(SDL_SetTextInputArea=SDLFunction())
    window._window = 77
    window._opened = True
    window._closed = False
    window._thread_id = get_ident()

    window.set_text_input_area(12, 34, 200, 24, 56)

    assert captured == {
        "window": 77,
        "rect": (12, 34, 200, 24),
        "cursor": 56,
    }



def test_text_input_service_is_independent_from_clipboard_service():
    class Clipboard:
        def get_text(self):
            return "from clipboard"

        def set_text(self, _value):
            return True

    class TextInputService:
        def __init__(self):
            self.started = 0
            self.stopped = 0
            self.cleared = 0

        def start_text_input(self):
            self.started += 1

        def stop_text_input(self):
            self.stopped += 1

        def clear_composition(self):
            self.cleared += 1

    clipboard = Clipboard()
    text_input = TextInputService()
    field = TextField("value", clipboard=clipboard, text_input=text_input)
    field.build()

    field._focus()
    field._blur()

    assert text_input.started == 1
    assert text_input.stopped == 1
    assert text_input.cleared == 1
    assert field._clipboard_get() == "from clipboard"



def test_sdl3_ime_candidate_area_scales_to_native_window_coordinates():
    captured = {}

    class SDLFunction:
        restype = None
        argtypes = None

        def __call__(self, window, rect_pointer, cursor):
            class Rect(ctypes.Structure):
                _fields_ = [
                    ("x", ctypes.c_int),
                    ("y", ctypes.c_int),
                    ("w", ctypes.c_int),
                    ("h", ctypes.c_int),
                ]

            rect = ctypes.cast(rect_pointer, ctypes.POINTER(Rect)).contents
            captured.update(
                rect=(rect.x, rect.y, rect.w, rect.h),
                cursor=cursor,
            )
            return True

    window = SDL3Window()
    window._lib = SimpleNamespace(SDL_SetTextInputArea=SDLFunction())
    window._window = 77
    window._opened = True
    window._closed = False
    window._thread_id = get_ident()
    window._coordinate_scale = 2.0

    window.set_text_input_area(12, 34, 200, 24, 56)

    assert captured == {
        "rect": (24, 68, 400, 48),
        "cursor": 112,
    }
