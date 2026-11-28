# Yuktara UI Native 2.4.0.dev0

Yuktara UI 2.4 extends the native SDL3 + Skia runtime with a reusable overlay
layer for floating and modal UI surfaces.

## Added overlay widgets

- `Dialog` — centered modal surface with scrim, outside-click and Escape
  dismissal options.
- `Popover` — anchored floating content with top/bottom/left/right placement,
  collision flipping and viewport clamping.
- `Tooltip` — passive anchored hint that does not capture pointer input.
- `ContextMenu` / `MenuItem` — pointer-positioned menu, disabled entries and
  automatic close after an enabled item is selected.
- `Toast` — status notification with explicit or persistent lifetime.
- `OverlayManager` / `OverlayHandle` — show, dismiss, stack, position and
  advance floating surfaces.

## Runtime integration

- Overlays paint above the application tree using the existing Skia painter.
- Input hit testing checks the topmost interactive overlay before the app tree.
- Modal focus is trapped within the active dialog; Escape handling skips
  pointer-transparent notifications and tooltips.
- Timed notifications expire through `NativeRuntime.advance_time(delta_ms)`;
  no hidden timer or background task is started.
- Accessibility semantics can include active overlays with
  `build_accessibility_tree(root, overlays=runtime.overlays.roots)`.

## Example

```bash
python examples/native/overlay_gallery.py
```

## Test

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```

Tests use injected layout/rendering models and normalized events. Real SDL3 and
Skia desktop window behavior, OS accessibility adapters and assistive-technology
behavior remain platform validation tasks. The existing 2.3 `Dropdown` still
uses inline options rather than the overlay manager.
