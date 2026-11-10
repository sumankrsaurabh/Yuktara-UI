# Native input components (2.3)

Yuktara UI 2.3 adds native text entry, selection, range control and tab
navigation. These components create ordinary `LayoutNode` instances and use
the shared layout engine, painter, normalized SDL3 events and accessibility
semantics.

## TextField

```python
from novaui.native import TextField

name = TextField(
    value="",
    placeholder="Your name",
    width=280,
    on_change=lambda value: print("name:", value),
    on_submit=lambda value: print("submitted:", value),
)
root = name.build()
```

Supported editing operations include committed text input, Backspace/Delete,
Left/Right, Home/End, Ctrl+A, Shift+Arrow selection replacement and Enter to
submit. `max_length`, `disabled` and `read_only` are supported. Input-method
pre-edit composition, OS clipboard integration, visual selection highlighting
and shaped-glyph hit testing are separate follow-up work.

## TextArea

`TextArea` shares the TextField editing model and enables newlines, wrapping and
basic Up/Down line navigation. Its default height is 128 logical pixels.

```python
from novaui.native import TextArea

notes = TextArea("", placeholder="Write notes...", height=160)
```

## Dropdown

```python
from novaui.native import Dropdown

period = Dropdown(
    ("Daily", "Weekly", "Monthly"),
    value="Weekly",
    on_change=lambda value: print(value),
)
```

The trigger toggles an inline option list. Enter/Space opens it; Up/Down
changes the active option; Enter selects; Escape closes. The 2.4 overlay manager
is available for application-built floating surfaces, but Dropdown has not yet
been migrated from its inline option-list implementation.

## Slider

```python
from novaui.native import Slider

zoom = Slider(value=70, minimum=0, maximum=100, step=5, label="Zoom")
```

The slider supports pointer dragging, keyboard arrows, Home/End, disabled
state and semantic values. Drag capture continues while the pointer moves
outside the original slider bounds.

## Tabs and SegmentedControl

```python
from novaui.native import Tabs, TabItem, Label, SegmentedControl

tabs = Tabs((
    TabItem("General", Label("General settings")),
    TabItem("Advanced", Label("Advanced settings")),
), value="General")

layout = SegmentedControl(("Day", "Week", "Month"), value="Week")
```

Tabs accept labels, native widgets or `LayoutNode` content. Left/Right selects
adjacent enabled tabs. SegmentedControl is a mutually-exclusive horizontal
selection with arrow-key navigation.

## Keyboard focus and repaint

`InputDispatcher` now tracks focus, handles Tab/Shift+Tab traversal, forwards
KEY_DOWN and TEXT_INPUT to the focused control, and activates focused clickable
controls with Enter/Space. Pointer-down captures a target until pointer-up so
drag controls continue receiving motion. `NativeRuntime` repaints after key,
text and captured-pointer changes.

## Validation and platform limits

The component tests use injected normalized events and a recording renderer.
They verify the Python widget and event-routing behavior, not native operating
system text services. SDL3 ABI/event structure validation and real Skia/SDL3
window testing remain platform-integration tasks.
