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

The tree painter supports backgrounds, rounded corners, borders, inherited
opacity, focus rings, clipping, scroll viewports and scroll indicators. Text
nodes use a configured `TextMeasurer` for measured wrapping, inline style runs,
paragraph styles, source-indexed selection geometry and caret placement. Image
nodes use `SkiaRenderer.draw_image()` with contain, cover, fill and native-size
fit modes. Skia rendering is CPU-rasterized and coordinates are logical pixels;
`RenderSize` scales the backing raster surface.

## Pointer and keyboard dispatch

Attach callbacks to nodes (`on_click`, pointer callbacks, `on_wheel`, keyboard
and text-input callbacks) and dispatch `InputEvent` instances through
`InputDispatcher` or `NativeRuntime`. Pointer-down captures the target through
pointer-up. Click fires only when press and release target the same node.
Mouse and touch pointer identities remain distinct. Keyboard focus supports
Tab/Shift+Tab and Enter/Space activation for focusable controls. The dispatcher
also routes context-menu navigation and integrates overlay hit testing.

## Current limitations

The input system is target-oriented and does not yet implement a full
capture/target/bubble event propagation model, gesture arena, drag-and-drop
recognizer or platform accessibility bridge. The renderer does not yet provide
a GPU-backed Skia surface, shadows/effects pipeline or dirty-region compositor.
Full IME pre-edit composition and candidate-window placement remain open work.
Real SDL3/Skia rendering and event behavior must be smoke-tested on each target
operating system.
