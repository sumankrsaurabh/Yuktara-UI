# Yuktara UI native reactivity and runtime lifecycle

This milestone adds pure-Python state, scheduling and component lifecycle primitives under `novaui.native.reactivity`, plus a small orchestration class at `novaui.native.runtime.NativeRuntime`.

## Observable state

```python
from novaui.native.reactivity import State

count = State(0)
subscription = count.subscribe(lambda new, old: print(old, "->", new))
count.update(lambda value: value + 1)
subscription.cancel()
```

`State` suppresses notifications when equality says the value has not changed. A subscription can be cancelled directly or used as a context manager.

## Batching

```python
from novaui.native.reactivity import Scheduler, State

scheduler = Scheduler()
with scheduler.batch():
    # Components using this scheduler are invalidated once per component,
    # even if several bound states change during this batch.
    state_a.value = 10
    state_b.value = 20
```

The scheduler deduplicates pending callbacks by key and flushes at the end of the outermost batch.

## Component lifecycle

A `Component` owns a builder, its current layout node and state subscriptions. `mount()` builds it; `bind_state()` subscribes to a state and invalidates/rebuilds the component when it changes; `unmount()` cancels subscriptions.

## Runtime orchestration

```python
from novaui.native import NativeRuntime, SkiaRenderer, RenderSize
from novaui.native.layout import LayoutNode, Rect, Size
from novaui.native.reactivity import State

message = State("Ready")
renderer = SkiaRenderer(RenderSize(800, 600))
app = NativeRuntime(
    lambda: LayoutNode.column(
        LayoutNode("text", text=message.value, font_size=24),
        background="#FFFFFF",
        padding=16,
    ),
    renderer,
    800,
    600,
)
app.component.bind_state(message)
app.start()
# message.value = "Updated" triggers rebuild, layout and paint.
```

`NativeRuntime` coordinates build -> layout -> paint, maintains an input dispatcher for the current tree, and supports resize, event dispatch and stop. It accepts any renderer implementing `clear`, `draw_rect` and `draw_text`, so lifecycle tests do not require Skia.

## Current boundaries

- State is synchronous and intended for the UI thread; it is not a cross-thread UI dispatcher.
- A component rebuild currently replaces its complete layout subtree. Fine-grained reconciliation and keyed diffing are future work.
- Scheduler batching deduplicates component rebuilds, but this is not yet a full frame clock or animation scheduler.
- The runtime does not create an SDL3 window or present frames itself; the SDL3 host remains a separate platform layer.
- The retained `novaui` Python import namespace is used for compatibility while the product is branded Yuktara UI.
