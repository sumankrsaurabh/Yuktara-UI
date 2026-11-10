# Yuktara UI native layout engine

The first native layout milestone is a backend-neutral, two-phase measure/arrange engine. It is deliberately isolated under `novaui.native.layout`; it belongs to the native-only Yuktara UI source package and does not depend on a DOM or browser runtime.

## Quick start

```python
from novaui.native.layout import LayoutEngine, LayoutNode, Insets, Rect, Size

title = LayoutNode("text", text="Dashboard")
sidebar = LayoutNode.box(intrinsic_size=Size(220, 500))
content = LayoutNode.box(weight=1, intrinsic_size=Size(400, 500))
page = LayoutNode.row(sidebar, content, spacing=16, padding=Insets.all(20))

engine = LayoutEngine()
engine.layout(page, Rect(0, 0, 1280, 720))
print(content.bounds)
```

## Supported primitives

- `box`: one child, optional intrinsic size, padding and child alignment.
- `row` / `column`: linear layout, spacing, weighted children, main-axis distribution and cross-axis alignment.
- `stack`: overlay children, with shared alignment.
- `text`: intrinsic-size placeholder. Supply `intrinsic_size` from a real font measurer for accurate text layout.

All dimensions are logical pixels. `Constraints` support min/max bounds. Layout is split into `measure()` and `arrange()`; `layout()` performs both. `hit_test()` returns the deepest topmost arranged node.

## Current limitations

This is a foundation, not yet a complete production layout system. Percentage dimensions, baseline alignment, text wrapping, min/max per-node dimensions, scroll viewports, clipping, grid, absolute positioning, intrinsic text measurement and device-scale conversion are not implemented. The simple text fallback (8 px per character, 18 px line height) is only a deterministic placeholder. SDL3/Skia are not needed to run layout tests.
