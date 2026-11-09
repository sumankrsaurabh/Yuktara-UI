# Yuktara UI

**Yuktara UI** is a Python-first, native-rendered UI framework developed by Yuktara Technologies. It targets desktop applications using SDL3 for window and input hosting and Skia for 2D rendering.

> Development status: early native framework development. SDL3/Skia runtime behavior and platform-specific integrations require validation on target OSes.

## Native architecture
- Python layout, retained UI tree, widgets and reactive state.
- SDL3 desktop window and normalized input event layer.
- Skia renderer bridge with CPU raster presentation path.
- Native text measurement and editing primitives.
- Automatic dependency setup through `python -m novaui setup`.
- Accessibility semantic tree, navigation, inline menus and popovers.
- Legacy/web renderer is not included in this repository.

## Quick start

```bash
python -m pip install -e .
python -m novaui setup
python examples/native/hello_window.py
```

## Development

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/native
python -m compileall -q novaui
```

## Repository layout
- `novaui/native/` — runtime, widgets, layout, rendering and SDL3 host.
- `novaui/native/dependencies/` — dependency detection and setup.
- `examples/native/` — native examples.
- `tests/native/` — backend-injected unit tests.
- `docs/` — architecture and subsystem documentation.

## Platform validation
Unit tests use injected/fake backends where needed. They do not certify real SDL3/Skia integration, platform IME/clipboard, OS screen-reader bridges, or multi-window behavior on Windows, Linux and macOS.

## License
No license has been selected. All rights reserved until maintainers add an explicit license.
