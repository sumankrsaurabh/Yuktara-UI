"""Experimental OpenGL-backed Skia renderer.

The host application must create and make an OpenGL context current before
constructing this renderer. Skia owns its GPU resources; the host owns the
window, GL context and swap/presentation lifecycle.
"""
from __future__ import annotations

from typing import Any

from .renderer import RenderSize, SkiaRenderer


class SkiaGpuRenderer(SkiaRenderer):
    """Render the same Yuktara drawing API into a Skia OpenGL surface.

    This is an off-screen GPU surface. A host can composite its snapshot into
    its own OpenGL framebuffer. The renderer deliberately does not create a
    window or steal ownership of the host's GL context.

    All calls must be made on the thread where the OpenGL context is current.
    The existing :class:`SkiaRenderer` remains the portable CPU fallback.
    """

    def __init__(self, size: RenderSize, *, skia_module: Any = None) -> None:
        self._gpu_context = None
        super().__init__(size, skia_module=skia_module)

    def _create_surface(self) -> None:
        skia = self._module()
        contexts = getattr(skia, "GrDirectContexts", None)
        make_gl = getattr(contexts, "MakeGL", None)
        if not callable(make_gl):
            raise RuntimeError(
                "This skia-python build does not expose the OpenGL GPU backend. "
                "Install the supported native extra and use a compatible build."
            )
        if self._gpu_context is None:
            try:
                self._gpu_context = make_gl()
            except Exception as exc:
                raise RuntimeError(
                    "Could not attach Skia to the current OpenGL context. "
                    "Create and make a compatible OpenGL context current before "
                    "constructing SkiaGpuRenderer."
                ) from exc
        if self._gpu_context is None:
            raise RuntimeError(
                "Skia could not create a GPU context. Check OpenGL driver support "
                "and ensure an OpenGL context is current on this thread."
            )

        image_info = skia.ImageInfo.MakeN32Premul(
            self.size.pixel_width, self.size.pixel_height
        )
        surface_factory = getattr(skia, "Surfaces", None)
        make_target = getattr(surface_factory, "MakeRenderTarget", None)
        if not callable(make_target):
            raise RuntimeError(
                "This skia-python build does not expose GPU render-target creation."
            )
        try:
            surface = make_target(
                self._gpu_context,
                skia.Budgeted.kNo,
                image_info,
                0,
                skia.GrSurfaceOrigin.kTopLeft_GrSurfaceOrigin,
            )
        except Exception as exc:
            raise RuntimeError("Skia failed to allocate an OpenGL render target.") from exc
        if surface is None:
            raise RuntimeError(
                "Skia returned no GPU surface. The active driver may not support "
                "the requested render-target format or dimensions."
            )
        self._surface = surface
        self._canvas = surface.getCanvas()
        self._canvas.scale(self.size.scale, self.size.scale_y or self.size.scale)

    @property
    def backend(self) -> str:
        return "opengl"

    def flush(self) -> None:
        """Submit queued Skia drawing commands to the active OpenGL context."""
        if self._surface is None:
            raise RuntimeError("GPU renderer is closed.")
        flush_submit = getattr(self._surface, "flushAndSubmit", None)
        if callable(flush_submit):
            flush_submit()
        else:
            self._gpu_context.flush()
            self._gpu_context.submit()

    def snapshot(self):
        """Return a GPU-backed immutable image after submitting pending draws."""
        self.flush()
        return self._surface.makeImageSnapshot()

    def close(self) -> None:
        """Release Skia surfaces; the host remains responsible for its GL context."""
        self._surface = None
        self._canvas = None
        self._image_cache.clear()
        self._gpu_context = None

    def resize(self, size: RenderSize) -> None:
        if self._gpu_context is None:
            raise RuntimeError("GPU renderer is closed.")
        self.size = size
        self._create_surface()


__all__ = ["SkiaGpuRenderer"]
