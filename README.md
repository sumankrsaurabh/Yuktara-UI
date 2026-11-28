# Yuktara UI

Yuktara UI is a Python-first native desktop UI framework by Yuktara Technologies.
Applications are composed from Python components and retained layout nodes. The
framework measures and arranges the interface, Skia paints CPU-raster frames,
and SDL3 provides the desktop window and input/event host.

> **Development status:** experimental native desktop framework, version
> `3.3.0.dev0`. The historical Python import namespace remains `novaui`
> for compatibility.

## Architecture

The runtime pipeline is:

1. Build a retained `LayoutNode` tree from application components.
2. Measure and arrange nodes with the backend-neutral layout engine.
3. Paint the retained tree with the Skia CPU raster renderer.
4. Present rendered frames through the SDL3 window host.
5. Normalize SDL3 input events and dispatch them to the active UI tree.

Layout, state, reconciliation and input dispatch remain backend-neutral. SDL3
and Skia-specific operations are isolated in their respective adapters. This
repository does not contain an HTML/CSS/JavaScript renderer, browser runtime,
WebView or pywebview implementation.

## Quick start

Create a virtual environment and install the development package:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Provision native dependencies:

```bash
python -m novaui setup
```

Launch the integrated desktop runtime:

```bash
python examples/native/runtime_window.py
```

Run the component gallery:

```bash
python examples/native/component_gallery.py
```

## Development checks

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
python -m build --wheel
```

The CI workflow runs the native test suite and package build across its
configured operating-system and Python-version matrix. The separate native
integration workflow provisions SDL3 and Skia, captures a gallery screenshot,
and opens a real SDL3 window under a virtual X11 display.

## Documentation

- [Architecture](ARCHITECTURE.md) — runtime pipeline and backend boundaries.
- [Development log](DEVELOPMENT_LOG.md) — cumulative implementation inventory
  and known limitations.
- [Native changelog](CHANGELOG-NATIVE.md) — version-by-version change history.
- [Component library](docs/native-component-library.md) — built-in components.
- [Responsive layout](docs/native-responsive-layout.md) — adaptive sizing and
  resize behavior.
- [Advanced layout](docs/native-advanced-layout.md) — constraints, wrapping,
  positioning and grid placement.
- [Typography and text shaping](docs/native-text-shaping.md) — font and shaping
  behavior.
- [Accessibility](docs/native-accessibility.md) — semantic metadata and current
  platform limitations.
- [Platform parity roadmap](docs/native-platform-parity-roadmap.md) — remaining
  cross-platform validation and capability gaps.
- [Version notes](README-NATIVE-2.3.md) · [2.4](README-NATIVE-2.4.md) ·
  [2.5](README-NATIVE-2.5.md) · [2.6](README-NATIVE-2.6.md) ·
  [2.7](README-NATIVE-2.7.md) · [2.8](README-NATIVE-2.8.md) ·
  [2.9](README-NATIVE-2.9.md) · [3.0](README-NATIVE-3.0.md) ·
  [3.1](README-NATIVE-3.1.md) · [3.2](README-NATIVE-3.2.md) ·
  [3.3](README-NATIVE-3.3.md).

## Runtime dependencies and limitations

- SDL3 3.4.20 provides the desktop window and event host.
- Skia Python 144.1 provides CPU raster rendering and text metrics.
- HarfBuzz shaping is optional and requires the `shaping` extra plus explicit
  font-file configuration.
- Native dependencies are provisioned into a per-user cache; the first setup
  requires an internet connection.
- Set `YUKTARA_UI_NO_AUTO_INSTALL=1` to disable automatic dependency
  installation and downloads.
- Set `YUKTARA_UI_CACHE_DIR` to override the native dependency cache.
- Set `YUKTARA_UI_SDL3_LIBRARY` to use an explicit SDL3 library path.

The current renderer uses CPU raster surfaces; direct GPU-surface integration
is future work. Automated unit tests do not certify physical-device behavior,
mixed-DPI multi-monitor handling, IME, clipboard or accessibility integration
on every supported operating system. Validate those capabilities on each
target platform before release. Mobile backends are not included.

## License

No open-source license has been selected. The source distribution remains
proprietary until Yuktara Technologies adds an explicit license.
