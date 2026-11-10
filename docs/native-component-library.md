# Yuktara UI native component library — 3.1 development

Yuktara UI components are Python objects that produce a retained `LayoutNode`
tree. Layout, painting, hit testing, event dispatch, animation and accessibility
remain owned by the native framework. Components do not embed HTML, CSS,
JavaScript, a browser or a WebView.

## Public component catalog

### Layout and composition

| API | Purpose |
|---|---|
| `row(...)` | Horizontal composition with spacing, alignment and weighted children. |
| `column(...)` | Vertical composition with spacing, alignment and weighted children. |
| `stack(...)` | Layer multiple children in the same layout area. |
| `Container(...)` | Generic content container with padding, margin, dimensions, fill, border and radius. |
| `Card(...)` | Themed content surface. |
| `Grid(...)` | Equal-track grid; `min_column_width` allows responsive column reflow. |
| `ScrollView(...)` | Clipped vertical, horizontal or two-axis scrolling viewport. |
| `Spacer(...)` | Flexible or fixed empty space. |
| `Divider(...)` | Horizontal or vertical separator. |

### Input and action controls

`Button`, `TextField`, `TextArea`, `Checkbox`, `Switch`, `RadioGroup`,
`Dropdown`, `Slider`, `Tabs`, `TabItem`, `SegmentedControl` and `DatePicker`
are available. They expose native node semantics and their respective callbacks.

### Data, navigation and hierarchy

| API | Purpose |
|---|---|
| `Table(...)` | Header/body rows with weighted columns, cell padding, borders, stripes and table semantics. |
| `NavigationDrawer(...)` | Selectable navigation entries, optional header/footer, badges and compact mode. |
| `TreeView(...)` / `TreeItem(...)` | Expandable and selectable hierarchical items, including disabled entries. |
| `Calendar(...)` | Month view with previous/next navigation and min/max date constraints. |

### Visual and system integration

| API | Purpose |
|---|---|
| `Image(...)` | Native Skia image view from a path, encoded bytes or decoded Skia image; `contain`, `cover`, `fill` and `none` fitting. |
| `FilePicker(...)` | Button integration for open, save and folder selection through an injected dialog service. |
| `Dialog`, `Popover`, `Tooltip`, `ContextMenu`, `Toast` | Native floating surfaces and notifications. |
| `Label`, `RichText`, `Badge`, `ProgressBar` | Text and status presentation. |

## Example

```python
from novaui.native import (
    Button, Calendar, Container, DatePicker, Grid, Image,
    NavigationDrawer, NavigationItem, ScrollView, Table,
    TreeItem, TreeView, column, row,
)

sidebar = NavigationDrawer([
    NavigationItem("Home", key="home"),
    NavigationItem("Settings", key="settings"),
], selected="home")

cards = Grid(
    [Container(child=Button(f"Open {index}"), padding=12)
     for index in range(6)],
    columns=3,
    min_column_width=180,
    column_gap=12,
    row_gap=12,
)

page = row(
    sidebar,
    ScrollView(column(
        cards,
        Table(headers=("Name", "Role"), rows=(("Ada", "Engineer"),)),
        DatePicker(),
        Calendar(),
        TreeView([TreeItem("Documents", children=(TreeItem("Report"),))]),
        spacing=16,
    ), height=720),
    spacing=16,
)
```

## Responsive grid behavior

`Grid.columns` is the maximum number of columns. When `min_column_width` is
provided and the parent supplies a finite width, the layout engine chooses the
largest column count that fits the requested minimum width and configured gap.
Without `min_column_width`, the requested `columns` value is used.

## Image behavior

`Image.source` accepts a filesystem path, encoded image bytes, or an already
decoded Skia image object. The renderer decodes encoded data using Skia and
caches path-backed images by path, modification time and file size. The `alt`
property supplies the accessibility label. Image decoding/painting requires the
Skia runtime to be installed.

## File picker integration

Pass an `SDL3Window` (or a compatible service object) to `FilePicker`:

```python
picker = FilePicker(
    window,
    mode="open",              # "open", "save" or "folder"
    filters=(("PDF files", "pdf"),),
    on_change=lambda paths: print(paths),
)
```

SDL3 file dialogs are asynchronous. `SDL3Window` retains the C callback and
marshals the completed paths to the window/event-polling thread. Results are
delivered during `poll_events()` / `poll_input_events()` or by explicitly
calling `process_file_dialog_results()` on the window thread. The SDL3 native
file-dialog APIs require SDL 3.2 or newer; Yuktara's pinned runtime is newer.
Cancellation is reported as an empty path tuple; an SDL error is reported as
`None` and can be handled through `FilePicker.on_error`.

## Gallery

Run `python examples/native/advanced_component_gallery.py` after
`python -m novaui setup`. Add `--image PATH` to preview an image with the native
`Image` component. The gallery includes grid, containers, tables, navigation,
tree, calendar, date picker and native file dialogs.

## Scope and validation

This is an experimental desktop component library, not a claim that every
platform integration is production-certified. Headless tests exercise component
construction, layout, accessibility semantics and injected renderer/dialog
services. Validate actual Skia image decoding/painting, SDL3 dialogs, window
scaling, accessibility provider bridges and input behavior on each supported OS.
Native accessibility semantics are represented in Yuktara's semantic tree;
UI Automation, NSAccessibility and AT-SPI provider bridges are separate work.
Mobile renderers are not included.
