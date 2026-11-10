"""Typography configuration for the native renderer."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_FONT_FAMILY = "Inter"
FALLBACK_FONT_FAMILIES = ("Arial", "Noto Sans", "DejaVu Sans", "sans-serif")


@dataclass(frozen=True, slots=True)
class FontConfig:
    """Font configuration shared by native text components."""

    family: str = DEFAULT_FONT_FAMILY
    fallback_families: tuple[str, ...] = FALLBACK_FONT_FAMILIES
    size: float = 14.0
    weight: str = "normal"
    italic: bool = False

    def __post_init__(self) -> None:
        if not self.family or not isinstance(self.family, str):
            raise TypeError("Font family must be a non-empty string.")
        if self.size <= 0:
            raise ValueError("Font size must be greater than zero.")
        if self.weight not in {"normal", "medium", "semibold", "bold"}:
            raise ValueError("Unsupported font weight.")


class FontResolver:
    """Resolve font families through Skia's system typeface provider.

    Inter is the framework default. If Inter is not installed or bundled by
    the application, the resolver tries the configured fallback families.
    """

    def __init__(self, skia_module=None) -> None:
        self._skia = skia_module

    def _module(self):
        if self._skia is None:
            try:
                from .dependencies import ensure_skia_python
                ensure_skia_python()
                import skia
            except Exception as exc:
                raise RuntimeError(
                    "Yuktara UI could not prepare Skia Python (skia-python 144.1). "
                    "Check the network connection or disable automatic setup with "
                    "YUKTARA_UI_NO_AUTO_INSTALL=1."
                ) from exc
            self._skia = skia
        return self._skia

    def resolve(self, config: FontConfig):
        skia = self._module()
        weights = {
            "normal": skia.FontStyle.kNormal_Weight,
            "medium": skia.FontStyle.kMedium_Weight,
            "semibold": skia.FontStyle.kSemiBold_Weight,
            "bold": skia.FontStyle.kBold_Weight,
        }
        style = skia.FontStyle(
            weights[config.weight],
            skia.FontStyle.kNormal_Width,
            skia.FontStyle.kItalic_Slant if config.italic else skia.FontStyle.kUpright_Slant,
        )
        for family in (config.family, *config.fallback_families):
            typeface = skia.Typeface.MakeFromName(family, style)
            if typeface is not None:
                return typeface
        return skia.Typeface.MakeDefault()
