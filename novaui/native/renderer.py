"""Small, deterministic Skia raster renderer used by Yuktara UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .typography import FontConfig, FontResolver


@dataclass(frozen=True, slots=True)
class RenderSize:
    width: int
    height: int
    scale: float = 1.0
    scale_y: float | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Render dimensions must be positive.")
        if self.scale <= 0 or (self.scale_y is not None and self.scale_y <= 0):
            raise ValueError("Render scales must be positive.")

    @property
    def pixel_width(self) -> int:
        return round(self.width * self.scale)

    @property
    def pixel_height(self) -> int:
        return round(self.height * (self.scale_y or self.scale))


class SkiaRenderer:
    """Owns a Skia raster surface and exposes safe high-level draw methods.

    The first implementation deliberately uses a CPU raster surface. A
    hardware-accelerated surface can be added behind this interface later,
    without changing component or layout APIs.
    """

    def __init__(self, size: RenderSize, *, skia_module: Any = None) -> None:
        self.size = size
        self._skia = skia_module
        self._surface = None
        self._canvas = None
        self._fonts = FontResolver(skia_module)
        self._image_cache = {}
        self._create_surface()

    def _module(self):
        if self._skia is None:
            # Skia is provisioned lazily on first native render. The installer
            # uses this process's Python interpreter and a pinned tested wheel.
            from .dependencies import ensure_skia_python

            try:
                ensure_skia_python()
                import skia
            except Exception as exc:
                raise RuntimeError(
                    "Yuktara UI could not prepare Skia Python "
                    "(skia-python 144.1). Check the network connection or "
                    f"set YUKTARA_UI_NO_AUTO_INSTALL=1 to disable bootstrapping. Details: {exc}"
                ) from exc
            self._skia = skia
            self._fonts = FontResolver(skia)
        return self._skia

    def _create_surface(self) -> None:
        skia = self._module()
        self._surface = skia.Surface.MakeRasterN32Premul(
            self.size.pixel_width, self.size.pixel_height
        )
        if self._surface is None:
            raise RuntimeError("Skia could not allocate the raster surface.")
        self._canvas = self._surface.getCanvas()
        self._canvas.scale(self.size.scale, self.size.scale_y or self.size.scale)

    @property
    def canvas(self):
        return self._canvas

    def clear(self, color: int = 0xFFFFFFFF) -> None:
        self._canvas.clear(color)

    def draw_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: int,
        *,
        radius: float = 0.0,
    ) -> None:
        if width < 0 or height < 0 or radius < 0:
            raise ValueError("Rectangle dimensions and radius cannot be negative.")
        skia = self._module()
        paint = skia.Paint(AntiAlias=True, Color=color)
        rect = skia.Rect.MakeXYWH(x, y, width, height)
        if radius:
            self._canvas.drawRoundRect(rect, radius, radius, paint)
        else:
            self._canvas.drawRect(rect, paint)

    def draw_stroke_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: int,
        *,
        stroke_width: float = 1.0,
        radius: float = 0.0,
    ) -> None:
        """Draw an outlined rectangle without affecting the filled-rect API."""
        if width < 0 or height < 0 or radius < 0 or stroke_width <= 0:
            raise ValueError("Rectangle dimensions and stroke width are invalid.")
        skia = self._module()
        paint = skia.Paint(AntiAlias=True, Color=color)
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(stroke_width)
        rect = skia.Rect.MakeXYWH(x, y, width, height)
        if radius:
            self._canvas.drawRoundRect(rect, radius, radius, paint)
        else:
            self._canvas.drawRect(rect, paint)

    def draw_text(
        self,
        text: str,
        x: float,
        baseline_y: float,
        *,
        color: int = 0xFF202735,
        font: FontConfig | None = None,
    ) -> None:
        if not isinstance(text, str):
            raise TypeError("Text content must be a string.")
        skia = self._module()
        config = font or FontConfig()
        paint = skia.Paint(AntiAlias=True, Color=color)
        cursor_x = x
        for run in self._fonts.resolve_runs(config, text):
            skia_font = skia.Font(run.typeface, config.size)
            self._canvas.drawString(run.text, cursor_x, baseline_y, skia_font, paint)
            cursor_x += float(skia_font.measureText(run.text))

    def _load_image(self, source):
        """Decode a path/encoded buffer or accept an already decoded Skia image."""
        if callable(getattr(source, "width", None)) and callable(getattr(source, "height", None)):
            return source
        if isinstance(source, memoryview):
            source = source.tobytes()
        if isinstance(source, bytearray):
            source = bytes(source)
        if isinstance(source, bytes):
            cache_key = ("bytes", hash(source), len(source))
            encoded = source
        elif isinstance(source, (str, bytes)) or hasattr(source, "__fspath__"):
            from pathlib import Path
            path = Path(source).expanduser()
            stat = path.stat()
            cache_key = ("path", str(path.resolve()), stat.st_mtime_ns, stat.st_size)
            encoded = path.read_bytes()
        else:
            raise TypeError("Image source must be a path, encoded bytes or Skia image")
        cached = self._image_cache.get(cache_key)
        if cached is not None:
            return cached
        skia = self._module()
        image = skia.Image.MakeFromEncoded(encoded)
        if image is None:
            raise ValueError("Skia could not decode the supplied image data")
        self._image_cache[cache_key] = image
        return image

    def draw_image(self, source, x: float, y: float, width: float, height: float, *,
                   fit: str = "contain", radius: float = 0.0, opacity: float = 1.0) -> None:
        """Draw an image into a native rectangle with contain/cover/fill fitting."""
        if width < 0 or height < 0 or radius < 0 or not 0 <= opacity <= 1:
            raise ValueError("Image bounds, radius or opacity are invalid")
        if fit not in {"contain", "cover", "fill", "none"}:
            raise ValueError("fit must be contain, cover, fill or none")
        if width == 0 or height == 0 or opacity == 0:
            return
        skia = self._module()
        image = self._load_image(source)
        image_width = float(image.width())
        image_height = float(image.height())
        if image_width <= 0 or image_height <= 0:
            return
        src = skia.Rect.MakeXYWH(0, 0, image_width, image_height)
        dst_x, dst_y, dst_width, dst_height = x, y, width, height
        if fit == "contain":
            scale = min(width / image_width, height / image_height)
            dst_width = image_width * scale
            dst_height = image_height * scale
            dst_x += (width - dst_width) / 2
            dst_y += (height - dst_height) / 2
        elif fit == "none":
            # Preserve the source's native pixel dimensions. The viewport clip
            # below crops oversized images and centers undersized images.
            dst_width = image_width
            dst_height = image_height
            dst_x += (width - dst_width) / 2
            dst_y += (height - dst_height) / 2
        elif fit == "cover":
            scale = max(width / image_width, height / image_height)
            crop_width = width / scale
            crop_height = height / scale
            src_x = (image_width - crop_width) / 2
            src_y = (image_height - crop_height) / 2
            src = skia.Rect.MakeXYWH(src_x, src_y, crop_width, crop_height)
        dst = skia.Rect.MakeXYWH(dst_x, dst_y, dst_width, dst_height)
        paint = skia.Paint(AntiAlias=True)
        if opacity < 1:
            paint.setAlphaf(float(opacity))
        self._canvas.save()
        try:
            if radius > 0 and callable(getattr(self._canvas, "clipRRect", None)):
                clip_rect = skia.Rect.MakeXYWH(x, y, width, height)
                clip_rrect = skia.RRect.MakeRectXY(clip_rect, radius, radius)
                self._canvas.clipRRect(clip_rrect, True)
            else:
                self._canvas.clipRect(skia.Rect.MakeXYWH(x, y, width, height))
            self._canvas.drawImageRect(image, src, dst, skia.SamplingOptions(), paint)
        finally:
            self._canvas.restore()

    def draw_glyph_run(self, glyph_ids, positions, x: float, baseline_y: float, *,
                       color: int = 0xFF202735, typeface=None, size: float = 14.0) -> None:
        """Draw pre-shaped HarfBuzz glyph IDs at measured local positions.

        Glyph IDs are valid only for the exact typeface supplied by the shaping
        backend.  This method intentionally does not attempt font fallback.
        """
        if not glyph_ids:
            return
        if typeface is None:
            raise ValueError("A typeface is required to draw pre-shaped glyph IDs.")
        if len(glyph_ids) != len(positions):
            raise ValueError("glyph_ids and positions must have equal lengths.")
        skia = self._module()
        builder_type = getattr(skia, "TextBlobBuilder", None)
        if builder_type is None or not callable(getattr(self._canvas, "drawTextBlob", None)):
            raise RuntimeError(
                "This Skia Python build does not expose TextBlobBuilder.allocRunPos "
                "and Canvas.drawTextBlob; pre-shaped text cannot be rendered."
            )
        paint = skia.Paint(AntiAlias=True, Color=color)
        font = skia.Font(typeface, float(size))
        points = [skia.Point(float(px), float(py)) for px, py in positions]
        builder = builder_type()
        builder.allocRunPos(font, list(map(int, glyph_ids)), points)
        blob = builder.make()
        if blob is None:
            return
        self._canvas.drawTextBlob(blob, float(x), float(baseline_y), paint)

    def save(self) -> int:
        return self._canvas.save()

    def save_layer(self, opacity: float = 1.0) -> int:
        """Save a compositing layer whose contents use the supplied opacity."""
        if not 0.0 <= opacity <= 1.0:
            raise ValueError("Layer opacity must be between 0 and 1.")
        skia = self._module()
        paint = skia.Paint()
        paint.setAlphaf(float(opacity))
        return self._canvas.saveLayer(None, paint)

    def clip_rect(self, x: float, y: float, width: float, height: float) -> None:
        skia = self._module()
        self._canvas.clipRect(skia.Rect.MakeXYWH(x, y, width, height))

    def restore(self) -> None:
        self._canvas.restore()

    def snapshot(self):
        """Return an immutable Skia image snapshot of the current frame."""
        return self._surface.makeImageSnapshot()

    def to_png_bytes(self) -> bytes:
        """Encode the current frame as PNG bytes."""
        skia = self._module()
        data = self.snapshot().encodeToData(skia.kPNG)
        if data is None:
            raise RuntimeError("Skia failed to encode the frame as PNG.")
        return bytes(data)

    def resize(self, size: RenderSize) -> None:
        self.size = size
        self._create_surface()
