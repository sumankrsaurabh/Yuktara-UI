# Yuktara UI — Implementation Register

> **Purpose:** This file is the living record of features and engineering work implemented in the Yuktara UI source repository. Update it whenever a feature batch is merged.
>
> **Recorded source baseline:** `main` — package version `3.3.0.dev0`; 3.4 development work is in progress.  
> **Last inventory review:** 2026-11-10  
> **Python import namespace:** `novaui` (the historical namespace is retained for compatibility)

This register describes what is present in the source and its documented behavior. It does **not** claim that every SDL3, Skia, operating-system, or accessibility integration has been certified on every target machine. See [Known limitations and unfinished integration](#known-limitations-and-unfinished-integration).

## 1. Project and architecture

Yuktara UI is a Python-first native desktop UI framework. Its application UI is built from Python components and retained layout nodes, laid out by the framework, and painted with Skia. SDL3 supplies the desktop window and input/event host.

| Layer | Implemented responsibility |
|---|---|
| Public Python API | Native widgets, layout helpers, themes, runtime and document APIs exposed under `novaui`. |
| Layout engine | Backend-neutral measure/arrange, geometry, constraints, placement, scroll extents and hit testing. |
| Retained UI tree | Layout nodes retain visual properties, callbacks, accessibility metadata and child relationships. |
| Reactivity | State, component rebuilding, keyed reconciliation and scheduled updates. |
| Runtime | Mount, layout, paint, event dispatch, resize, frame progression and teardown lifecycle. |
| Platform host | SDL3 window lifecycle, event decoding, normalized pointer/touch input, clipboard and file-dialog integration. |
| Rendering | Skia CPU raster renderer and retained-tree painter with clipping and compositing. |
| Overlays | Runtime-managed floating and modal surfaces above the application tree. |
| Typography | Font configuration/resolution, text measurement, paragraph layout and editing geometry. |
| Dependency setup | First-run/preflight provisioning for Python and native runtime dependencies. |

The repository does not implement an HTML/CSS/JavaScript renderer, browser runtime, WebView or pywebview layer. The current rendering path uses CPU raster Skia; a direct GPU-surface renderer is not part of this baseline.

## 2. Implemented layout and composition

### Layout primitives

- `box`, `row`, `column`, `stack`, `scroll`, `grid` and `text` layout nodes.
- High-level `row(...)`, `column(...)` and `stack(...)` composition helpers.
- `responsive` layout nodes with ordered minimum-width variants, plus public `Responsive` and `ResponsiveVariant` components for breakpoint-driven hierarchy changes.
- `Container`, `Card`, `Spacer`, `Divider`, `Grid`, `ScrollView`, `Positioned`, `Responsive` and `ResponsiveVariant` components.
- Intrinsic sizing, padding, spacing, weighted children and main-/cross-axis alignment.
- Fixed and percentage dimensions; per-node minimum and maximum width/height constraints.
- Flex wrapping for rows and columns, per-line spacing, weighted allocation, flex basis and per-child cross-axis alignment.
- Baseline alignment for rows containing text.
- Absolute positioning using left/right/top/bottom offsets, including edge-to-edge stretching.
- Grid auto-placement, explicit zero-based row/column placement, row/column spans, collision detection and stable reservation of explicitly placed cells.
- Responsive equal-width grid columns using a minimum column width.
- Vertical, horizontal and two-axis scroll viewports, clipping, scroll offsets and scroll extents.
- Hit testing that resolves the deepest topmost arranged node.
- Text measurement hooks that can use a configured text measurer; deterministic fallback sizing exists when no measurer is supplied.

The layout engine is intentionally not a complete CSS Flexbox/Grid implementation. See [the layout engine guide](docs/native-layout-engine.md).

## 3. Implemented component library

The following catalog is the documented native component surface in the 3.3 source baseline.

### Layout and surfaces

- `Container` — content surface with padding, margin, dimensions, fill/background, border and radius.
- `Card` — themed content surface.
- `row`, `column`, `stack` — horizontal, vertical and layered composition.
- `Grid` and `GridItem` — responsive grid and explicit placement/spans.
- `ScrollView` — clipped scrolling content.
- `Spacer` — fixed or flexible space.
- `Divider` — horizontal or vertical separator.
- `Positioned` — absolute-positioned child.
- `Responsive` / `ResponsiveVariant` — minimum-width breakpoint variants for switching between compact, medium and expanded compositions.

### Text, status and visual content

- `Label` and `RichText`.
- `Badge`.
- `ProgressBar`.
- `Image` — path, encoded bytes or decoded Skia image input, with `contain`, `cover`, `fill` and `none` fitting modes, rounded clipping and alternate-text semantics.
- Themed light/dark component styling through the native theme/token layer.

### Actions and input controls

- `Button`.
- `TextField` — single-line text editing.
- `TextArea` — multiline text editing, line wrapping and newline entry.
- `Checkbox`.
- `Switch`.
- `RadioGroup`.
- `Dropdown` — selectable option list with keyboard navigation; optionally attach it to the runtime overlay manager for an anchored, viewport-clamped floating menu with bounded scrolling and outside/Escape dismissal.
- `Slider`.
- `Tabs` and `TabItem`.
- `SegmentedControl`.
- `DatePicker`.

### Data, navigation and hierarchy

- `Table` — headers/body rows, weighted columns, cell padding, borders, striping and table semantics.
- `NavigationDrawer` and navigation items — selected entries, optional header/footer, badges and compact mode.
- `TreeView` and `TreeItem` — expandable/selectable hierarchy, including disabled entries.
- `Calendar` — month navigation and minimum/maximum date constraints.

### Overlays and notifications

- `Dialog` — centered modal surface and scrim.
- `Popover` — anchored floating content.
- `Tooltip` — pointer-transparent anchored hint.
- `ContextMenu` and `MenuItem`.
- `Toast` — timed or persistent notification.
- `OverlayManager` and `OverlayHandle` — stacking, placement, dismissal and lifecycle management.

### Operating-system integration

- `FilePicker` — open, save and folder selection through an injected dialog service and SDL3-backed integration.
- SDL3-backed UTF-8 system clipboard service for text controls.
- SDL3-backed desktop window, event and presentation integration.

For component API examples, see [the component library guide](docs/native-component-library.md), [input components](docs/native-input-components.md) and [overlay components](docs/native-overlay-components.md).

## 4. Input, focus and interaction behavior

The shared input dispatcher and controls implement:

- Normalized pointer and keyboard event routing.
- Focus/blur tracking and callbacks.
- Tab and Shift+Tab traversal through focusable controls.
- Enter/Space activation for focused clickable controls.
- Pointer capture so drag interactions continue outside the original control bounds.
- Keyboard and committed text input routing to the focused text control.
- Repaint requests after keyboard, text and captured-pointer changes.
- Slider pointer dragging, keyboard arrows and Home/End.
- Dropdown trigger/open/navigation/select/close keyboard behavior.
- Tabs and segmented-control keyboard selection.
- Disabled/read-only states and accessibility-focused state where documented by each component.
- Context-menu keyboard navigation and focus restoration after supported overlay dismissal.

## 5. Typography, text editing and rich text

### Font and text measurement

- Inter-first font configuration with configured fallback families for Noto Sans script variants, CJK, emoji, Arial and DejaVu Sans.
- Font fallback run resolution when the active Skia binding exposes glyph-coverage lookup.
- Shared Skia-backed text measurement when `NativeRuntime` uses `SkiaRenderer`; custom renderers can inject a `TextMeasurer`.
- `TextCluster`, `TextLine` and `TextLayout` geometry retaining source offsets.
- Caret position mapping, pointer-to-source offset mapping and line-specific selection rectangles.
- Paragraph-aware wrapping and source-indexed rich inline text styling.

### Text control editing

- Backspace/Delete and cursor movement.
- Home/End, Ctrl+A, Shift selection and Ctrl+Left/Right word navigation.
- Grapheme-aware deletion/movement for common combining-mark sequences, emoji modifiers, ZWJ emoji, flags and common Indic virama conjuncts.
- TextField/TextArea clipping and scroll-to-caret behavior.
- Native selection highlight and caret painting separate from the text value.
- SDL3 clipboard-backed Ctrl+C, Ctrl+X and Ctrl+V when a window clipboard service is supplied.
- SDL3 text-input start/stop integration when text controls gain/lose focus through the documented host path.

### Paragraph and rich-text formatting

- Inline rich-text spans and style runs.
- Paragraph alignment, indentation, paragraph spacing and line-height overrides.
- Native list markers.
- Source-indexed inline styling and paragraph-aware layout.

### Document pagination

The document subsystem adds:

- Configurable `PageSize` and `PageMargins`, with A4 portrait defaults.
- `DocumentParagraph` blocks that retain font configuration, inline rich text and paragraph styles.
- Explicit `PageBreak` blocks.
- Fixed-page pagination and source-preserving paragraph fragments.
- `keep_together`, `keep_with_next`, widow-line and orphan-line controls.
- Left, center and right page headers/footers.
- `{page}` and `{pages}` placeholders resolved after pagination.
- `DocumentLayout.paint_page()` for Skia or compatible recording renderers.
- A raster A4 pagination example.

This is a native document layout/raster-preview subsystem, not a PDF exporter or operating-system print pipeline.

## 6. Runtime, reactivity and lifecycle

### Retained tree and reconciliation

- Declarative retained-node reconciliation based on `LayoutNode` dataclass metadata.
- Refresh of callbacks, visual properties, accessibility metadata, paint hooks and grid settings when nodes are reused.
- Invalidation of cached text layout when relevant text/style state changes.
- Preservation of compatible live focus and scroll state through supported rebuilds.
- Pruning of removed nodes from pointer capture, hover, touch-scroll and focus-history collections.
- Dispatcher root updates when the retained tree is rebuilt.

### Scheduler and thread ownership

- Synchronous-by-default standalone scheduler.
- Runtime scheduler ownership bound to the UI thread on start.
- Worker-thread state changes queued for UI-thread processing through `runtime.process_pending()`.
- State-bound apply callbacks marshalled through the scheduler.
- Cancellation-aware handling of callbacks from unmounted bindings.
- Explicit runtime/window thread-affinity checks for flush, rendering, input dispatch, resize and stop operations.
- Failure isolation so one failing scheduled callback does not discard later callbacks in the same drained batch.

### Connected SDL3 host loop

- `SDL3Window.run_runtime(runtime, frame_provider)` opens the window, obtains logical/backing-pixel sizes, mounts the UI, decodes/dispatches events, flushes pending state, advances host-clock features, presents frames and tears down resources.
- `renderer_frame(...)` bridge for presenting the Skia renderer through the SDL3 host.
- Separate logical window and backing-surface dimensions with independent X/Y scale factors.
- SDL normalized touch positions/deltas converted into logical coordinates before dispatch.
- Handling for logical resize and backing pixel-size changes.
- Runtime restart behavior on the same owner thread is covered by the documented stabilization work.

Applications using a custom host loop are responsible for processing pending work, advancing time and presenting frames on the UI thread.

## 7. Overlays, animation and accessibility semantics

### Overlay manager

- Stacked overlay surfaces painted above the application tree.
- Centered modal dialogs with scrim and optional outside-click/Escape dismissal.
- Anchored popover and tooltip placement with collision flipping and viewport clamping.
- Context menu placement and viewport clamping.
- Front-to-back hit testing for interactive overlays.
- Pointer-transparent tooltips/toasts.
- Modal input blocking and focus/Tab confinement to the active modal.
- Focus restoration after supported menu/modal dismissal.
- Combined application and overlay semantic-tree construction.
- Explicit host-driven toast expiry; the framework does not start a hidden timer.

### Animation

- `AnimationManager` and `AnimationHandle`.
- Host-clock-driven numeric property animation through `NativeRuntime.animate(...)`.
- Linear, ease-in, ease-out, ease-in-out and ease-out-cubic easing.
- Replacement/cancellation and finish-all/cancel-all operations.
- Opacity compositing through Skia save layers, with a documented fallback for compatible injected renderers.
- Reduced-motion mode that completes active animations and skips future interpolation.

### Accessibility model

- Native semantic-tree representation for components.
- Documented roles, labels, values and states such as disabled, checked, selected, expanded and focused.
- Visible keyboard focus rings.
- Modal accessibility scopes that omit obscured background content while a modal is active.
- Context-menu keyboard focus/navigation behavior.
- Semantic composition that can include active overlays.

The semantic model and focus behavior are implemented in the framework. Native operating-system provider bridges and real assistive-technology certification are not included in this baseline.

## 8. Dependency management, setup and developer experience

- Package metadata and build configuration in `pyproject.toml`.
- Python package name: `yuktara-ui`; historical import namespace: `novaui`.
- CLI entry point: `yuktara-ui` mapped to `novaui.cli:main`.
- `python -m novaui setup` preflight setup command.
- Automatic first-use provisioning for the native dependency path, with a user-writable cache.
- Skia Python 144.1 native extra.
- SDL3 3.4.20 native runtime provisioning documented for Windows, macOS and Linux.
- SDL3 downloads/source archive are SHA-256 verified in the documented setup path.
- Linux setup can attempt installation of common build/video/audio development packages through the available system package manager; this may require administrator authorization.
- `YUKTARA_UI_NO_AUTO_INSTALL=1` to disable automatic installation/downloads.
- `YUKTARA_UI_CACHE_DIR` to override the native cache directory.
- `YUKTARA_UI_SDL3_LIBRARY` to supply an explicit compatible SDL3 library path.
- Optional `shaping` extra using `uharfbuzz`.
- Developer extras for pytest and package building.

Python must already be installed and first-run setup requires network access unless dependencies are supplied through the documented configuration.

## 9. Example applications and galleries

The repository includes native examples for the following workflows:

| Example | Demonstrates |
|---|---|
| `examples/native/runtime_window.py` | Integrated SDL3 + Skia runtime host loop. |
| `examples/native/sdl3_skia_window.py` | Lower-level SDL3/Skia window and renderer smoke path. |
| `examples/native/component_gallery.py` | Core component gallery. |
| `examples/native/input_gallery.py` | Text and input controls, including a dropdown menu hosted by the overlay manager. |
| `examples/native/overlay_gallery.py` | Dialogs, popovers, tooltips, menus and toast overlays. |
| `examples/native/animation_gallery.py` | Animation and accessibility interaction. |
| `examples/native/text_editor_gallery.py` | Native text editing. |
| `examples/native/rich_text_paragraph.py` | Rich text and paragraph formatting. |
| `examples/native/document_pagination.py` | A4 document pagination/raster preview. |
| `examples/native/advanced_component_gallery.py` | Grid, containers, tables, navigation, tree, calendar, date picker, images and file dialogs. |
| `examples/native/advanced_layout.py` | Percentage sizing, wrapping, positioning and grid spans. |
| `examples/native/responsive_layout.py` | Live compact, medium and expanded breakpoint layouts in a resizable SDL3 window. |
| `examples/native/harfbuzz_shaping.py` | Optional HarfBuzz shaping with an explicitly supplied font. |
| `scripts/native_runtime_smoke.py` | Short real-window SDL3 + Skia presentation smoke test used by the manual native integration workflow. |

## 10. Release and development history

This timeline records the documented source milestones retained in the repository. It is a feature-oriented history, not a claim that every intermediate development commit is listed.

| Milestone | Implemented development |
|---|---|
| Native foundation | Python-native retained UI, SDL3 window/input host, Skia CPU raster rendering, layout/runtime structure, themes, core components and dependency setup. |
| 2.1 — dependency baseline | SDL3 3.4.20 and Skia Python 144.1 baselines, verified SDL3 downloads, Linux source-build provisioning, automatic dependency bootstrap and removal of the unused NumPy dependency. |
| 2.2 — first component library | Labels, buttons, cards, badges, dividers, spacers, progress bars, checkboxes, switches, radio groups, light/dark semantic theme tokens, border rendering and backend-neutral accessibility semantics. |
| 2.3 — input components | TextField, TextArea, Dropdown, Slider, Tabs/TabItem, SegmentedControl; focus tracking, keyboard routing, Tab traversal, pointer capture and repaint after input. |
| 2.7 — optional text shaping | Optional HarfBuzz adapter, explicit font-file mapping, positioned glyph rendering through Skia TextBlob, source-cluster geometry and heuristic directional-run segmentation. Full UAX #9 bidi and IME composition remain incomplete. |
| 2.8 — rich text and line breaking | TextStyleSpan, TextPaintRun, TextParagraph, RichText widget, UAX #14-informed dependency-free line-break policy and discontiguous visual selection geometry. |
| 2.4 — overlays | Dialog, Popover, Tooltip, ContextMenu/MenuItem, Toast, OverlayManager/OverlayHandle; placement, modal input/focus handling and host-driven expiry. |
| 2.5 — animation/accessibility refinements | Animation manager/handles, easing, property animation, opacity compositing, reduced motion, focus rings, menu keyboard navigation, focus restoration and modal semantic scopes. |
| 2.6 — typography/text editing | Font fallback runs, shared text measurement, cluster/line/layout geometry, grapheme-aware editing, selection/caret painting, text scrolling and SDL3 clipboard integration. |
| 2.9 — paragraph formatting | Paragraph alignment, indentation, spacing, line-height overrides and list markers through paragraph styles and rich text. |
| 3.0 — document layout | Page configuration, page breaks, fixed-page pagination, paragraph fragments, keep/widow/orphan controls and page headers/footers. |
| 3.1 — general-purpose component library | Responsive Grid, Container, ScrollView, Image, Table, NavigationDrawer, Calendar, DatePicker, TreeView and SDL3-backed FilePicker. |
| 3.2 — runtime stabilization | Retained-tree reconciliation, UI-thread scheduling, runtime/window lifecycle, logical/backing-pixel sizing, touch-coordinate conversion and integrated SDL3 host loop. |
| 3.3 — advanced layout | Percentage dimensions and constraints, row/column flex wrapping, flex basis, baseline alignment, absolute positioning, GridItem placement and spans. |
| 3.4 — development in progress (not released) | Permanent cross-platform CI, SDL3/Skia desktop smoke workflow, SDL3 IME composition path, responsive width-breakpoint layouts, high-DPI logical/pixel coordinate separation, initial window-size normalization, aspect-preserving presentation, display/monitor-change synchronization, resize-aware example host loops, responsive galleries, defensive dimension validation for runtime/window resize entry points, and optional overlay-backed Dropdown menus. Regression tests, the permanent cross-platform CI matrix and the Linux/Xvfb SDL3/Skia live-window smoke test are passing. Package metadata remains at 3.3.0.dev0 until a release decision. |

## 11. Verification record

### 3.3.0.dev0 source-import baseline

The original source-import workflow recorded on 2026-11-10 completed successfully and reported:

- 283 tests passed.
- Python compilation check passed.
- Wheel build passed.
- Source archive checksum/extraction checks passed.
- Commit/push step passed.

Workflow record: [Import verified Yuktara UI Native 3.3.0.dev0](https://github.com/sumankrsaurabh/Yuktara-UI/actions/runs/42777562642).

### 3.4 development verification (unreleased)

The permanent cross-platform CI workflow completed successfully on 2026-11-10 for commit
`4a4f8cc45dd37d2d2172d6ee0c27bff5d7e48127`:

- 306 tests passed.
- All 18 operating-system/Python combinations passed: Windows, macOS and Ubuntu with Python 3.10–3.15.
- Package compilation and public import checks passed on all matrix jobs.
- Native package statement coverage: 84%.
- Wheel build, wheel installation and installed-distribution import passed.

Workflow record: [CI — 2026-11-10, run 42786741828](https://github.com/sumankrsaurabh/Yuktara-UI/actions/runs/42786741828).

The separate Linux/Xvfb SDL3 + Skia live-window integration job also completed successfully. It installed the system build prerequisites (including XTest), provisioned SDL3 and Skia, opened a real SDL3 window and presented Skia frames. This verifies the integrated desktop path in the virtual X11 environment; it does not certify physical displays, drivers or every supported operating system.

Workflow record: [Native desktop integration — 2026-11-10, run 42786336871](https://github.com/sumankrsaurabh/Yuktara-UI/actions/runs/42786336871).

### Latest 3.4 development verification — commit `124ea27a12ab17d6dc2dc627d348dbd27ea202a4`

The next verification run completed successfully on 2026-11-10:

- 323 tests passed.
- All 18 Windows/macOS/Ubuntu and Python 3.10–3.15 matrix jobs passed.
- The coverage job reported 84% statement coverage (6,444 statements; 1,037 missed).
- Wheel build, installation and installed-distribution import passed.
- The independent Linux/Xvfb integration job provisioned SDL3 3.4.20 and Skia Python 144.1, opened an SDL3 window and presented Skia frames.

Workflow records: [CI — run 42793002537](https://github.com/sumankrsaurabh/Yuktara-UI/actions/runs/42793002537) · [Native desktop integration — run 42793002651](https://github.com/sumankrsaurabh/Yuktara-UI/actions/runs/42793002651).

### Latest 3.4 development verification — dropdown overlay integration, commit `f24ffbf83ede84fb9d4e9c828f2d29c4fc6aa278`

The dropdown overlay integration completed verification on 2026-11-10:

- 327 tests passed.
- All 18 Windows/macOS/Ubuntu and Python 3.10–3.15 matrix jobs passed.
- The coverage job reported 84% statement coverage (6,504 statements; 1,045 missed).
- Wheel build, installation and installed-distribution import passed.
- The independent Linux/Xvfb SDL3 + Skia workflow passed dependency provisioning, window creation and frame presentation.

Workflow records: [CI — run 42794293051](https://github.com/sumankrsaurabh/Yuktara-UI/actions/runs/42794293051) · [Native desktop integration — run 42794292988](https://github.com/sumankrsaurabh/Yuktara-UI/actions/runs/42794292988).



The automated tests primarily validate Python-side behavior using backend-injected services, normalized events and recording renderers. They are not a substitute for testing actual desktop hardware, drivers, system dialogs, input methods, high-DPI displays or accessibility tools.

## 11A. Current 3.4 development work (not yet a release)

The package version remains `3.3.0.dev0`; the following work is on `main` as unreleased development code. Automated CI verification is recorded below, while native OS/device validation remains separate:

### Continuous integration

- `.github/workflows/ci.yml` runs the existing native suite and Python compilation on Ubuntu, Windows and macOS with Python 3.10 through 3.15. Python 3.10 remains tested because it is the declared minimum, although it reached upstream end of life on 2026-10-01.
- The workflow also builds and installs the wheel, verifies the installed package outside the source checkout, and measures package coverage.
- `.github/workflows/native-integration.yml` runs on main-branch changes to platform, runtime, rendering, layout, dependency or smoke-test code, and can also be dispatched manually. Its Linux/Xvfb job installs SDL3 build prerequisites, provisions Skia/SDL3 through `python -m novaui setup`, opens a real SDL3 window and presents Skia frames.
- `scripts/native_runtime_smoke.py` is the bounded three-frame desktop smoke application.
- The ordinary test matrix is backend-neutral by design. The separate Linux/Xvfb SDL3 + Skia live-window workflow has passed its window-open and frame-presentation steps; this is a smoke test, not cross-platform hardware certification.

### Window resizing, high DPI and responsive layout

- SDL3 windows now request `SDL_WINDOW_HIGH_PIXEL_DENSITY` by default, translate requested initial UI dimensions into native window coordinates, and enforce a configurable minimum client size (defaults to 320×240 UI units).
- Linux SDL3 source-build provisioning now installs XTest development headers (`libxtst-dev` and matching package names on supported Linux package managers), which SDL's X11 configuration requires when XTest support is enabled.
- Window size, backing pixel size, SDL window display scale and pixel density are read separately and normalized into device-independent UI coordinates.
- Mouse positions/deltas and IME candidate-window rectangles are converted using the same UI coordinate scale; touch coordinates remain normalized and are mapped by the runtime.
- SDL window display-scale and monitor-move changes trigger a fresh runtime/renderer size synchronization; the event decoder now recognizes `SDL_EVENT_WINDOW_DISPLAY_CHANGED` and `SDL_EVENT_WINDOW_DISPLAY_SCALE_CHANGED`.
- SDL3 texture presentation uses a centered aspect-fit destination rectangle and letterboxing instead of stretching a mismatched frame across the output surface.
- Corrected SDL3 focus-gained/focus-lost event identifiers and added display-change/display-scale-change decoding.
- Added public `Responsive` and `ResponsiveVariant` components. The layout engine selects width variants during measure, so the active tree changes at a breakpoint without a component rebuild.
- Runtime and SDL3 window dimension entry points now reject non-finite, non-integral or boolean dimensions as appropriate; runtime resize validates all logical and backing dimensions before mutating state.
- `Dropdown.attach_overlay_manager(runtime.overlays)` opts into a floating popover menu with bounded option scrolling, viewport-aware anchor placement, outside/Escape dismissal and keyboard selection. The standalone inline mode remains available when no manager is attached.
- Existing row flex wrapping and `Grid(min_column_width=...)` remain the preferred fluid-layout tools when changing the component hierarchy is unnecessary.
- All interactive native galleries were moved onto `SDL3Window.run_runtime()` so resize, pixel-size and display-scale events reach `NativeRuntime` consistently.
- Added `examples/native/responsive_layout.py` and the responsive/high-DPI guides.
- Added breakpoint/reflow tests in `tests/native/test_responsive_layout.py`, high-DPI/window-coordinate/letterbox/monitor-event tests in `tests/native/test_window_metrics.py`, and scaled IME candidate-window tests in `tests/native/test_ime_composition.py`; all pass in the subsequent successful 323-test CI run.

### IME composition path

- Added normalized `EventType.TEXT_EDITING` events carrying the composition string, cursor position and selection length.
- Added SDL3 `SDL_EVENT_TEXT_EDITING` decoding.
- Routed composition events through `NativeRuntime`, `InputDispatcher` and the focused text control.
- TextField/TextArea now display the temporary pre-edit string and underline without changing their committed value.
- Text input/IME operations are injectable through a dedicated `text_input` service; the existing `clipboard` adapter remains a backward-compatible fallback. OS clipboard access stays separately injectable.
- SDL3 `SDL_SetTextInputArea` and `SDL_ClearComposition` are exposed through `SDL3Window`; the candidate area is updated from measured caret geometry after layout.
- Committed `TEXT_INPUT` replaces the original selected range; Escape/blur cancels the pre-edit state.
- Added eight targeted tests in `tests/native/test_ime_composition.py`, covering SDL event decode, preview, commit, cancellation, runtime routing, candidate-area binding and independent input/clipboard services; they pass in the verified 323-test CI run.

## 12. Known limitations and unfinished integration

The following items are **not** to be treated as completed features in the 3.3 baseline:

- End-to-end IME behavior with physical keyboards and real input methods has not yet been validated on Windows, macOS and Linux. The 3.4 development code now decodes SDL3 text-editing events, routes them through the runtime, displays temporary pre-edit text with an underline without mutating committed text, handles commit and Escape/blur cancellation, and positions SDL's candidate area from measured caret geometry. See the regression tests in `tests/native/test_ime_composition.py`.
- The dropdown supports the overlay manager when attached to `runtime.overlays`; a legacy inline presentation is retained for unattached standalone widgets. Its menu integration is covered by selection, keyboard, outside-dismissal and attach/detach regression tests.
- Full Unicode Standard Annex #29 segmentation and complete Unicode line breaking.
- Complete bidirectional text, Arabic joining, Indic shaping, ligature-aware caret geometry and complex-script shaping across all platforms. Optional HarfBuzz support is available, but it does not make the entire text pipeline fully certified.
- Native accessibility provider bridges for Windows UI Automation, macOS NSAccessibility and Linux AT-SPI; screen-reader behavior is not certified.
- End-to-end SDL3 window, mixed-DPI monitor movement, clipboard, file-dialog, font fallback and image decoding verification on every supported OS/configuration. A Linux/Xvfb smoke run does not certify all platform-native behavior.
- Direct GPU Skia surfaces; the documented renderer path is CPU raster content presented through SDL3.
- Mobile backends for Android/iOS.
- PDF export, OS printing and advanced publishing features such as footnotes, section breaks, multi-column flow and floating document images.
- Advanced CSS-like layout features including named grid tracks, min-content/max-content sizing, flex shrink, subgrid, transforms/rotation and sticky positioning.
- An open-source license. The project currently documents its source distribution as proprietary.

These are limitations or possible future milestones, not commitments that have already been implemented.

## 13. How to maintain this register

For every future development batch:

1. Add the batch/version and date to the release history.
2. Add each new public component/API or runtime capability to the relevant inventory section.
3. Record behavior that is implemented separately from behavior that is only planned.
4. Add or update example paths and documentation links.
5. Record test counts and CI/build results only after they have actually run.
6. Move a limitation out of the unfinished section only after implementation and regression coverage exist; retain platform-validation caveats until those platforms are tested.
7. Update the recorded source baseline and review date.

This file is intended to be the central, cumulative implementation record. Release-specific README files and subsystem guides remain the detailed API references.
