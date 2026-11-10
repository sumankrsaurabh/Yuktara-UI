# Yuktara UI normalized input events

The SDL3 backend now translates common desktop events into backend-neutral
`InputEvent` values.

## Supported events

| SDL3 source | Yuktara UI event | Data |
|---|---|---|
| `SDL_EVENT_QUIT` | `QUIT` | timestamp |
| `SDL_EVENT_WINDOW_RESIZED` | `WINDOW_RESIZED` | logical width, height, window ID |
| `SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED` | `WINDOW_PIXEL_SIZE_CHANGED` | pixel width, height, window ID |
| Window focus gained/lost | matching focus event | window ID |
| Key down/up | `KEY_DOWN` / `KEY_UP` | keycode, scancode, modifiers, repeat |
| Text input | `TEXT_INPUT` | UTF-8 text |
| Mouse motion | `POINTER_MOTION` | position, delta, button-state mask |
| Mouse button down/up | `POINTER_DOWN` / `POINTER_UP` | position, button, click count |
| Mouse wheel | `POINTER_WHEEL` | position and wheel delta |
| Finger down/up/motion | pointer events (`source="touch"`) | normalized position, delta, finger ID |

Touch finger down/up/motion events are normalized as pointer events with
`source="touch"`. SDL touch coordinates remain normalized to the 0–1 range;
the input router should scale them against the current logical window bounds.
Keyboard text-editing/composition events are not yet normalized.

## Safety and ABI notes

The decoder consumes SDL3's 128-byte `SDL_Event` union as bytes and reads only
the known SDL3 event structures. It does not depend on a third-party Python
binding. Validate this decoder against the exact SDL3 headers used by the
target build before shipping across every supported architecture.

## Example

```python
from novaui.native.platform import SDL3EventDecoder

decoder = SDL3EventDecoder()
for raw_event in window.poll_events():
    event = decoder.decode(raw_event.raw)
    if event.type.name == "KEY_DOWN":
        print(event.key.keycode)
```
