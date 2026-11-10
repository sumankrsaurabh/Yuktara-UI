# Responsive layouts and device-independent sizing

Yuktara UI performs layout in **device-independent UI units**, then renders into a backing surface sized for the current SDL3 window pixel density.

This separates three concerns:

1. **Window size** — the native client area and its resize events.
2. **UI size** — the coordinate system used by layout, hit testing and controls.
3. **Backing pixel size** — the actual Skia raster dimensions used for sharp output on high-density displays.

## Automatic responsive layout

Use `Responsive` when a screen needs a different composition at different widths. Each variant is a minimum-width threshold and a child component or layout tree:

```python
from novaui.native import (
    Card, Label, Responsive, ResponsiveVariant, column, row,
)

compact = column(
    Card((Label("Account"), Label("Profile details"))),
    Card((Label("Activity"), Label("Recent activity"))),
)

wide = row(
    Card((Label("Account"), Label("Profile details"))),
    Card((Label("Activity"), Label("Recent activity"))),
    spacing=16,
)

screen = Responsive(
    variants=(
        ResponsiveVariant(0, compact),
        ResponsiveVariant(720, wide),
    )
)
```

The first variant is the fallback below its threshold. Thresholds must be strictly increasing. At each measure pass the engine selects the highest threshold that fits the available width.

The selected child is laid out in the responsive node's content area. A window resize triggers a layout pass, so a breakpoint transition does not require a state change or component rebuild.

Thresholds are measured in device-independent UI units, not raw framebuffer pixels.

## Fluid layouts without composition changes

Use existing layout features when the same composition can adapt naturally:

- `row(..., wrap=True)` for controls, tags and cards that should flow onto additional lines.
- `Grid(..., min_column_width=240)` for a grid whose column count should fall as width becomes narrow.
- Percentage dimensions such as `width="90%"` with `min_width` and `max_width`.
- `Container(max_width=...)` to constrain a wide reading surface.
- `ScrollView` for content that is legitimately taller or wider than its viewport.

Prefer wrapping or a responsive grid first. Use `Responsive` when the hierarchy, navigation or information order should actually change.

## SDL3 window sizing and high DPI

`SDL3Window` requests `SDL_WINDOW_HIGH_PIXEL_DENSITY` by default. It reads the SDL window size, pixel size, window display scale and pixel density, then normalizes platform-native coordinates into the framework's UI coordinate system.

The runtime receives both the normalized UI dimensions and the physical backing dimensions. On resize or display-scale changes, the Skia surface is recreated at the new backing size and the layout engine remeasures the component tree.

Mouse coordinates, mouse deltas and IME candidate-window rectangles are converted through the same coordinate scale. Touch locations remain normalized fractions and are converted by the runtime using the current UI size.

The SDL presentation layer uses a centered aspect-fit destination rectangle. When a frame and the renderer output have different aspect ratios, it adds letterboxing rather than stretching the frame.

For the resize-aware runtime lifecycle, use:

```python
window.run_runtime(
    runtime,
    lambda _runtime: renderer_frame(renderer, skia_module=skia),
)
```

Avoid custom event loops that call only `runtime.dispatch(event)`. Window resize, pixel-size and display-scale events must be sent through `runtime.handle_event(event)` or handled by `SDL3Window.run_runtime()`. The run loop also advances animations, processes UI-thread work, resizes the renderer and shuts down resources consistently.

## Example and tests

Run the live example:

```bash
python -m novaui setup
python examples/native/responsive_layout.py
```

The breakpoint tests are in `tests/native/test_responsive_layout.py`; high-DPI metrics and aspect-fit tests are in `tests/native/test_window_metrics.py`.

The live SDL3/Skia integration workflow should also be run on real supported desktop platforms. A virtual X11 window smoke test does not replace Windows/macOS/Linux hardware and mixed-DPI monitor validation.
