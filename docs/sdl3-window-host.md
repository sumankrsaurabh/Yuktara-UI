# Yuktara UI native runtime — SDL3 window host

This milestone adds a native desktop window and a presentation path:

`Python UI / layout (future) → Skia raster surface → RGBA8 frame → SDL3 streaming texture → SDL renderer → OS window`

## Design decisions

- **SDL3 is the window, event-queue, and presentation host.** No browser, DOM,
  local HTTP server, or pywebview is involved.
- The adapter loads the SDL3 shared library at runtime using `ctypes`. This
  avoids forcing one third-party Python SDL binding on the framework.
- Skia remains the drawing engine. `skia_bridge.py` explicitly reads RGBA8888
  pixels from a Skia image so SDL does not need to guess Skia's native N32 byte
  order.
- SDL calls are confined to the thread that opened the window.
- The frame loop is intentionally simple. A scheduler, dirty-region rendering,
  normalized input events, and GPU-backed Skia surfaces are later milestones.

## Runtime requirements

- Python 3.10+.
- Internet access on first use when Skia or SDL3 is missing or older than the
  framework's pinned baseline.
- On Linux, a package manager and an interactive terminal may be needed once
  to authorize installation of the C compiler and SDL video/audio headers used
  to build the official SDL3 source release into the per-user cache.
- Inter is preferred when installed; configured system fallback families are
  used when it is not available.

The dependency manager installs Skia Python and provisions SDL3 automatically.
Developers do not need to download SDL DLLs or install the Python Skia binding
by hand. Use `python -m novaui setup` for a preflight check before launching.

The SDL C API signatures used here follow the official SDL3 documentation:
`SDL_CreateWindow`, `SDL_CreateRenderer`, `SDL_CreateTexture`,
`SDL_UpdateTexture`, `SDL_RenderTexture`, and `SDL_RenderPresent`.

## Run the smoke test

From the repository root:

```bash
python -m pip install -e .
python -m novaui setup
python examples/native/sdl3_skia_window.py
```

The example's Skia and SDL3 dependencies are prepared automatically. An
explicit `library_path` remains available for development and custom builds;
explicit libraries must report SDL3 3.4.20 or newer.

## Current limitations — do not mistake this for a finished backend

1. `poll_events()` currently preserves raw 128-byte SDL event records and
   normalizes only `SDL_EVENT_QUIT`. Keyboard, pointer, wheel, text-input,
   window-resize, and DPI events still need typed decoding.
2. The window's render texture currently follows the supplied frame dimensions;
   automatic window-size and high-DPI negotiation is not implemented.
3. This path uploads CPU-rendered frames. It is a correctness-first bridge, not
   the final high-performance GPU path.
4. Android/iOS are not covered by this desktop ctypes backend. They need native
   platform integration and separate packaging/build work.
5. The legacy runtime is maintained separately and is not included in the native Yuktara UI source package.

## Next implementation sequence

1. Decode SDL3 keyboard, pointer, wheel, text-input, resize, and DPI events.
2. Add a normalized `PointerEvent` / `KeyEvent` API.
3. Implement a frame scheduler and resize negotiation.
4. Add layout primitives (`Box`, `Row`, `Column`, `Stack`) and hit testing.
5. Add an OpenGL/Skia GPU surface backend behind the same renderer interface.
