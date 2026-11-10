# Yuktara UI

**Yuktara UI** is a Python-first native UI framework by **Yuktara Technologies**.
It uses SDL3 for the desktop window/input layer and Skia for CPU raster rendering.
The historical Python import namespace is currently `novaui` and will be migrated
only through a planned compatibility release.

> **Status:** experimental native desktop UI framework (3.3.0.dev0; 3.4 development).
> Automated CI passes across Windows, macOS and Linux on Python 3.10–3.15. A
> Linux/Xvfb SDL3 + Skia live-window smoke test also passes; physical-device,
> mixed-DPI monitor and platform-specific IME/accessibility validation remains ongoing.

For a cumulative inventory of implemented features, development milestones, examples and known limitations, see [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md). See the [native accessibility semantics guide](docs/native-accessibility.md) for semantic metadata and current platform limitations.

## Native stack

- **SDL3 3.4.20** — native desktop window and event host.
- **Skia Python 144.1** — CPU raster rendering and text metrics.
- **Python** — layout, retained tree, reactivity, normalized input and runtime.
- **Native typography and editing** — Inter-first glyph fallback runs,
  cluster-aware text metrics, selection/caret painting, text scrolling,
  SDL3-backed system clipboard access, paragraph-aware Unicode line wrapping
  and source-indexed rich inline text styling. Optional Unicode extended
  grapheme segmentation is available through the `unicode` extra; optional
  HarfBuzz shaping is available through the `shaping` extra and explicit
  font-file configuration.
- **Native component library** — responsive `Responsive`/`ResponsiveVariant` layouts, labels, buttons, containers, cards, badges,
  dividers, progress bars, checkboxes, switches, radio groups, text inputs,
  dropdowns, sliders, tabs, segmented controls, responsive grids, scroll views,
  images, tables, navigation drawers, calendars, date pickers, tree views and
  SDL3-backed file pickers, plus dialogs, popovers, tooltips, context menus and
  toast notifications with light/dark themes.
- **Native overlay manager** — stacked floating surfaces, modal input blocking,
  anchor-aware placement, viewport collision handling and host-driven toast time.
- **Native animation and accessibility** — host-clock-driven property transitions,
  reduced-motion handling, focus rings, context-menu keyboard navigation and
  modal accessibility scopes.
- **Automatic dependency manager** — provisions Python and native dependencies
  on first use and supports an explicit preflight setup command.

The repository contains no HTML/CSS/JavaScript renderer, browser runtime,
WebView or pywebview implementation.

## Quick start

Create a virtual environment and install the project:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
```

Run automatic dependency preflight (optional; the window/render paths also
bootstrap the dependencies when first needed):

```bash
python -m novaui setup
```

Run the integrated SDL3 + Skia application runtime:

```bash
python examples/native/runtime_window.py
```

For a low-level renderer/window smoke test without the component runtime, run
`python examples/native/sdl3_skia_window.py`.

The integrated host loop can also be used through `SDL3Window.run_runtime()`;
see [`docs/native-runtime-stabilization.md`](docs/native-runtime-stabilization.md)
for lifecycle, UI-thread scheduling and high-DPI coordinate details.

Run the native component gallery:

```bash
python examples/native/component_gallery.py
```

Run the focused input-controls gallery:

```bash
python examples/native/input_gallery.py
```

Run the native overlay gallery:

```bash
python examples/native/overlay_gallery.py
```

Run the native animation and accessibility gallery:

```bash
python examples/native/animation_gallery.py
```

Explore rich text and paragraph layout:

```bash
python examples/native/rich_text_paragraph.py
```

Inspect optional HarfBuzz shaping with a local font file:

```bash
python examples/native/harfbuzz_shaping.py ./font.ttf --family "Inter"
```

## Automatic dependency behavior

- Skia Python **144.1** is installed from PyPI with the active Python interpreter.
- SDL3 **3.4.20** is downloaded from the official SDL release and checked against
  its published SHA-256 for Windows and macOS.
- On Linux, the official SDL3 3.4.20 source archive is SHA-256 verified and built
  into the per-user cache. If the compiler or X11/Wayland development headers
  are missing, setup attempts to install common build/video/audio packages
  through apt, dnf, pacman, zypper or apk. This can request administrator
  authorization once from an interactive terminal.
- Native libraries are stored in a per-user writable cache, not in site-packages
  or the project directory.
- NumPy is not installed because this source does not use it.

The first setup needs an internet connection. Python must already be installed.
For a preflight check, run `python -m novaui setup` before launching the app.

### Environment controls

| Variable | Purpose |
|---|---|
| `YUKTARA_UI_NO_AUTO_INSTALL=1` | Disable all automatic installation and downloading. |
| `YUKTARA_UI_CACHE_DIR` | Override the user cache location. |
| `YUKTARA_UI_SDL3_LIBRARY` | Supply an explicit SDL3 library path; the library must be SDL3 3.4.20 or newer. |

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q tests/native
python -m compileall -q novaui
```

