# Yuktara UI native reactivity and runtime lifecycle

This module provides pure-Python state, a keyed invalidation scheduler,
component lifecycle primitives and `NativeRuntime` orchestration.

## Observable state

```python
from novaui.native.reactivity import State

count = State(0)
subscription = count.subscribe(lambda new, old: print(old, "->", new))
count.update(lambda value: value + 1)
subscription.cancel()
```

`State` suppresses notifications when equality says a value has not changed.
Subscriptions can be cancelled directly or used as context managers.

## Batching and scheduler ownership

```python
from novaui.native.reactivity import Scheduler, State

scheduler = Scheduler()
a = State(0)
b = State(0)
with scheduler.batch():
    a.value = 10
    b.value = 20
```

A standalone scheduler is synchronous by default. `NativeRuntime.start()` binds
its scheduler to the thread that owns the native window. State changes on that
thread rebuild synchronously; worker-thread state changes queue work until the
host calls `runtime.process_pending()` on the UI thread. `bind_state(...,
apply=...)` callbacks are marshalled through the same scheduler. Calling
`flush()` from a non-owner thread raises `RuntimeError`. If a scheduled callback
raises, later callbacks from the drained batch remain queued for the next flush.

## Component lifecycle and retained-tree reconciliation

A `Component` owns its builder, current `LayoutNode` and state subscriptions.
`mount()` builds and reconciles its node tree; `bind_state()` subscribes to a
state; `unmount()` deactivates bindings and cancels subscriptions. Compatible
keyed nodes are updated in place. Declarative fields and callbacks are refreshed
from the next build, while live focus and scroll offsets are retained. Derived
layout geometry is invalidated for the next measure pass. Detached nodes are
removed from dispatcher capture, hover, touch-scroll and focus-history state.

## Runtime orchestration

```python
from novaui.native import NativeRuntime, SkiaRenderer, RenderSize
from novaui.native.layout import LayoutNode
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
app.stop()
```

`NativeRuntime` coordinates build, layout, paint, overlays, animation time and
input dispatch. Its rendering, input, resize, lifecycle and scheduler flush
operations are restricted to the owner thread after start. Runtime start/stop
can be repeated on the same owner thread. Background state updates are applied
with `process_pending()`.

For an SDL3-managed application loop, use `SDL3Window.run_runtime()`; see
[`native-runtime-stabilization.md`](native-runtime-stabilization.md).

## Current boundaries

- The scheduler marshals state invalidations; it is not a general async task
  executor and does not provide an OS wake event. Custom hosts must call
  `process_pending()` during their event loop.
- Reconciliation updates `LayoutNode` trees; it is not a general virtual-DOM
  reconciler with arbitrary per-widget component-local state or effects.
- Runtime tests use injected renderers and platform doubles. Real SDL3/Skia
  lifecycle and platform-specific behavior still require desktop smoke tests.
