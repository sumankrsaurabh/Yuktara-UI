# Yuktara UI Native 2.3.0.dev0

Yuktara UI 2.3 extends the native SDL3 + Skia Python framework with a reusable
input and navigation component set.

## Added controls

- `TextField` — single-line committed text input, cursor editing, Ctrl+A,
  Shift+Arrow selection replacement, max length, read-only and submit callback.
- `TextArea` — multiline input, wrapping, newline insertion and basic vertical
  cursor navigation.
- `Dropdown` — option selection, expanded state, keyboard open/navigation/
  select/close behavior.
- `Slider` — stepped value range, pointer drag capture, arrow keys, Home/End.
- `Tabs` / `TabItem` — tab selection, optional widget or layout content,
  Left/Right navigation and disabled tabs.
- `SegmentedControl` — mutually-exclusive native segmented selection.

## Input system

- Focus tracking with focus/blur callbacks and accessibility focused state.
- Tab / Shift+Tab traversal through focusable controls.
- Keyboard event and committed text routing.
- Enter/Space activation for focused clickable controls.
- Pointer capture across drag motion.
- Repaint after keyboard, text and captured pointer events.

## Example

```bash
python examples/native/input_gallery.py
```

## Test

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```

All tests run against the backend-neutral model and recording renderers.
Real SDL3 and Skia window behavior, OS clipboard, IME pre-edit composition,
visual selection decoration and glyph-precise cursor hit testing still require
additional platform-specific work.
