# Native animation and accessibility — 2.5

Yuktara UI 2.5 adds a deterministic animation timeline and improves focus and
assistive-technology semantics without adding a browser runtime, timers or
worker threads.

## Animating a retained node

```python
from novaui.native import NativeRuntime, Button, column

panel = Button("Animated panel").build()
runtime = NativeRuntime(lambda: column(panel), renderer, 640, 400)
runtime.start()

runtime.animate(
    panel,
    "opacity",
    0.0,
    duration_ms=240,
    easing="ease_out_cubic",
    on_complete=lambda: print("fade completed"),
)

# Call this from the platform host's frame loop using elapsed milliseconds.
runtime.advance_time(frame_delta_ms)
```

`NativeRuntime.animate(target, attribute, to_value, ...)` animates any numeric
attribute. The standard easing names are `linear`, `ease_in`, `ease_out`,
`ease_in_out` and `ease_out_cubic`. A new animation targeting the same object
and attribute replaces the previous one. `runtime.animations.cancel(handle)`
cancels an animation; `finish=True` applies its final value and invokes its
completion callback. `finish_all()` applies all endpoints; `cancel_all()`
discard animations without applying endpoints.

`LayoutNode.opacity` must remain in the range 0..1; the constructor and animation API validate the initial value and animation target. Skia renderers
composite a node subtree through a save-layer, including its custom-painted
children. Compatible injected renderers that do not implement `save_layer`
receive inherited alpha on regular fills, borders and text as a fallback.
Custom paint callbacks should use the renderer's current canvas/layer when the
renderer supports compositing.

## Reduced motion

Pass `reduced_motion=True` to `NativeRuntime`, or update the preference later:

```python
runtime.set_reduced_motion(True)
```

Enabling reduced motion immediately finishes current animations and makes new
animations apply their final values without interpolation. The platform host
is responsible for reading the operating-system preference and passing it to
the runtime; the core does not query OS settings itself.

## Keyboard focus

Focusable controls show a two-pixel focus ring when the renderer supports
stroke rectangles. `LayoutNode.focus_ring_color` and
`LayoutNode.focus_ring_width` are configurable. Text fields retain their own
focused border in addition to the general focus ring.

Context menus receive initial focus on their first enabled item. Up and Down
move between enabled items, and Enter/Space invokes the focused item. Closing a
menu restores the previously focused control where possible. Closing a modal
restores the control that had focus before the modal opened.

## Modal accessibility scope

`build_accessibility_tree(root, overlays=runtime.overlays.roots)` includes
active overlay semantics. While a modal dialog is active, its overlay becomes
the only child scope exposed under the application semantic root; obscured
background controls are omitted. When the modal closes, the normal application
semantics return.

This is a backend-neutral semantic model, not an OS accessibility provider.
Windows UI Automation, macOS NSAccessibility and Linux AT-SPI adapters, native
screen-reader testing, text-input IME composition and clipboard integration
remain platform integration work.

## Host frame loop

The host owns timing. Compute the elapsed time between frames and pass it to
`runtime.advance_time(delta_ms)`. That method advances both animations and
expiring overlays. It does not sleep, start a timer or create another thread.
