# Yuktara UI native layout engine

The native layout engine is a backend-neutral, two-phase measure/arrange system
under `novaui.native.layout`. It operates in logical window pixels; the active
renderer applies the backing-surface scale when rasterizing.

## Quick start

```python
from novaui.native.layout import LayoutEngine, LayoutNode, Insets, Rect, Size

sidebar = LayoutNode.box(intrinsic_size=Size(220, 500), max_width=280)
content = LayoutNode.box(weight=1, min_width=240, intrinsic_size=Size(400, 500))
page = LayoutNode.row(sidebar, content, spacing=16, padding=Insets.all(20))

engine = LayoutEngine()
engine.layout(page, Rect(0, 0, 1280, 720))
print(content.bounds)
```

## Supported primitives

- `box`: one normal-flow child plus optional absolute-positioned overlays,
  intrinsic size, padding, per-node constraints and child alignment.
- `row` / `column`: fixed and percentage dimensions, min/max constraints,
  spacing, weighted children, main-axis distribution, cross-axis alignment,
  baseline alignment and optional flex wrapping.
- `stack`: overlays flow children in a shared alignment area and supports
  absolute-positioned children.
- `scroll`: vertical, horizontal or two-axis scroll viewport with clamped
  offsets, clipping and calculated scroll extents.
- `grid`: responsive equal-width tracks, automatic placement, explicit row and
  column placement, row/column spans and independent track gaps.
- `text`: measured text when a `TextMeasurer` is supplied, including wrapping,
  inline styles, paragraph styles, line-height and source-indexed geometry.

## Dimensions and constraints

`width`, `height`, `min_width`, `max_width`, `min_height` and `max_height`
accept non-negative logical-pixel numbers or percentage strings, for example
`width="50%"`. Percentages resolve against the corresponding finite parent
constraint. If the parent extent is unbounded, a percentage dimension falls
back to intrinsic measurement. A min/max pair that resolves to an invalid range
raises `ValueError` during measurement.

## Flex layout

`row(..., wrap=True, wrap_spacing=12)` wraps children into additional rows.
`column(..., wrap=True, wrap_spacing=12)` wraps into additional columns. The
existing `weight` property distributes remaining main-axis space independently
within each line. `flex_basis` sets the starting main-axis size for a weighted
child. `align_self` overrides the parent's cross-axis alignment for one child.
`Alignment.BASELINE` aligns row children by their first text baseline or an
explicit `LayoutNode(baseline=...)` value.

## Absolute positioning

Set `position="absolute"` and provide any of `left`, `right`, `top` and
`bottom`. Offsets may be pixels or percentages relative to the parent's content
box. Supplying both horizontal edges without an explicit width stretches the
child between them; the same rule applies vertically. Absolute children are
excluded from the parent's normal-flow intrinsic size and painted/hit-tested in
their retained child order.

The high-level `Positioned(child, left=..., top=...)` widget builds the same
layout node for application code.

## Grid placement

`GridItem(child, row=0, column=0, column_span=2, row_span=1)` places a child in
explicit zero-based tracks. Children without coordinates use stable row-major
auto-placement. Explicit cells are reserved before auto-placement, and
intersecting explicit cells raise `ValueError`. Row spans distribute any
additional required height across the covered rows. The `Grid` widget exposes
this as a component-level API.

## Hit testing and limitations

`hit_test()` returns the deepest topmost arranged node. Scroll viewports are
clipped by the native tree painter and can be driven by wheel or touch gestures.

This remains an experimental layout engine, not a full CSS Grid/Flexbox
implementation. Named grid tracks, intrinsic min-content/max-content sizing,
flex shrink factors, advanced baseline tables, transforms/rotation, sticky
positioning, subgrid and constraint-based breakpoint rules are not included.
Intrinsic text measurement requires a configured `TextMeasurer`; without one,
text uses a deterministic fallback size. SDL3/Skia are not needed to run the
layout tests.
