# Yuktara UI 3.2.0.dev0 — runtime and retained-tree stabilization

Yuktara UI 3.2 hardens the native application lifecycle, state scheduling,
retained-tree reconciliation and logical/backing-pixel coordinate handling.
No component-construction API changes are required.

## Main changes

- Declarative retained-node properties are copied from `LayoutNode` metadata,
  while derived geometry and live focus/scroll state are handled separately.
- Reused nodes refresh callbacks, visual properties, accessibility metadata,
  paint hooks and grid settings; stale text layout is invalidated.
- Dispatcher references to removed nodes are pruned from capture, hover,
  touch-scroll and focus-history state.
- `NativeRuntime.start()` binds the scheduler to the UI owner thread.
  Worker-thread state changes and binding callbacks are delivered by
  `runtime.process_pending()` on that thread.
- Runtime and SDL window operations enforce thread ownership. Runtime restart
  on the same thread resets quit/focus state and reconnects manager callbacks.
- Logical window dimensions are separated from backing-pixel dimensions;
  independent X/Y scale factors feed the Skia raster surface.
- Touch positions and deltas are converted from SDL normalized fractions into
  logical window coordinates before dispatch.
- `SDL3Window.run_runtime()` integrates open, size negotiation, mount, decoded
  event dispatch, queued state flushing, animation/toast clock progression,
  frame presentation and teardown.
- A failing scheduled callback no longer drops later callbacks from the same
  drained batch.

## Integrated runtime example

```bash
python -m pip install -e .
python -m novaui setup
python examples/native/runtime_window.py
```

Applications with a custom event loop should call `runtime.process_pending()`
and `runtime.advance_time(delta_ms)` on the UI thread, then present the current
renderer frame.

## Verification

The current development test suite contains backend-injected tests for
reconciliation, runtime lifecycle, thread-affine scheduling, event decoding,
logical/pixel resizing, touch coordinate conversion and SDL host teardown.
Run it with:

```bash
python -m pytest -q tests/native
```

These tests do not certify real window creation or high-DPI behavior across
Windows, Linux and macOS. Native SDL3/Skia integration, screen-reader bridges,
GPU surfaces, full IME composition and Android/iOS backends remain future work.
