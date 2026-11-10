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


Moving a window between monitors is handled by SDL's window-display-changed
and window-display-scale-changed events. The host re-reads window size,
pixel density and display scale, then synchronizes the layout and Skia
backing surface again.


## Window adaptive information

Use `NativeRuntime.adaptive_info` when application-level decisions need both
width and height classes. It is recalculated whenever the runtime's logical
window size or backing-pixel scale changes.

```python
from novaui.native import (
    WindowWidthSizeClass,
    WindowHeightSizeClass,
)

info = runtime.adaptive_info

if info.width_size_class is WindowWidthSizeClass.COMPACT:
    # Use bottom navigation and a single content pane.
    ...
elif info.width_size_class in {
    WindowWidthSizeClass.LARGE,
    WindowWidthSizeClass.EXTRA_LARGE,
}:
    # Consider a navigation rail and a multi-pane workspace.
    ...

if info.height_size_class is WindowHeightSizeClass.COMPACT:
    # Reduce vertical chrome and allow content to scroll.
    ...
```

The default width classes use logical breakpoints: compact below 600, medium
from 600, expanded from 840, large from 1200 and extra-large from 1600. Height
classes are compact below 480, medium from 480 and expanded from 900. These
defaults can be customized with `WindowSizeBreakpoints`. Width and height are
classified independently. `pixel_width` and `pixel_height` are included for
rendering diagnostics only; they never drive adaptive breakpoints.

The helper `compute_window_adaptive_info()` can also be used without creating
a native runtime, for previews, tests and custom application hosts.

## Resize event coalescing

The standard SDL3 runtime host coalesces all window-resize, backing-pixel-size,
display-migration and display-scale events from one SDL event batch. It queries
the final window metrics once, updates the runtime once, and performs at most
one surface recreation/layout pass for that batch. Identical repeated metrics
are treated as a no-op by `NativeRuntime.resize()`. This avoids repeated full
layout and raster work while the user is dragging a window edge.

## Two-dimensional adaptive composition

Use `AdaptiveLayout` when the best composition depends on both available
width and height. This is useful for short landscape windows, compact laptop
windows, and large desktop workspaces. The first variant is the fallback;
later variants activate only when **both** minimum dimensions are satisfied.

```python
from novaui.native import AdaptiveLayout, AdaptiveVariant, column, row, Grid

compact = column(sidebar, content)
wide = row(sidebar, content, spacing=16)
workspace = Grid(children=(sidebar, content, inspector), columns=3)

screen = AdaptiveLayout(
    variants=(
        AdaptiveVariant(0, 0, compact),
        AdaptiveVariant(760, 0, wide),
        AdaptiveVariant(1200, 720, workspace),
    )
)
```

The first variant is the fallback; later variants override earlier matches
when both of their minimum dimensions fit. Use a zero threshold on one axis
for a width-only or height-only condition. Threshold pairs must be unique.
Resizing switches the retained child without rebuilding the component.
Thresholds use logical UI units, not framebuffer pixels.

Use `Responsive` for width-only breakpoints and `AdaptiveLayout` when both
axes materially affect information hierarchy. Avoid using the latter merely
to scale controls; use fluid constraints, wrapping and scrolling for that.

## Adaptive navigation scaffold

`NavigationScaffold` supplies a common navigation pattern that changes
presentation as the window grows: a bottom bar on compact windows, a
navigation rail on medium windows, and a full drawer on spacious desktop
windows. It keeps one content node and one selected destination model across
these compositions.

```python
from novaui.native import NavigationItem, NavigationScaffold, Label

navigation = NavigationScaffold(
    items=(
        NavigationItem("Home", icon="⌂", key="home"),
        NavigationItem("Projects", icon="▦", key="projects"),
        NavigationItem("Settings", icon="⚙", key="settings"),
    ),
    content=Label("Your current page"),
    selected="home",
    on_select=lambda destination: print(destination.key),
)
```

The default transitions are bottom navigation below 600 logical units,
navigation rail from 600, and full drawer from 1100 logical units when height
is at least 640. These are configurable through `min_rail_width`,
`min_drawer_width` and `min_drawer_height`. Selection callbacks receive the
selected `NavigationItem`; disabled destinations cannot be selected.
The scaffold provides navigation chrome and selection state, while the
application remains responsible for switching page content in response to
the callback.
