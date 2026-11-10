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


## Yuktara design system

Yuktara's component language uses a shared semantic token system rather than
independent per-widget colors and measurements. The design direction combines
the systematic state and role model common to modern platform design systems
with restrained native typography, comfortable touch targets, quiet surfaces
and clear hierarchy. It is an original Yuktara implementation, not a copy of
Material 3 or Apple's proprietary assets.

### Theme tokens

`NativeTheme` is immutable and provides:

- **Color roles:** primary, secondary, tertiary, danger, warning, success,
  information, on-colors, outline, focus, inverse surfaces and disabled roles.
- **Surface scale:** lowest, low, base, high and highest container roles.
- **Shape scale:** extra-small through extra-large plus pill.
- **Spacing scale:** 4, 8, 12, 16, 20, 24, 32, 40 and 48 logical units.
- **Typography roles:** display, headline, title, body and label sizes.
- **Control metrics:** shared small, medium and large control heights and
  icon-button dimensions, with a 44-unit default touch target.
- **Dark palette:** `NativeTheme.dark()` supplies a complete matching semantic
  palette rather than simply inverting light colors.

Existing token names such as `primary`, `surface`, `radius_medium` and
`radius_large` remain supported. Components should consume semantic roles
from the supplied theme; avoid hard-coded colors, radii or arbitrary spacing
inside new widgets.

### Core component patterns

`Button` supports `primary`, `tonal`, `secondary`, `outline`, `text`,
`danger` and `success` variants. Small, medium and large sizes share the
theme's control metrics. Enabled buttons expose hover, pressed and keyboard
focus states; disabled buttons install no activation or pointer-state handlers.

`IconButton` requires a visible glyph and a separate accessible label. Its
standard, filled, tonal and outlined variants share the same button state
behavior and square target metrics.

`Surface` provides lowest, low, base, high, highest and outlined surface
roles. Use these roles to establish hierarchy before introducing custom colors
or borders. `Card` remains available as a compatibility-friendly content
container.

Text fields use the shared surface, outline and focus tokens. Status badges,
switches and buttons consume the shared typography and spacing scales.

### Usage

```python
from novaui.native import (
    Button, IconButton, NativeTheme, Surface, column, row,
)

theme = NativeTheme()
screen = Surface(
    variant="low",
    children=(
        row(
            Button("Continue", variant="primary", theme=theme),
            Button("Learn more", variant="text", theme=theme),
        ),
        IconButton("＋", "Create item", variant="tonal", theme=theme),
    ),
    theme=theme,
)
```

Run the interactive catalogue with `python examples/native/design_system_gallery.py`.
Use `--dark` to inspect the dark palette. The automated token and interaction
regressions are in `tests/native/test_design_system.py`.

### Rendering and platform boundaries

Elevation levels are semantic tokens today; the current CPU-raster renderer
does not yet provide a complete cross-platform shadow/elevation compositor.
The gallery and headless tests validate native component trees and states,
not certification against Android Material You, iOS UIKit, macOS AppKit or
assistive-technology platform bridges. Yuktara keeps its own component APIs
and visual identity while adopting familiar interaction conventions.


### Content and action components (3.10)

The component catalogue now includes:

- `FloatingActionButton`: small (48), regular (56) and large (96) action
  targets, plus an extended icon-and-label presentation. The accessible name
  remains the full action label in both forms.
- `Chip`: neutral, primary, success, warning, danger and information roles,
  with selected, disabled and optional activation semantics.
- `Avatar`: small through extra-large initials/glyph presentation with
  explicit accessible description and semantic color variants.
- `ListTile`: leading content, title, optional subtitle and trailing content,
  selected/disabled states, dense spacing and row-wide activation.

Examples:

```python
from novaui.native import Avatar, Chip, FloatingActionButton, ListTile

profile = Avatar("Asha Sharma", initials="AS", size="large")
filter_chip = Chip("Recently updated", selected=True)
create = FloatingActionButton("Create document", icon="+", extended=True)
row = ListTile(
    "Project files",
    subtitle="18 items",
    leading=Avatar("Project files", initials="P"),
    trailing=Chip("Synced", variant="success"),
)
```

The interactive design-system gallery demonstrates these components. Tests in
`tests/native/test_content_components.py` cover semantics, dimensions,
selection, disabled activation and composition.
