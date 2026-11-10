# Yuktara UI native renderer

Yuktara UI's native renderer uses Skia for CPU-backed raster drawing and SDL3
for desktop window creation, event polling and frame presentation. It is a
native rendering path: no DOM, browser runtime, HTML, CSS or pywebview is used.

## Typography

Inter is the default family. The resolver asks Skia for Inter first, then tries
Arial, Noto Sans, DejaVu Sans and the platform sans-serif fallback. Applications
that require identical typography on every machine should still package a
licensed copy of their chosen font; system font availability can differ.

## Rendering

`SkiaRenderer` creates a CPU-backed raster surface and provides drawing methods
for clearing, rectangles, rounded rectangles, clipping and text. It can export
PNG snapshots for visual regression tests and debugging. SDL3 receives packed
RGBA frames through the ctypes-based presentation adapter.

## Automatic dependencies

Skia Python 144.1 is installed lazily with the active Python interpreter when
rendering or text measurement first needs it. SDL3 3.4.20 is downloaded from the
official SDL release on Windows/macOS, or built from its checksum-verified
official source on Linux. Both are stored in the per-user cache. Developers do
not have to manually download the Skia package or SDL3 shared library.

To prepare everything before starting an app:

```bash
python -m novaui setup
```

`python -m pip install -e .` installs the Yuktara UI Python package itself. The
optional `[native]` extra can be used by projects that prefer dependency setup
at package-install time, but it is not required for first-run provisioning.

## Example

```python
from novaui.native import RenderSize, SkiaRenderer
from novaui.native.theme import NativeTheme

renderer = SkiaRenderer(RenderSize(960, 640))
theme = NativeTheme()
renderer.clear(theme.background)
renderer.draw_rect(32, 32, 360, 120, theme.surface, radius=theme.radius_large)
renderer.draw_text("Yuktara UI", 56, 88, color=theme.foreground, font=theme.font)

with open("yuktara-ui-preview.png", "wb") as output:
    output.write(renderer.to_png_bytes())
```

## Current boundaries

- The renderer currently uses CPU raster surfaces; direct GPU surface
  integration remains future work.
- SDL3 ctypes structure/event decoding and platform behavior still require
  end-to-end validation on each supported operating system.
- Complex-script shaping, bidi cursor movement and deterministic bundled font
  resolution need further validation and implementation.
- Android and iOS require dedicated Python embedding and native surface hosts.


## Window resizing and aspect preservation

The SDL3 host tracks UI dimensions separately from the backing pixel size.
When the frame and SDL renderer output have different aspect ratios,
`SDL3Window.present()` centers the frame using an aspect-fit destination
rectangle and clears the remaining area with the configured letterbox color.
This prevents texture stretching during transient size mismatches.

The runtime resizes the Skia raster surface when the window's logical or pixel
size changes. For display-scale changes, use `SDL3Window.run_runtime()` so
window metrics are re-read and the layout is measured again.
