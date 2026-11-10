# Yuktara UI native changelog

## 3.3.0.dev0 — advanced layout engine

- Added per-node min/max width and height constraints and percentage dimensions.
- Added flex wrapping to rows and columns, with independent wrap spacing and
  per-line weighted sizing.
- Added flex basis, child-level cross-axis alignment and baseline alignment.
- Added absolute positioning with pixel/percentage edge offsets and
  edge-to-edge child stretching outside normal flow.
- Added grid row/column placement, spans, explicit-cell collision checks and
  stable auto-placement that reserves later explicit cells.
- Added high-level `GridItem` and `Positioned` widgets and extended `Container`
  with percentage sizing, constraints and positioning.
- Added a backend-neutral advanced-layout example and dedicated layout guide.
- Added 25 focused layout tests plus regression coverage for padding normalization
  and retained-tree reconciliation; full native suite now contains 283 tests.

## 3.2.0.dev0 — runtime and retained-tree stabilization

- Fixed retained-node reconciliation by deriving copied declarative fields from
  `LayoutNode` dataclass metadata, including visual, accessibility, layout and
  event callback properties; derived geometry is deliberately recomputed.
- Preserved live focus and scroll offsets across compatible rebuilds while
  invalidating stale text-layout caches.
- Kept the input dispatcher stable across rebuilds and pruned removed nodes
  from pointer capture, hover, touch-scroll and focus-history state.
- Bound runtime scheduler work to the UI owner thread. State-bound `apply`
  callbacks and rebuilds from worker threads are queued for `process_pending()`.
- Added explicit logical-window and backing-pixel size tracking with independent
  X/Y scales, normalized SDL touch-coordinate conversion and focus-loss reset.
- Added `SDL3Window.run_runtime()` to coordinate window sizing, event decoding,
  pending state flushes, animation time, frame presentation and teardown.
- Made runtime startup transactional when scheduler ownership cannot be bound,
  reset quit/focus state on same-thread restart, and preserved later queued
  scheduler callbacks when one callback raises.
- Enforced SDL window thread affinity for repeated open and close operations.
- Made runtime teardown/restart reattach overlay and animation callbacks, and
  guaranteed SDL window cleanup if runtime teardown raises.
- Added regression tests for reconciliation, UI-thread callbacks, focus history,
  touch scaling, DPI resize, focus loss, scheduler failure recovery, SDL thread
  affinity and integrated host-loop teardown.
- Updated earlier layout, reactivity, SDL host, retained-tree and rendering/input
  guides to describe current capabilities rather than obsolete limitations.
- Real SDL3/Skia integration on Windows, Linux and macOS remains a separate
  platform-validation requirement.

## 3.1.0.dev0 — general-purpose native component library

- Added responsive `Grid` layout with automatic column reflow based on available width.
- Added `Container`, `ScrollView` and native `Image` components.
- Added accessible `Table` composition with weighted columns, headers and row striping.
- Added selectable `NavigationDrawer`, `Calendar`, `DatePicker` and expandable `TreeView`.
- Added `FilePicker` for SDL3 open, save and folder dialogs.
- Marshalled asynchronous SDL3 file-dialog completions back to the window polling thread.
- Added an integrated advanced component gallery and component-library reference.
- Added coverage for responsive layout, accessibility semantics, date constraints, tree expansion and native dialog callback lifecycle.

## 2.1.0.dev1 — 2026-11-10

- Updated the SDL3 runtime baseline to 3.4.20.
- Updated the Skia Python runtime baseline to 144.1.
- Updated the pinned development test runner to pytest 9.2.0.
- Added SHA-256 verification for official SDL3 runtime downloads.
- Added Linux source-build provisioning and desktop backend prerequisite checks.
- Added automatic dependency bootstrap to standalone text measurement and font resolution.
- Removed the unused NumPy runtime dependency.
- Updated native setup documentation and the SDL3 + Skia smoke-test example.


## 2.2.0.dev0

- Added the first built-in native component library: labels, buttons, cards, badges, dividers, spacers and progress bars.
- Added interactive checkbox, switch and radio-group controls with live semantic state.
- Expanded the light/dark semantic theme palettes and shape tokens.
- Added border rendering to the Skia renderer and retained-tree painter.
- Added a backend-neutral accessibility semantic tree.
- Added an interactive native component gallery and component tests.


## 2.3.0.dev0

- Added TextField and TextArea with committed text, caret editing, deletion,
  navigation, basic selection replacement, validation and submit callbacks.
- Added Dropdown with inline options and keyboard selection.
- Added Slider with stepped values, pointer capture, keyboard control and
  custom Skia painting.
- Added Tabs/TabItem and SegmentedControl with keyboard navigation.
- Added focus management, Tab traversal, keyboard/text dispatch and repaint
  handling for the focused control and captured pointer.
- Added dedicated native input component gallery and docs.

## 2.4.0.dev0

- Added a runtime-owned overlay manager with stacked surfaces, handles and
  deterministic dismissal callbacks.
- Added centered modal dialogs with scrims, outside-click handling and Escape
  dismissal, including non-dismissible modal configuration.
- Added anchored popovers and passive tooltips with collision flipping and
  viewport clamping.
- Added pointer-positioned context menus with disabled items and automatic
  dismissal after item selection.
- Added status toasts with host-driven lifetime progression through
  `NativeRuntime.advance_time`.
- Integrated overlay hit testing, modal focus trapping, Escape routing, paint
  ordering and combined accessibility semantics.
