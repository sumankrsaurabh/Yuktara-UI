"""Pixel extraction bridge from Skia raster images to SDL RGBA textures."""

from __future__ import annotations

from .sdl3 import PixelFrame


def skia_image_to_rgba(image, *, skia_module, width: int, height: int) -> PixelFrame:
    """Read a Skia image into tightly packed, unpremultiplied RGBA8 bytes.

    The explicit color/alpha types avoid assuming the host's native N32 order.
    """
    info = skia_module.ImageInfo.Make(
        width,
        height,
        skia_module.ColorType.kRGBA_8888_ColorType,
        skia_module.AlphaType.kUnpremul_AlphaType,
    )
    pixels = bytearray(width * height * 4)
    ok = image.readPixels(info, pixels, width * 4, 0, 0)
    if not ok:
        raise RuntimeError("Skia could not convert the image to RGBA8888.")
    return PixelFrame(width, height, bytes(pixels), width * 4)


def renderer_frame(renderer, *, skia_module) -> PixelFrame:
    """Convenience adapter for Yuktara UI's SkiaRenderer."""
    size = renderer.size
    return skia_image_to_rgba(
        renderer.snapshot(),
        skia_module=skia_module,
        width=size.pixel_width,
        height=size.pixel_height,
    )
