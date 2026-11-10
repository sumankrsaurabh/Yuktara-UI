# Native component library — 2.2 development

Yuktara UI widgets are Python objects that build the framework's retained
`LayoutNode` tree. They do not paint directly and do not depend on SDL3 or Skia.
The existing layout engine, painter, hit tester, event dispatcher and renderer
continue to own those responsibilities.

## Basic composition

```python
from novaui.native import (
    Badge, Button, Card, Divider, Label, NativeTheme,
    ProgressBar, column, row,
)

theme = NativeTheme()
root = column(
    Label("Project overview", size=24, weight="bold", theme=theme),
    row(Badge("Online", "success", theme), Badge("Build 2.2", "primary", theme)),
    Card((
        Label("Build status", weight="semibold", theme=theme),
        ProgressBar(72, label="Build progress", theme=theme),
        Divider(theme=theme),
        Button("Open details", variant="primary", theme=theme),
    ), theme=theme),
    spacing=14,
    padding=20,
    background=theme.background,
)
```

A widget's `build()` returns a `LayoutNode`; composition helpers such as
`row`, `column` and `Card` accept either widgets or prebuilt layout nodes.

## Components

| Component | API / behavior |
|---|---|
| `Label` | Typography size, weight, color, wrapping, maximum lines and alignment. |
| `Button` | Primary, secondary, outline, ghost, danger and success variants; small, medium and large sizes; disabled state; click callback. |
| `Card` | Vertical content container with padding, spacing, surface color, radius and optional border. |
| `Badge` | Neutral, primary, success, warning, danger and info status treatments. |
| `Divider` | Horizontal or vertical separator with configurable thickness and color. |
| `Spacer` | Flexible empty space inside row and column layouts. |
| `ProgressBar` | Determinate 0–100% progress with track, fill and semantic value. |
| `Checkbox` | Toggle state, disabled state and `on_change(bool)` callback. |
| `Switch` | Toggle state, live track/knob update and `on_change(bool)` callback. |
| `RadioGroup` | Single selection, row/column direction and `on_change(value)` callback. |

The first component set deliberately avoids advertising a text input field before
the text editor has a complete keyboard, IME, selection and clipboard pipeline.
Text fields, dropdowns, sliders, dialogs, menus and floating overlays are
planned follow-on components.

## Themes

`NativeTheme()` provides the Yuktara light palette. `NativeTheme.dark()` provides
a corresponding dark palette. Both expose semantic ARGB tokens (surface,
foreground, muted, border, primary, success, warning, danger, info, disabled,
focus) and shape tokens for small, medium, large and pill radii.

## Accessibility semantics

Widgets annotate their nodes with semantic roles, labels, values, disabled
state and selection/toggle state. `build_accessibility_tree(root)` converts
those annotations to immutable `SemanticNode` values. This is a platform-neutral
semantic model; native OS bridges such as UI Automation, NSAccessibility and
AT-SPI are not implemented in this milestone.

## Interaction and rerendering

The input dispatcher invokes a widget's click callback on pointer-up when the
pointer is released over the same node that received pointer-down. Checkbox,
switch and radio-group nodes update their visible text/track/selection metadata
in place, so a normal frame render reflects the change. Application state can
be connected through the framework's `State` and `Component.bind_state` APIs.

## Gallery

Run `python examples/native/component_gallery.py` after `python -m novaui setup`
to open an interactive SDL3 + Skia sample gallery.

## Current scope

This is an initial component foundation, not a finished complete control suite.
The component model is backend-neutral and the gallery should be validated on
real Windows, Linux and macOS SDL3/Skia runtimes. OS screen-reader integration,
keyboard focus traversal for all controls, true overlay portals, and mobile
renderers remain future work.