The `CI` workflow runs the native tests, compilation and wheel checks across
Windows, macOS and Linux on Python 3.10 through 3.15. The `Native desktop
integration` workflow runs when platform/runtime/rendering code changes (or
when manually dispatched); it provisions SDL3 and Skia and opens a real SDL3 +
Skia window under a virtual X11 display.

To run the bounded desktop smoke test locally after dependency preflight:

```bash
python -m novaui setup
python scripts/native_runtime_smoke.py
```

The cumulative feature and development record is maintained in
[DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md).

For adaptive layouts, high-DPI coordinate handling and window resize behavior,
see [Responsive Layouts](docs/native-responsive-layout.md). Run
`python examples/native/responsive_layout.py` to try compact, medium and
expanded layouts in a resizable desktop window.

## Repository layout

```text
novaui/
  native/
    dependencies/  # first-run Python and SDL3 provisioning
    layout/        # geometry, nodes, measurement, arrangement, hit testing
    platform/      # SDL3 host, event decoding and dispatch
    reactivity/    # state, scheduler, components and keyed reconciliation
    rendering/    # retained layout-tree painter and clipping
    text/          # Skia-backed text measurement, cluster geometry and editing
    widgets/       # Native built-in component library
    renderer.py    # Skia CPU raster renderer
    runtime.py     # build -> layout -> paint -> input lifecycle
    overlays.py    # native floating surfaces and modal lifecycle
    theme.py       # native theme tokens
    typography.py  # Inter-first font configuration and resolver

tests/native/     # backend-injected unit tests
examples/native/  # SDL3/Skia example

docs/             # architecture, component library and subsystem documentation
```

## Platform validation and limitations

Tests can validate dependency-manager decisions and Python-side behavior, but
they do not certify a real desktop window on every operating system. Validate
SDL3 window creation, display scaling, GPU/driver behavior, audio/video backend
availability, IME composition, clipboard integration and installed font fallback
coverage on each supported OS. SDL3 clipboard APIs are implemented, but their
end-to-end desktop behavior is not yet certified on each target OS.
The current Skia renderer uses CPU raster surfaces; direct GPU surface integration
is future work. Mobile backends are not included.

## License

No open-source license has been selected. The source distribution remains
proprietary until Yuktara Technologies adds an explicit license.


## Native 2.3 input components

See [README-NATIVE-2.3.md](README-NATIVE-2.3.md) and
[docs/native-input-components.md](docs/native-input-components.md) for TextField,
TextArea, Dropdown, Slider, Tabs and SegmentedControl. Run
`python examples/native/input_gallery.py` to see the controls.


## Native 2.4 overlay components

See [README-NATIVE-2.4.md](README-NATIVE-2.4.md) and
[docs/native-overlay-components.md](docs/native-overlay-components.md) for
Dialog, Popover, Tooltip, ContextMenu, Toast and OverlayManager usage.
Run `python examples/native/overlay_gallery.py` to exercise them.


