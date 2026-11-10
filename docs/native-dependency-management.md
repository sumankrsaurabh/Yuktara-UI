# Native dependency management

Yuktara UI provisions native dependencies on demand so an application developer
does not need to locate SDL3 DLLs or install Skia by hand.

## Verified dependency baselines (2026-11-10)

| Dependency | Version | Source |
|---|---:|---|
| SDL3 | 3.4.20 | Official SDL release |
| skia-python | 144.1 | PyPI |
| pytest (dev) | 9.2.0 | PyPI |

NumPy is intentionally omitted: no runtime module in this source tree imports it.

## Lifecycle

- `SkiaRenderer` calls `ensure_skia_python()` at first render. The manager checks
  the installed distribution metadata and installs the exact tested version
  using `sys.executable -m pip` when needed.
- `SDL3Window` validates the loaded shared library with `SDL_GetVersion()`. A
  system library older than 3.4.20 is not accepted as the managed runtime.
- Windows and macOS use the official SDL3 3.4.20 redistributable assets. The
  downloaded archive/disk image is checked against the SHA-256 published with
  the official release before any library is copied into the cache.
- Linux has no official prebuilt runtime asset in the SDL 3.4.20 release. The
  manager verifies the official source tarball, then builds a shared SDL3
  library into the user's cache with CMake. It checks for a working compiler
  and X11/Wayland development backend; if either is missing, it attempts to
  install the compiler and common SDL video/audio development packages through
  apt, dnf, pacman, zypper or apk. Administrator authorization is requested
  only when setup is run from an interactive terminal. A GUI-launched process
  without a terminal fails quickly with instructions rather than hiding a
  password prompt.
- All managed files are stored below `cache_root()`. No writes are made into
  the Python package directory.

## Explicit setup

```bash
python -m novaui setup
```

Add `--include-dev` to also provision the pinned pytest development dependency.

## Environment controls

- `YUKTARA_UI_NO_AUTO_INSTALL=1` disables automatic package installation and
  native downloads/builds.
- `YUKTARA_UI_CACHE_DIR=/path/to/cache` changes the per-user cache location.
- `YUKTARA_UI_SDL3_LIBRARY=/path/to/SDL3` selects an explicit SDL3 library path.
  The explicit library must report SDL3 3.4.20 or newer via `SDL_GetVersion()`.

## Failure model

Network errors, SHA-256 mismatches, unavailable wheels, unsupported CPU
architectures and build failures raise `DependencyError` or `SDL3Error` with a
specific setup message. Automatic setup is not silent: the first launch may
require network access and may invoke the OS package manager on Linux. The
framework never elevates privileges with an interactive password prompt.
