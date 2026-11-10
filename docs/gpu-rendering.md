# GPU rendering and animation

## GPU renderer

Yuktara keeps `SkiaRenderer` as the default CPU-raster backend. The optional
`SkiaGpuRenderer` can now wrap SDL3's default OpenGL framebuffer for direct
GPU drawing, without a GPU-to-CPU readback or SDL streaming-texture upload:

```python
from math import sin
from time import perf_counter
from novaui.native.platform.sdl3 import SDL3Window

with SDL3Window(
    title="Yuktara GPU demo",
    width=1100,
    height=720,
    graphics_backend="opengl",
    vsync=1,
) as window:
    renderer = window.create_gpu_renderer()
    started = perf_counter()
    try:
        while True:
            if any(event.quit_requested for event in window.poll_events()):
                break
            elapsed = perf_counter() - started
            x = 420 + sin(elapsed * 1.4) * 260
            renderer.clear(0xFF101820)
            renderer.draw_rect(x, 300, 180, 100, 0xFF2878D0, radius=20)
            window.present_gpu(renderer)
    finally:
        # Release Skia resources while SDL's GL context is still current.
        renderer.close()
```

For a host that already owns an OpenGL context, the off-screen mode remains
available:

```python
from novaui.native import RenderSize, SkiaGpuRenderer
renderer = SkiaGpuRenderer(RenderSize(1280, 800))
renderer.clear(0xFF101820)
renderer.draw_rect(24, 24, 240, 120, 0xFF2878D0, radius=16)
renderer.flush()
renderer.close()
```

Install the native Skia wheel with:

```bash
python -m pip install -e ".[gpu]"
```

The renderer uses the prebuilt Skia Python binding GPU APIs
(`GrDirectContexts.MakeGL`, `GrBackendRenderTarget` and
`Surfaces.MakeFromBackendRenderTarget`). The host remains responsible for
creating, making current, swapping and destroying the OpenGL context. All
renderer calls must stay on that context's owning thread.

For SDL3, set `graphics_backend="opengl"` when creating the window. Yuktara
requests an OpenGL 3.3 core context and configures the swap interval through
SDL3. `create_gpu_renderer()` wraps the window's default RGBA8 framebuffer;
`present_gpu(renderer)` submits Skia work and swaps the SDL window. The
existing `graphics_backend="sdl"` path and `present(PixelFrame)` remain the
default CPU fallback. Recreate the GPU renderer after a drawable-size change
so its framebuffer dimensions match the new window size.

The backend is experimental. Driver support, context loss, high-DPI behavior,
resource lifetime and real-device performance must be validated on each target
OS/GPU before enabling it by default. OpenGL is used here because it is exposed
by the prebuilt `skia-python` binding; this does not claim Vulkan, Metal or
Direct3D integration through this Python API.

## Animation

The native runtime already owns an explicit host-clock animation manager. It
does not create timer threads: the SDL host advances it once per frame, and
property changes invalidate the runtime for repaint. This keeps animation
timing deterministic and keeps widget animation independent of any browser or
JavaScript runtime.

Registered curves now include linear, quadratic, cubic, quartic, sine, back,
bounce and elastic easing. Applications can also supply a custom easing
callable:

```python
runtime.animate(
    node,
    "opacity",
    0.0,
    duration_ms=240,
    easing="ease_out_cubic",
)

runtime.animate(
    node,
    "translation_x",
    24.0,
    duration_ms=320,
    easing=lambda progress: progress * progress,
)
```

The target attribute must be numeric. Curves that overshoot (for example
`ease_out_back` and `ease_out_elastic`) are useful for position and scale;
use bounded curves for values such as opacity. Reduced-motion mode completes
new and active animations immediately.

For details on the existing animation lifecycle and accessibility behavior,
see [native animation and accessibility](native-animation-accessibility.md).
