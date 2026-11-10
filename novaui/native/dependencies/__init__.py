"""Automatic native dependency setup for Yuktara UI."""
from .manager import (
    DependencyError,
    PYTEST_VERSION,
    SDL3_VERSION,
    SKIA_PYTHON_VERSION,
    cache_root,
    ensure_sdl3_runtime,
    ensure_skia_python,
    setup_all,
)

__all__ = [
    "DependencyError", "PYTEST_VERSION", "SDL3_VERSION", "SKIA_PYTHON_VERSION",
    "cache_root", "ensure_sdl3_runtime", "ensure_skia_python", "setup_all",
]
