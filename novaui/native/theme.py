"""Yuktara UI design tokens for native components."""
from __future__ import annotations

from dataclasses import dataclass
from .typography import FontConfig


@dataclass(frozen=True, slots=True)
class NativeTheme:
    """Immutable semantic palette and geometry tokens.

    Colors are ARGB integers so the theme can be consumed directly by the
    Skia renderer without a per-frame CSS/color-string parsing layer.
    """
    name: str = "yuktara-light"
    background: int = 0xFFF6F7F9
    surface: int = 0xFFFFFFFF
    surface_variant: int = 0xFFF0F2F5
    foreground: int = 0xFF202735
    muted: int = 0xFF667085
    border: int = 0xFFE2E6EC
    primary: int = 0xFF315FEA
    primary_soft: int = 0xFFEAF0FF
    on_primary: int = 0xFFFFFFFF
    success: int = 0xFF16834A
    success_soft: int = 0xFFE7F6ED
    on_success: int = 0xFFFFFFFF
    warning: int = 0xFFB86B08
    warning_text: int = 0xFF8B4F05
    warning_soft: int = 0xFFFFF3D8
    danger: int = 0xFFC43D4B
    danger_soft: int = 0xFFFFE9EC
    on_danger: int = 0xFFFFFFFF
    info: int = 0xFF1769AA
    info_soft: int = 0xFFE7F3FF
    disabled_surface: int = 0xFFE9ECF1
    disabled_text: int = 0xFF98A1AF
    focus: int = 0xFF7C9BFF
    radius_small: float = 6.0
    radius_medium: float = 10.0
    radius_large: float = 16.0
    radius_pill: float = 999.0
    font: FontConfig = FontConfig()

    @classmethod
    def dark(cls) -> "NativeTheme":
        return cls(
            name="yuktara-dark",
            background=0xFF151922,
            surface=0xFF202735,
            surface_variant=0xFF2A3444,
            foreground=0xFFF4F6FA,
            muted=0xFFAFB9C8,
            border=0xFF364253,
            primary=0xFF8AA7FF,
            primary_soft=0xFF27365D,
            on_primary=0xFF111A2E,
            success=0xFF57C889,
            success_soft=0xFF1F3E30,
            on_success=0xFF10271A,
            warning=0xFFF2B84B,
            warning_text=0xFFFFD37C,
            warning_soft=0xFF49391D,
            danger=0xFFFF7D89,
            danger_soft=0xFF4A252D,
            on_danger=0xFF351218,
            info=0xFF7EC4FF,
            info_soft=0xFF1E3548,
            disabled_surface=0xFF303947,
            disabled_text=0xFF7C8797,
            focus=0xFF9CB4FF,
        )
