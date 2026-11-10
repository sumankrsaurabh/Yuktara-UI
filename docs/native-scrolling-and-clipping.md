# Yuktara UI Native Scrolling and Clipping

Yuktara UI 2.x provides a backend-neutral scroll viewport through `LayoutNode.scroll`.

```python
from novaui.native.layout import LayoutNode, Size

items = LayoutNode.column(
    *(LayoutNode("box", height=64, intrinsic_size=Size(240, 64)) for _ in range(30)),
    spacing=8,
)
feed = LayoutNode.scroll(
    items,
    width=320,
    height=600,
    scroll_axis="vertical",  # vertical | horizontal | both
)
```

## Behavior

- The viewport keeps its declared or constrained size while measuring its child
  along the scrollable axis without a finite content limit.
- `content_size`, `max_scroll_x`, and `max_scroll_y` are populated during layout.
- `scroll_x` and `scroll_y` are clamped during arrange, including after a resize
  or content change.
- Descendants are painted inside a rectangular viewport clip. Nested scroll
  viewports create nested clip regions.
- Hit testing excludes descendants outside the viewport.
- Mouse wheel input scrolls the nearest scroll ancestor at 40 logical pixels per
  wheel unit. Touch drag scrolls in the opposite direction of the finger motion.
- A compact scrollbar thumb is painted when content overflows.

## Programmatic control

Set `scroll.scroll_y` or `scroll.scroll_x` and run layout again to clamp the new
position. A `NativeRuntime` automatically schedules a new frame for wheel and
active touch-motion events. The low-level `InputDispatcher` only updates the
node model; applications using it directly should request a frame themselves.

## Current limitations

- Scrollbar thumbs are visual indicators only; thumb dragging and track paging
  are not implemented yet.
- No inertial scrolling, overscroll physics, or scroll snapping yet.
- Content virtualization is not implemented; all child nodes are measured,
  arranged, and painted.
- Touch scrolling uses normalized pointer motion events; platform-specific
  gesture arbitration and multi-touch pinch behavior remain future work.
- Clipping depends on the renderer implementing `save`, `clip_rect`, and
  `restore`. The built-in Skia renderer implements these methods.
