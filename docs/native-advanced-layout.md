# Advanced native layout — Yuktara UI 3.3

Yuktara UI 3.3 expands the measure/arrange engine without changing the SDL3 +
Skia rendering architecture.

## Responsive dimensions

```python
from novaui.native import Container, Label, column

content = column(
    Label("Responsive content"),
    Container(
        child=Label("75% width, constrained"),
        width="75%", min_width=280, max_width=720,
        padding=16,
    ),
    spacing=12,
)
```

Percentages resolve against finite parent constraints. A percentage on an
unbounded axis falls back to the child's intrinsic size.

## Flex wrapping and baseline alignment

```python
from novaui.native import Alignment, Badge, Button, row

chip_row = row(
    Badge("Native"), Badge("Responsive"), Badge("SDL3"),
    Button("Continue"),
    wrap=True,
    spacing=8,
    wrap_spacing=10,
    cross_align=Alignment.CENTER,
)
```

Use `column(..., wrap=True)` to form additional columns when the available
main-axis height is exhausted. Weighted children expand within their own flex
line. `cross_align=Alignment.BASELINE` is available for rows containing text.

## Grid spans

```python
from novaui.native import Grid, GridItem, Label

grid = Grid(
    [
        GridItem(Label("Wide card"), row=0, column=0, column_span=2),
        GridItem(Label("Side card"), row=0, column=2),
        Label("Auto-placed card"),
    ],
    columns=3,
    column_gap=12,
    row_gap=12,
)
```

Grid coordinates are zero-based. Unpositioned items use stable row-major
auto-placement and skip all explicit occupied cells. Overlapping explicit cells
are rejected instead of rendering ambiguously.

## Absolute positioning

```python
from novaui.native import Container, Label, Positioned, stack

panel = stack(
    Container(child=Label("Panel content"), padding=20),
    Positioned(
        Label("NEW"), right=12, top=12,
        width=64, height=24,
    ),
)
```

Offsets are relative to the parent's content box. Absolute children do not
contribute to normal-flow intrinsic sizing. If both opposing edges are given
and no explicit size is supplied, the child stretches between those edges.

## Low-level layout properties

`LayoutNode` exposes `min_width`, `max_width`, `min_height`, `max_height`,
`flex_wrap`, `wrap_spacing`, `flex_basis`, `align_self`, `position`, edge offsets,
`grid_row`, `grid_column`, `grid_row_span` and `grid_column_span`.

Run the deterministic backend-neutral layout tests with:

```bash
python -m pytest -q tests/native/test_advanced_layout.py
```

These tests validate the layout model, not real desktop rendering. The native
SDL3 and Skia integrations still require testing on each supported operating
system and DPI configuration.
