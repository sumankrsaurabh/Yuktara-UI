# Native platform parity and desktop adaptation roadmap

This document compares the current Yuktara UI native baseline with capabilities
expected from mature adaptive UI toolkits such as Jetpack Compose, Flutter and
Qt. It is an engineering gap register, not a claim of feature parity.

## 1. Desktop window and display lifecycle

| Capability | Yuktara UI baseline | Required target |
|---|---|---|
| Continuous window resize | SDL resize events feed runtime resize | Coalesce high-frequency resize events and validate no stale frames |
| Logical vs physical size | Separate UI and backing-pixel dimensions | Keep this invariant across every backend |
| Mixed-DPI monitor migration | Re-query display scale and pixel size | Real Windows/macOS/Linux validation with different monitor scales |
| Resolution changes | Recreate Skia raster surface | Validate repeated changes, minimized/restored windows and mode transitions |
| Aspect-ratio mismatch | Aspect-fit letterboxing by default | Never distort; render at current viewport and letterbox only transient mismatches |
| Refresh-rate awareness | Active display refresh metadata and SDL VSync request | Measure actual frame times and test 60/75/90/120/144/165/240 Hz |
| Presentation pacing | VSync where supported; no extra sleep while synchronized | Adaptive pacing, missed-vblank diagnostics and configurable frame policy |
| Multi-window | Not a complete multi-window application lifecycle | Independent window/runtime/render resources and per-window display metrics |

## 2. Adaptive composition parity

Jetpack Compose's adaptive guidance expects applications to react to runtime
window resizing, split-screen and desktop windowing—not merely device classes.
Yuktara currently has width-threshold Responsive variants, wrapping and
responsive grids. The following are still missing or incomplete:

- A first-class WindowSizeClass model with compact, medium and expanded
  width classes plus height classes.
- Window posture/orientation and usable-area information.
- Canonical adaptive scaffolds: navigation rail/bar/drawer, list-detail,
  supporting pane and multi-pane layouts.
- A stable adaptive navigation API that preserves selection and back-stack state
  while moving between navigation modes.
- Insets and safe-area handling for desktop window decorations and future mobile
  backends.
- Reflow tests across a viewport matrix, including very short and very wide
  windows, not only width breakpoints.

## 3. Rendering and visual quality

Current rendering is CPU-raster Skia uploaded to an SDL streaming texture.
That is a valid deterministic baseline, but it is not equivalent to a modern
GPU-backed compositor.

Priority gaps:

1. GPU-backed Skia surfaces and explicit graphics-device/context lifecycle.
2. Dirty-region rendering and retained display-list caching.
3. Frame-time instrumentation (layout, paint, raster, upload, present).
4. Texture/image cache budgets, decode scheduling and high-DPI asset selection.
5. Subpixel text positioning and pixel snapping rules for 1x/1.25x/1.5x/2x.
6. Color-space and HDR policy; do not silently claim HDR support.
7. Resize stress tests that verify output dimensions, no anisotropic scaling,
   no stale snapshots and no quality loss after repeated DPI transitions.

The renderer must always draw a fresh frame into a surface matching the actual
backing pixel size. Upscaling an old frame is not an acceptable substitute.

## 4. Text and input

The repository already has native text editing, selection, clipboard and an
initial IME composition path. Important remaining gaps include complete Unicode
bidirectional layout, Arabic joining, Indic shaping and ligature-aware caret
geometry; full Unicode grapheme and line-break conformance; physical keyboard
and IME validation across operating systems; drag/drop and richer selection
semantics; and robust accessibility announcements for text changes.

## 5. Accessibility

Yuktara has a backend-neutral semantic tree, but no certified operating-system
provider bridge. Production parity requires Windows UI Automation, macOS
NSAccessibility and Linux AT-SPI adapters, action dispatch, live-region events,
native focus notifications and screen-reader testing with real assistive
technology.

## 6. Window/display acceptance matrix

Before calling desktop display support production-ready, run the following
on real hardware:

- 100%, 125%, 150%, 175% and 200% display scaling.
- Two monitors with different scale factors; move the window across the boundary.
- 1280x720, 1920x1080, 2560x1440 and 3840x2160 output modes.
- 60, 75, 90, 120, 144, 165 and 240 Hz where available.
- Resize continuously, maximize/restore, minimize/restore and change display
  resolution while the app is running.
- Verify logical layout bounds, backing surface dimensions, pointer mapping,
  text sharpness, image sharpness, frame pacing and resource release.
- Verify that aspect-ratio mismatches letterbox and never stretch content.
- Capture frame-time percentiles and confirm no unbounded CPU busy-loop.

## 7. Release gates

Do not describe Yuktara UI as equivalent to Compose, Flutter or Qt until the
adaptive composition, GPU rendering, text, accessibility and physical display
validation gaps above are closed. Keep implementation status and platform
certification status separate in release notes.


## Progress update: adaptive window foundation

The development branch now provides `WindowAdaptiveInfo`, independently
classifies logical window width and height, exposes compact/medium/expanded/
large/extra-large width classes, and updates `NativeRuntime.adaptive_info`
after a resize. The SDL runtime host coalesces resize and DPI events per event
batch and skips identical runtime resizes. This closes the initial window-size
classification gap, but adaptive navigation scaffolds, state-preserving
navigation transitions, multi-pane layouts and physical-device validation are
still open work.
