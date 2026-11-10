# GPU rendering and animation

## GPU renderer

Yuktara keeps `SkiaRenderer` as the default CPU-raster backend. An experimental
`SkiaGpuRenderer` is available for hosts that already own a current OpenGL
context:

```python
from novaui.native import RenderSize, SkiaGpuRenderer

# Create an OpenGL 3.x context with your platform/window host first.
# It must be current on this thread before this line.
renderer = SkiaGpuRenderer(RenderSize(1280, 800, scale=1.0))

# Use the same draw API as SkiaRenderer:
renderer.clear(0xFF101820)
renderer.draw_rect(24, 24, 240, 120, 0xFF2878D0, radius=16)
renderer.flush()  # submit Skia's queued GPU work

# Optional diagnostic/export path; PNG encoding may read pixels back to CPU.
png_bytes = renderer.to_png_bytes()

# Release Skia surfaces before the host destroys its OpenGL context.
renderer.close()
```

Install the native Skia wheel with:

```bash
python -m pip install -e ".[gpu]"
```

The renderer calls Skia's prebuilt Python binding GPU API
(`GrDirectContexts.MakeGL` and `Surfaces.MakeRenderTarget`). The host remains
responsible for creating, making current, swapping and destroying the OpenGL
context. All renderer calls must stay on that context's owning thread.

This first GPU milestone is an **off-screen OpenGL render target**, not yet a
drop-in replacement for the SDL3 window presenter. The existing integrated
SDL3 loop still presents CPU `PixelFrame` buffers. Directly sharing the Skia
render target with SDL3's presentation surface requires a platform-specific
texture/framebuffer interop path and is intentionally not simulated with a
costly readback. If no compatible OpenGL context or GPU-enabled Skia wheel is
available, use `SkiaRenderer` and the normal SDL3 presentation path.

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
