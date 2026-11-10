# Native overlay system (2.4)

Yuktara UI 2.4 adds a native overlay manager above the retained application
layout. Overlay content remains ordinary `LayoutNode` content and is painted by
the same Skia renderer. No browser, DOM, CSS, WebView or platform-specific
popup window is created.

## Runtime entry point

The runtime owns the manager as `runtime.overlays` (also exposed as
`runtime.overlay_manager`). Add and remove surfaces through this manager:

```python
from novaui.native import (
    Button, ContextMenu, Dialog, MenuItem, NativeRuntime, Popover,
    Toast, Tooltip,
)

runtime = NativeRuntime(build_root, renderer, 900, 600)
runtime.start()

# Centered modal, scrim, Escape handling and outside-click dismissal.
dialog_handle = runtime.overlays.show_dialog(
    Dialog("Delete item?", "This action cannot be undone."),
    on_dismiss=lambda reason: print("dialog closed:", reason),
)

# Position relative to an already-laid-out control node.
popover_handle = runtime.overlays.show_popover(
    Popover("Additional details"), anchor=some_button_node,
    placement="bottom",  # bottom, top, left or right
)

# Passive tooltip; does not intercept pointer events.
tooltip_handle = runtime.overlays.show_tooltip(
    Tooltip("Save your changes"), anchor=some_button_node,
)

# Context menu at logical window coordinates; selecting an enabled item closes it.
menu_handle = runtime.overlays.show_context_menu(
    ContextMenu([MenuItem("Open", on_click=open_item), MenuItem("Rename", on_click=rename_item)]),
    position=(pointer_x, pointer_y),
)

# Toast notifications use the host-driven clock described below.
toast_handle = runtime.overlays.show_toast(Toast("Saved", variant="success"))
```

`show()` is also available for custom `LayoutNode` or buildable widget content.
It accepts `kind`, `anchor`, `position`, `placement`, `modal`, outside/Escape
dismissal flags, pointer-event participation, an optional duration and an
`on_dismiss(reason)` callback. Handles can be passed to `dismiss(handle)`;
`dismiss()` without a handle closes the topmost entry.

## Placement and interaction

- Dialogs are centered in a full-window overlay root. A translucent scrim is
  painted between the app tree and dialog surface. The modal root blocks input
  to the app underneath and can optionally dismiss on outside click or Escape.
- Popovers and tooltips use a `LayoutNode` or `Rect` anchor. Placement flips to
the opposite side when the preferred side would overflow, then clamps to the
window viewport.
- Context menus are positioned at logical window coordinates and clamped to
  the viewport. Disabled items are non-interactive; selecting an enabled item
  closes the menu after its callback returns.
- Tooltips and toasts are pointer-transparent. Other interactive overlays are
  hit-tested from front to back.
- Keyboard focus and Tab traversal are restricted to the top modal while one is
  active. Escape closes the top dismissible overlay; passive toasts/tooltips do
  not shield an underlying dialog from Escape.
- `build_accessibility_tree(root, overlays=runtime.overlays.roots)` includes
  active overlay semantics in a combined application semantic tree.

## Toast time source

The framework deliberately does not start a background timer. The host owns
its frame clock and advances it explicitly:

```python
runtime.advance_time(delta_seconds * 1000.0)
```

A `Toast` defaults to 3000 ms. Use `duration_ms=None` for a persistent toast,
then close it with its handle or `dismiss_all()`. Expiration invokes
`on_dismiss("timeout")` when a callback is provided. A host that only renders
on demand should call `runtime.advance_time(...)` from its own event/frame loop.

## Component shapes

`Dialog`, `Popover`, `Tooltip`, `ContextMenu`, `MenuItem` and `Toast` are
buildable widgets. They can be created with `build()` and passed as native
layout nodes when needed. Content and dialog action rows accept strings,
`LayoutNode` instances or objects with a `build()` method.

## Validation and platform limits

The overlay lifecycle, geometry, hit testing, keyboard handling, semantic tree
composition and paint order are covered by backend-injected tests. These tests
do not certify native window behavior on each OS. Real SDL3 + Skia rendering,
display scaling, accessibility provider integration and platform-specific
screen reader behavior still require validation on target systems.

## Dropdown integration

A `Dropdown` can use the runtime-owned overlay manager so its options float
above surrounding content, remain anchored to the control, flip/clamp to the
viewport and dismiss on outside click or Escape:

```python
period = Dropdown(("Daily", "Weekly", "Monthly"), value="Weekly")
runtime = NativeRuntime(build_root, renderer, 900, 600)
period.attach_overlay_manager(runtime.overlays)
runtime.start()
```

The option list is rendered in a bounded scroll view for long lists. Keyboard
Up/Down navigation and Enter/Space selection remain available. Selection,
outside dismissal, Escape and runtime teardown all close the overlay. For
backward compatibility, a dropdown without an attached manager continues to
use its inline option list; attaching the manager opts into the floating menu.
