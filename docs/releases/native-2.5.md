# Yuktara UI Native 2.5.0.dev0

Yuktara UI 2.5 extends the SDL3 + Skia runtime with deterministic animation,
reduced-motion support, focus feedback and keyboard/accessibility refinements.

## Animation system

- `AnimationManager` and `AnimationHandle` provide explicit host-clock-driven
  numeric property animation.
- Easing curves: `linear`, `ease_in`, `ease_out`, `ease_in_out` and
  `ease_out_cubic`.
- `NativeRuntime.animate(...)` animates retained object properties and repaints
  when timeline values change.
- `LayoutNode.opacity` supports group compositing in Skia through save layers.
- Reduced-motion mode immediately finishes active animations and skips future
  interpolation.
- No timers, workers or hidden event loops are created.

## Accessibility and keyboard refinements

- Keyboard-focused controls receive a visible native focus ring.
- Context menus focus their first enabled item and support Up/Down navigation
  and Enter/Space activation.
- Focus returns to the previously active control after dismissing a context
  menu or modal dialog where that control remains available.
- Modal accessibility scopes omit obscured background controls while a modal
  dialog is active.
- Existing semantic roles, labels, values, disabled, checked, selected,
  expanded and focused states remain available to platform adapters.

## Usage

```python
runtime.animate(panel_node, "opacity", 0.0, duration_ms=240,
                easing="ease_out_cubic")
runtime.advance_time(frame_delta_ms)  # call from the host frame loop
runtime.set_reduced_motion(True)      # follow OS/user preference
```

See [docs/native-animation-accessibility.md](docs/native-animation-accessibility.md)
for the complete API and platform limitations.

Run the animation gallery:

```bash
python examples/native/animation_gallery.py
```

Run verification:

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```

Tests use injected renderers and event models. Real desktop SDL3 + Skia behavior,
OS accessibility providers, IME composition, clipboard support and assistive-
technology compatibility still require validation on each target OS.