- Added native overlay gallery, docs and backend-injected interaction tests.


## 2.5.0.dev0

- Added a deterministic AnimationManager/AnimationHandle API with linear and
  eased numeric property transitions, cancellation, completion callbacks and
  host-clock advancement.
- Added `NativeRuntime.animate`, animation lifecycle cleanup and reduced-motion
  behavior that immediately finishes active and future transitions.
- Added LayoutNode opacity and composited Skia save-layer opacity support, with
  inherited alpha fallback for injected renderers without layer compositing.
- Added visible native focus rings for keyboard-focused controls.
- Improved context-menu keyboard focus, Up/Down navigation and Enter/Space
  activation; restore previous focus after dismissing menus and modal dialogs.
- Scoped modal accessibility semantics to the active dialog, omitting obscured
  application controls while the modal is open.
- Added animation/accessibility gallery, documentation and backend-injected tests.


## 2.6.0.dev0

- Added per-grapheme font fallback runs across configured Noto Sans script,
  CJK, emoji and system fallback families when Skia glyph coverage probing is
  available.
- Connected real SkiaRenderer instances to a shared TextMeasurer in
  NativeRuntime so measurement and painting use the same font configuration.
- Added source-indexed TextCluster/TextLine/TextLayout geometry, caret mapping,
  pointer-to-offset mapping and per-line selection rectangles.
- Preserved trailing empty lines and source offsets during wrapping; added
  common grapheme segmentation for combining marks, emoji sequences, flags and
  Indic virama conjuncts.
- Reworked TextField/TextArea to paint caret and selection separately from
  content, support pointer-drag selection, measured caret scrolling, grapheme-
  safe deletion/navigation and Ctrl+Left/Right word movement.
- Added SDL3 UTF-8 OS clipboard APIs and optional Ctrl+C/Ctrl+X/Ctrl+V support
  through an injected clipboard service; focus changes start and stop SDL3
  committed text input for the owning window.
- Corrected SDL3 text-input event decoding to read the native UTF-8 pointer field,
  preserving non-ASCII committed text rather than treating it as a fixed-size
  inline byte array.
- Added text-editor gallery, documentation and multilingual editing/clipboard
  regression tests.


## 2.7.0.dev0

- Added an optional HarfBuzz shaping adapter with explicit font-file mapping
  for primary and fallback typefaces; the default runtime remains dependency-free.
- Added positioned glyph IDs, source cluster ranges, glyph offsets/advances and
  direction metadata to the native text layout pipeline.
- Used shaped advances for line measurement and wrapping, and mapped visual
  cluster geometry back to logical source offsets for caret and selection.
- Added Skia TextBlobBuilder-based positioned glyph rendering so shaped glyphs
  are not reshaped from the original Unicode string during painting.
- Added basic directional run segmentation and configurable paragraph base
  direction, with full Unicode Bidirectional Algorithm support documented as
  a remaining integration task.
- Added a shaping inspection example, dedicated documentation and tests for
  ligatures, RTL text, glyph rendering, font mapping and optional dependencies.


## 2.8.0.dev0

- Added a UAX #14-informed, dependency-free line-break policy for whitespace,
  tabs, zero-width break characters, soft hyphens, common hyphens/slashes, CJK
  ideographs and opening/closing punctuation.
- Preserved non-breaking spaces, narrow non-breaking spaces, non-breaking
  hyphens, word joiners and ZWJ glue when emergency wrapping is required.
- Added injectable line-break policy and public break-offset inspection.
- Added `TextStyleSpan`, `TextPaintRun` and `TextParagraph` models with stable
  source ranges and grapheme-boundary validation.
- Added the `RichText` widget for inline family, size, weight, color, background
  and underline styles in a single native text node.
- Extended paragraph metrics to account for larger inline font runs and
  selection geometry to return discontiguous visual rectangles.
- Added a rich-text paragraph gallery, documentation and paragraph-layout tests.


## 2.9.0.dev0

- Added immutable `ParagraphStyle` for per-paragraph start/center/end alignment,
  left/right indentation, first-line indentation, before/after spacing,
  additive line spacing, line-height overrides and native list markers.
- Connected paragraph styles to `RichText`, `LayoutNode`, `TextMeasurer` and
  the layout engine while preserving the historical positional `RichText` API.
- Added paragraph-aware wrapping so first-line indents reduce only the first
  line's available width.
- Extended `TextLine` and `TextParagraph` with measured horizontal/vertical
  geometry used by paint, caret positioning, pointer mapping and selection.
- Added hanging-indent marker rendering and paragraph-formatting examples.


## 3.0.0.dev0

- Added backend-neutral fixed-page document layout with A4 defaults, custom page
  dimensions and margins, and printable body geometry.
- Added `DocumentParagraph`, `PageBreak`, `PageTemplate` and immutable page and
  paragraph-fragment models.
- Added pagination for wrapped paragraphs while preserving original source
  offsets, measured text clusters, shaped runs and inline style spans.
- Added keep-together and keep-with-next grouping along with configurable
  widow/orphan line preferences and forward-progress handling for oversized
  blocks.
- Added left/center/right headers and footers with `{page}` and `{pages}`
  substitution after total page count is known.
- Added native `DocumentLayout.paint_page()` for Skia and renderer-compatible
  backends, including paragraph styles, inline runs and list markers.
- Added A4 raster document example, documentation and 13 pagination tests.
- Full justification, tab-stop leaders, tables, footnotes, section breaks and
  PDF export remain out of scope for this development milestone.
