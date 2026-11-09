# Yuktara UI

**Yuktara UI** is a Python-first native UI framework from **Yuktara Technologies**. It targets desktop applications using SDL3 for window and input hosting and Skia for 2D rendering.

> Development status: early native framework development. Python subsystems have unit coverage, but real SDL3/Skia runtime integration and platform-specific behavior still need validation on target systems.

## Architecture

- Python layout, retained UI tree, widgets and reactive state.
- SDL3 desktop window and normalized input event layer.
- Skia rendering bridge and CPU raster presentation path.
- Native text measurement, editing, selection and undo/redo primitives.
- Automatic dependency setup through `python -m novaui setup`.
- Accessibility semantics, navigation stack, menus and popovers.
- No HTML, CSS, JavaScript, DOM or WebView renderer.

## Quick start

The repository currently contains project identity and contributor documentation. The native framework source snapshot is maintained separately; see [IMPORT_NATIVE_SOURCE.md](IMPORT_NATIVE_SOURCE.md) for the exact import procedure.

```bash
python -m pip install -e .
python -m novaui setup
python examples/native/hello_window.py
```

## Development checks

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/native
python -m compileall -q novaui
```

## Platform caveats

Tests using fake/injected backends do not certify actual SDL3/Skia operation, high-DPI behavior, native IME/clipboard, OS screen-reader providers, or multi-window behavior on Windows, Linux and macOS. Linux and macOS dependency setup may use system package managers and libraries.

## Project identity

The public framework name is **Yuktara UI**. The Python import package remains `novaui` temporarily for source/API continuity; a dedicated compatibility migration will rename it in a future release. The Yuktara Technologies word processor product built with this framework is **Dastavej**.

## License

No open-source license has been selected. All rights are reserved pending an explicit license decision.
