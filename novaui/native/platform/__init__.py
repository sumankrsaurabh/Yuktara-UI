"""Platform windowing and input backends for Yuktara UI."""
from .sdl3 import PixelFrame, SDL3Window, SDLEvent
from .events import EventType, InputEvent, KeyEvent, PointerEvent, WindowEvent
from .sdl3_events import SDL3EventDecoder
from .dispatcher import DispatchResult, InputDispatcher

__all__ = [
    "PixelFrame", "SDL3Window", "SDLEvent", "EventType", "InputEvent",
    "KeyEvent", "PointerEvent", "WindowEvent", "SDL3EventDecoder",
    "DispatchResult", "InputDispatcher",
]
