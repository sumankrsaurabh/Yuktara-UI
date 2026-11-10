# Yuktara UI

**Yuktara UI** is a Python-first native UI framework by **Yuktara Technologies**.
It uses SDL3 for the desktop window/input layer and Skia for CPU raster rendering.
The historical Python import namespace is currently `novaui` and will be migrated
only through a planned compatibility release.

> **Status:** experimental native framework foundation. Unit tests use injected
> backends; real SDL3/Skia integration still needs validation on each target OS.

## Native stack

- **SDL3 3.4.20** — native desktop window and event host.
- **Skia Python 144.1** — CPU raster rendering and text metrics.
- **Python** — layout, retained tree, reactivity, normalized input and runtime.
- **Inter-first font resolution** — uses installed Inter when available, then
  configured system fallbacks.
- **Native component library** — labels, buttons, cards, badges, dividers,
  progress bars, checkboxes, switches and radio groups with light/dark themes.
- **Automatic dependency manager** — provisions Python and native dependencies
  on first use and supports an explicit preflight setup command.

The repository contains no HTML/CSS/JavaScript renderer, browser runtime,
WebView or pywebview implementation.

## Quick start

Create a virtual environment and install the project:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
```

Run automatic dependency preflight (optional; the window/render paths also
bootstrap the dependencies when first needed):

```bash
python -m novaui setup
```

Run the SDL3 + Skia example:

```bash
python examples/native/sdl3_skia_window.py
```

Run the native component gallery:

```bash
python examples/native/component_gallery.py
```

## Automatic dependency behavior

- Skia Python **144.1** is installed from PyPI with the active Python interpreter.
- SDL3 **3.4.20** is downloaded from the official SDL release and checked against
  its published SHA-256 for Windows and macOS.
- On Linux, the official SDL3 3.4.20 source archive is SHA-256 verified and built
  into the per-user cache. If the compiler or X11/Wayland development headers
  are missing, setup attempts to install common build/video/audio packages
  through apt, dnf, pacman, zypper or apk. This can request administrator
  authorization once from an interactive terminal.
- Native libraries are stored in a per-user writable cache, not in site-packages
  or the project directory.
- NumPy is not installed because this source does not use it.

The first setup needs an internet connection. Python must already be installed.
For a preflight check, run `python -m novaui setup` before launching the app.

### Environment controls

| Variable | Purpose |
|---|---|
| `YUKTARA_UI_NO_AUTO_INSTALL=1` | Disable all automatic installation and downloading. |
| `YUKTARA_UI_CACHE_DIR` | Override the user cache location. |
| `YUKTARA_UI_SDL3_LIBRARY` | Supply an explicit SDL3 library path; the library must be SDL3 3.4.20 or newer. |

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q tests/native
python -m compileall -q novaui
```

## Repository layout

```text
novaui/
  native/
    dependencies/  # first-run Python and SDL3 provisioning
    layout/        # geometry, nodes, measurement, arrangement, hit testing
    platform/      # SDL3 host, event decoding and dispatch
    reactivity/    # state, scheduler, components and keyed reconciliation
    rendering/    # retained layout-tree painter and clipping
    text/          # Skia-backed text measurement and wrapping
    widgets/       # Native built-in component library
    renderer.py    # Skia CPU raster renderer
    runtime.py     # build -> layout -> paint -> input lifecycle
    theme.py       # native theme tokens
    typography.py  # Inter-first font configuration and resolver

tests/native/     # backend-injected unit tests
examples/native/  # SDL3/Skia example

docs/             # architecture, component library and subsystem documentation
```

## Platform validation and limitations

Tests can validate dependency-manager decisions and Python-side behavior, but
they do not certify a real desktop window on every operating system. Validate
SDL3 window creation, display scaling, GPU/driver behavior, audio/video backend
availability, IME/clipboard integration and font fallback on each supported OS.
The current Skia renderer uses CPU raster surfaces; direct GPU surface integration
is future work. Mobile backends are not included.

## License

No open-source license has been selected. The source distribution remains
proprietary until Yuktara Technologies adds an explicit license.
