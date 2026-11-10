import ctypes

from novaui.native.platform.events import EventType
from novaui.native.platform.sdl3_events import (
    SDL3EventDecoder, SDL_EVENT_KEY_DOWN, SDL_EVENT_MOUSE_MOTION,
    SDL_EVENT_MOUSE_WHEEL, SDL_EVENT_QUIT, SDL_EVENT_TEXT_INPUT,
    SDL_EVENT_WINDOW_RESIZED, SDL_EVENT_FINGER_MOTION,
    _Keyboard, _MouseMotion, _MouseWheel, _TextInput, _TouchFinger, _Window,
)


def raw_event(struct):
    data = bytearray(128)
    data[:ctypes.sizeof(struct)] = bytes(struct)
    return bytes(data)


def test_quit_event():
    event = SDL3EventDecoder().decode(raw_event(type("Quit", (), {
        "__bytes__": lambda self: b""
    })())) if False else SDL3EventDecoder().decode(
        (SDL_EVENT_QUIT).to_bytes(4, "little") + bytes(124)
    )
    assert event.type is EventType.QUIT


def test_window_resize_event():
    ev = _Window()
    ev.type = SDL_EVENT_WINDOW_RESIZED
    ev.windowID = 7
    ev.data1 = 1280
    ev.data2 = 800
    decoded = SDL3EventDecoder().decode(raw_event(ev))
    assert decoded.type is EventType.WINDOW_RESIZED
    assert decoded.window.width == 1280
    assert decoded.window.height == 800


def test_key_down_event():
    ev = _Keyboard()
    ev.type = SDL_EVENT_KEY_DOWN
    ev.key = 97
    ev.scancode = 4
    ev.mod = 3
    ev.repeat = True
    decoded = SDL3EventDecoder().decode(raw_event(ev))
    assert decoded.type is EventType.KEY_DOWN
    assert decoded.key.keycode == 97
    assert decoded.key.repeat


def test_text_input_event():
    ev = _TextInput()
    ev.type = SDL_EVENT_TEXT_INPUT
    ev.text = b"hello"
    decoded = SDL3EventDecoder().decode(raw_event(ev))
    assert decoded.type is EventType.TEXT_INPUT
    assert decoded.text == "hello"


def test_mouse_motion_event():
    ev = _MouseMotion()
    ev.type = SDL_EVENT_MOUSE_MOTION
    ev.x, ev.y = 22.5, 44.0
    ev.xrel, ev.yrel = 1.5, -2.0
    ev.state = 1
    decoded = SDL3EventDecoder().decode(raw_event(ev))
    assert decoded.type is EventType.POINTER_MOTION
    assert decoded.pointer.x == 22.5
    assert decoded.pointer.delta_y == -2.0


def test_mouse_wheel_event():
    ev = _MouseWheel()
    ev.type = SDL_EVENT_MOUSE_WHEEL
    ev.x, ev.y = 1.0, 2.0
    ev.mouse_x, ev.mouse_y = 10.0, 20.0
    decoded = SDL3EventDecoder().decode(raw_event(ev))
    assert decoded.type is EventType.POINTER_WHEEL
    assert decoded.pointer.wheel_y == 2.0


def test_touch_motion_event_uses_normalized_coordinates():
    ev = _TouchFinger()
    ev.type = SDL_EVENT_FINGER_MOTION
    ev.fingerID = 1234
    ev.x, ev.y = 0.25, 0.75
    ev.dx, ev.dy = 0.05, -0.1
    decoded = SDL3EventDecoder().decode(raw_event(ev))
    assert decoded.type is EventType.POINTER_MOTION
    assert decoded.pointer.source == "touch"
    assert decoded.pointer.pointer_id == 1234
    assert decoded.pointer.x == 0.25