## Native 2.5 animations and accessibility

See [README-NATIVE-2.5.md](README-NATIVE-2.5.md) and
[docs/native-animation-accessibility.md](docs/native-animation-accessibility.md)
for property animation, reduced motion, focus feedback, keyboard context menus
and modal accessibility scopes.


## Native 2.6 typography and text editing

See [README-NATIVE-2.6.md](README-NATIVE-2.6.md) and
[docs/native-text-editor.md](docs/native-text-editor.md) for font fallback runs,
cluster-aware measurement, selection/caret geometry and SDL3 clipboard support.
Run `python examples/native/text_editor_gallery.py` to try the text controls.


## Native paragraph formatting (2.9)

Per-paragraph alignment, indentation, paragraph spacing, line-height overrides
and native list markers are available through `ParagraphStyle` and `RichText`.
See [`docs/native-text-paragraphs.md`](docs/native-text-paragraphs.md) and
`examples/native/rich_text_paragraph.py`.

## Native document layout (3.0)

The document subsystem paginates native paragraph blocks onto fixed-size pages
with explicit page breaks, page-numbered headers/footers, keep-together and
widow/orphan controls. See [`README-NATIVE-3.0.md`](README-NATIVE-3.0.md) and
[`docs/native-document-layout.md`](docs/native-document-layout.md). Run
`python examples/native/document_pagination.py preview.png` for an A4 raster
preview using the Skia renderer.


## Native 3.1 general-purpose components

Yuktara UI 3.1 adds responsive `Grid`, `Container`, `ScrollView`, `Image`,
`Table`, `NavigationDrawer`, `Calendar`, `DatePicker`, `TreeView` and SDL3-backed
`FilePicker`. Run `python examples/native/advanced_component_gallery.py` to
explore them. See [`README-NATIVE-3.1.md`](README-NATIVE-3.1.md) and
[`docs/native-component-library.md`](docs/native-component-library.md) for
usage and current platform-validation limits.


## Native 3.2 runtime stabilization

Yuktara UI 3.2 hardens retained-tree updates, UI-thread state scheduling, SDL3
window lifecycle, touch coordinate conversion and high-DPI backing-surface sizing.
See [`README-NATIVE-3.2.md`](README-NATIVE-3.2.md) and
[`docs/native-runtime-stabilization.md`](docs/native-runtime-stabilization.md).

## Native 3.3 advanced layout

Yuktara UI 3.3 adds percentage dimensions, per-node min/max constraints, flex
wrapping for rows and columns, baseline alignment, absolute positioning and
GridItem row/column spans. `Positioned` and `GridItem` expose these behaviors
through the component API. See [`README-NATIVE-3.3.md`](README-NATIVE-3.3.md),
[`docs/native-advanced-layout.md`](docs/native-advanced-layout.md) and
[`docs/native-layout-engine.md`](docs/native-layout-engine.md).

Run the backend-neutral layout example with:

```bash
python examples/native/advanced_layout.py
```


## Desktop display and platform parity

The SDL3 host tracks logical UI dimensions separately from backing pixels,
recreates the Skia raster surface at the current pixel size, and uses
aspect-fit presentation to avoid stretching. Renderer VSync is requested by
default and follows the active display refresh when supported. Active display
resolution, density and refresh metadata are available through
`SDL3Window.get_display_metrics()`.

See [Native platform parity roadmap](docs/native-platform-parity-roadmap.md)
for the current gaps against mature adaptive UI toolkits and the physical
multi-monitor/high-refresh acceptance matrix. GPU rendering and physical
multi-platform certification remain unfinished.


Adaptive runtime information is available through `NativeRuntime.adaptive_info`.
It classifies the actual logical application window independently on width and
height (compact, medium, expanded, large and extra-large width classes), while
preserving backing-pixel dimensions for sharp rendering. Resize events are
coalesced per SDL event batch to avoid repeated surface recreation while the
user drags a window edge. See [responsive layout documentation](docs/native-responsive-layout.md).
