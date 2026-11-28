# Yuktara UI 3.3.0.dev0 — advanced layout engine

Yuktara UI 3.3 expands the native measure/arrange system with practical
responsive and positioning features for application interfaces.

## Main changes

- Added min/max width and height constraints to layout nodes.
- Added percentage-based width, height, min/max constraints and absolute edge
  offsets, resolved against finite parent constraints.
- Added `row(..., wrap=True)` and `column(..., wrap=True)` with independent
  cross-axis line spacing and weighted allocation per line.
- Added `flex_basis`, `align_self`, cross-axis content alignment and baseline
  alignment through `Alignment.BASELINE` or an explicit node baseline.
- Added absolute positioning with left/right/top/bottom offsets, edge-to-edge
  stretching and exclusion from normal-flow intrinsic measurement.
- Added GridItem placement, row/column spanning, collision checks and stable
  auto-placement that reserves explicit cells first.
- Added high-level `Positioned` and `GridItem` widgets, plus percentage and
  min/max support in `Container`.
- Added 25 focused layout tests for constraints, percentages, wrapping,
  weighted lines, baseline alignment, absolute positioning and grid spans.

## Example

```bash
python examples/native/advanced_layout.py
```

See [`docs/native-advanced-layout.md`](docs/native-advanced-layout.md) and
[`docs/native-layout-engine.md`](docs/native-layout-engine.md) for API details.

## Verification

The complete backend-injected native test suite currently runs with:

```bash
python -m pytest -q tests/native
```

This does not certify SDL3/Skia rendering across Windows, Linux and macOS.
Real desktop/DPI validation remains a separate release requirement.
