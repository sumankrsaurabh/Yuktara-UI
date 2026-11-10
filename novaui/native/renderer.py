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

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Render dimensions must be positive.")
        if self.scale <= 0:
            raise ValueError("Render scale must be positive.")

    @property
    def pixel_width(self) -> int:
        return round(self.width * self.scale)

    @property
    def pixel_height(self) -> int:
        return round(self.height * self.scale)


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
        self._canvas.scale(self.size.scale, self.size.scale)

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
        typeface = self._fonts.resolve(config)
        paint = skia.Paint(AntiAlias=True, Color=color)
        skia_font = skia.Font(typeface, config.size)
        self._canvas.drawString(text, x, baseline_y, skia_font, paint)


    def save(self) -> int:
        return self._canvas.save()

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
