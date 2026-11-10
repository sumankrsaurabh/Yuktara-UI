# Yuktara UI native runtime — SDL3 window host

The desktop host uses SDL3 for windowing, the event queue and presentation:

`Python UI → layout → Skia raster surface → RGBA8 frame → SDL3 streaming texture → OS window`

## Design decisions

- **SDL3 is the desktop window and input host.** There is no browser, DOM, local
  HTTP server, WebView or pywebview layer.
- The adapter loads the SDL3 shared library through `ctypes`, avoiding a
  mandatory third-party Python SDL binding.
- Skia draws into a CPU raster surface. `skia_bridge.py` reads explicit
  RGBA8888 pixels for upload, avoiding assumptions about native N32 byte order.
- SDL window creation, event polling, presentation and destruction are
  restricted to the thread that opened the window.
- SDL3 is checked against the framework's pinned minimum version (3.4.20).

## Run the integrated host loop

```python
from novaui.native import NativeRuntime, RenderSize, SkiaRenderer
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame

renderer = SkiaRenderer(RenderSize(1100, 720))
runtime = NativeRuntime(build_ui, renderer, 1100, 720)
skia = renderer._module()
window = SDL3Window("Yuktara UI", 1100, 720)
window.run_runtime(
    runtime,
    lambda app: renderer_frame(renderer, skia_module=skia),
)
```

`run_runtime()` opens the window, queries logical and backing-pixel sizes,
resizes and starts the runtime, decodes and dispatches events, flushes queued
state changes, advances animation and toast time, presents RGBA frames, then
stops the runtime and releases SDL resources. `frame_provider(runtime)` keeps
Skia pixel extraction injectable. `max_frames` is available for deterministic
smoke tests.

## Event and coordinate model

`poll_events()` exposes raw 128-byte SDL event records. `poll_input_events()`
uses `SDL3EventDecoder` to produce backend-neutral keyboard, UTF-8 text,
mouse, wheel, touch, window resize, backing-pixel resize and window-focus events.

Layout and mouse coordinates use logical window pixels. SDL touch positions and
deltas are normalized fractions and are converted by `NativeRuntime` before
hit-testing. `SDL_GetWindowSize()` supplies logical dimensions;
`SDL_GetWindowSizeInPixels()` supplies backing-surface dimensions. Independent
X/Y scale factors are passed to `RenderSize` so Skia rasterizes at the required
pixel resolution while layout remains in logical coordinates.

## Current limitations

1. The presentation path uploads CPU-rendered frames through an SDL streaming
   texture. It is a correctness-oriented bridge, not a GPU-accelerated Skia
   surface or a dirty-region compositor.
2. Backend-injected tests cover the Python event/lifecycle contracts, but real
   window creation, high-DPI behavior, clipboard, dialogs, font shaping and
   image decoding still need validation on each target operating system.
3. Native screen-reader bridges, full IME composition/candidate positioning,
   Android and iOS platform backends are not included in this desktop backend.
4. The host loop is intentionally simple. Applications with a custom event
   loop must call `runtime.process_pending()` and `runtime.advance_time()` and
   present a frame on the UI thread.
