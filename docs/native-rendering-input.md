# Native rendering and pointer dispatch

## Paint a laid-out tree

```python
from novaui.native import SkiaRenderer, RenderSize
from novaui.native.layout import LayoutEngine, LayoutNode, Rect, Size
from novaui.native.rendering import LayoutTreePainter

root = LayoutNode.column(
    LayoutNode("text", text="Yuktara UI", font_size=24, text_color="#202735"),
    LayoutNode.box(intrinsic_size=Size(120, 48), background="#DCEBFF", radius=12),
    spacing=12,
    background="#FFFFFF",
)
LayoutEngine().layout(root, Rect(0, 0, 800, 600))
renderer = SkiaRenderer(RenderSize(800, 600))
LayoutTreePainter(renderer).paint(root, clear_color="#F5F7FA")
png = renderer.to_png_bytes()
```

`LayoutTreePainter` draws node backgrounds and text, then paints descendants above parents. Colors accept ARGB integers or `#RGB`, `#RRGGBB`, and `#AARRGGBB` strings. It uses the renderer's Inter-first font configuration. Text baseline placement is currently approximate.

## Pointer dispatch

Attach callbacks to nodes (`on_click`, `on_pointer_down`, `on_pointer_up`, `on_pointer_move`, `on_pointer_enter`, `on_pointer_leave`, `on_wheel`) and pass normalized events from `SDL3Window.poll_input_events()` to `InputDispatcher.dispatch(event)`. Callbacks receive the `InputEvent`. Click fires only if press and release target the same node. Mouse and touch pointer identities remain separate.

## Limitations

This milestone paints solid backgrounds and text only; borders, shadows, clipping, opacity, image drawing and text wrapping are future work. Dispatch is target-based (no ancestor bubbling, capture phase, gesture arena or keyboard focus yet). Native SDL3/Skia runtime remains optional and was not exercised in the test environment.
