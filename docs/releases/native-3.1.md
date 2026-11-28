# Yuktara UI 3.1.0.dev0 — general-purpose native component library

This milestone fills out the general UI layer beyond the original input and
text controls. It adds reusable responsive layout, image display, data views,
navigation, date selection, hierarchical navigation and native file dialogs.

## Added in 3.1

- `Grid` with responsive column reflow, minimum track width and row/column gaps.
- `Container` with padding, margin, dimensions, background, border and radius.
- `ScrollView` with vertical, horizontal and two-axis clipping/scrolling.
- `Image` with Skia decoding for file paths and encoded image buffers, `contain`,
  `cover`, `fill` and `none` fit policies, rounded clipping and alt semantics.
- `Table` with headers, weighted columns, cell padding, borders and striping.
- `NavigationDrawer` with selected entries, compact mode, badges and callbacks.
- `Calendar` and expandable `DatePicker` with min/max date constraints.
- `TreeView` / `TreeItem` with expansion and selection semantics.
- `FilePicker` for open, save and folder dialogs using an SDL3-backed service.
- New integrated gallery: `examples/native/advanced_component_gallery.py`.

## Existing controls retained

Buttons, labels, cards, badges, dividers, progress bars, checkboxes, switches,
radio groups, text fields, text areas, dropdowns, sliders, tabs, segmented
controls, dialogs, popovers, tooltips, context menus, toast notifications,
rich text, paragraph formatting and document pagination remain in the package.

## Run

```bash
python -m pip install -e .
python -m novaui setup
python examples/native/advanced_component_gallery.py
python examples/native/advanced_component_gallery.py --image ./sample.png
```

See [`docs/native-component-library.md`](docs/native-component-library.md) for
APIs, file-picker callback behavior and current platform limitations.
