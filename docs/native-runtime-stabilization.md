# Yuktara UI 3.2 — runtime and retained-tree stabilization

This release hardens the retained tree and desktop lifecycle without changing
widget construction APIs.

## Complete retained-node reconciliation

The reconciler now derives its declarative copy list from `LayoutNode` dataclass
fields. New visual, accessibility, grid and callback fields are therefore
included automatically. Derived layout state is not copied. A reused node keeps
live accessibility focus and scroll offsets, and its cached text layout is
invalidated so the next measure pass rebuilds geometry from the updated text and
style configuration. The dispatcher retains identity across rebuilds; detached
nodes are removed from pointer capture, hover, touch-scroll and focus-history
collections.

Nodes that are removed from the tree are also pruned from pointer capture,
hover and touch-scroll state. A still-live dispatcher is updated to the new root,
so keyboard focus and active pointer capture survive compatible state-driven
rebuilds.

## UI-thread scheduling

A standalone `Scheduler` remains synchronous by default. When a
`NativeRuntime` starts, it binds its scheduler to the current UI thread. State
changes from that thread continue to rebuild synchronously. State changes from
worker threads are queued and must be applied on the UI thread with
`runtime.process_pending()`.

The runtime host calls `process_pending()` during its event loop. Applications
that own a custom event loop should do the same on each UI frame. State-bound
`apply` callbacks are also marshalled through the scheduler, so they do not run
on a worker thread before the component rebuild. Pending callbacks from a
cancelled binding are ignored after unmount. Calling `flush()`, rendering,
dispatching input, resizing or stopping from a non-owner thread raises
`RuntimeError` rather than invoking SDL/Skia on the wrong thread.

## Logical and backing-pixel sizes

Layout and pointer coordinates use logical window pixels. `SDL3Window.get_sizes()`
returns `(logical_size, pixel_size)` using `SDL_GetWindowSize` and
`SDL_GetWindowSizeInPixels`. `NativeRuntime` tracks both sizes and computes
independent X/Y scale factors. `RenderSize` carries an optional vertical scale
for surfaces where the pixel ratios differ slightly.

SDL touch positions and deltas arrive normalized by SDL3. The runtime converts
them to logical coordinates before hit-testing and dispatch. Mouse coordinates
remain in logical window pixels. `WINDOW_RESIZED` changes logical dimensions;
`WINDOW_PIXEL_SIZE_CHANGED` updates the backing surface dimensions.

## Connected SDL3 host

`SDL3Window.run_runtime(runtime, frame_provider)` provides a common lifecycle:

1. Open the SDL3 window and query logical and pixel dimensions.
2. Resize the runtime backing surface and mount the component tree.
3. Poll and decode SDL3 events, dispatching them to the runtime.
4. Flush queued cross-thread state changes and advance animation/overlay time.
5. Ask `frame_provider(runtime)` for an RGBA `PixelFrame` and present it.
6. Stop the runtime and close SDL3 resources on the opening thread.

The frame provider keeps pixel extraction injectable. For `SkiaRenderer`, use
`renderer_frame(renderer, skia_module=skia)` from `novaui.native.platform.skia_bridge`.

```python
from novaui.native import NativeRuntime, RenderSize, SkiaRenderer
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame

renderer = SkiaRenderer(RenderSize(1100, 720))
skia = renderer._module()  # initialize the configured Skia binding
runtime = NativeRuntime(build_ui, renderer, 1100, 720)
window = SDL3Window("Yuktara UI", 1100, 720)
window.run_runtime(
    runtime,
    lambda app: renderer_frame(renderer, skia_module=skia),
)
```

## Current boundaries

This milestone has backend-injected regression coverage for lifecycle and event
routing. It does not certify real window creation, input, display scaling,
clipboard, file dialogs, font shaping or image decoding on every target OS.
The presentation path remains CPU-raster Skia uploaded to an SDL streaming
texture. GPU surfaces, native screen-reader bridges and mobile platform backends
remain future work. The 3.2 regression suite validates the backend-injected
lifecycle and coordinate contracts; it is not a substitute for real desktop
smoke tests on each supported OS and display-scaling configuration.
