"""Yuktara Clarity design tokens: an original, restrained native design language."""
from __future__ import annotations

from dataclasses import dataclass
from .typography import FontConfig


@dataclass(frozen=True, slots=True)
class NativeTheme:
    """Immutable semantic tokens shared by every native component.

    The visual direction favors quiet neutral surfaces, crisp hierarchy,
    restrained blue actions and generous geometry. Colors are ARGB integers.
    Inter remains the only implicit typeface; FontConfig controls explicit
    opt-in font customization.
    """
    name: str = "yuktara-clarity-light"

    # Semantic color roles — light appearance
    background: int = 0xFFF5F5F7
    surface: int = 0xFFFFFFFF
    surface_variant: int = 0xFFF2F2F4
    foreground: int = 0xFF1D1D1F
    muted: int = 0xFF6E6E73
    border: int = 0xFFD2D2D7
    primary: int = 0xFF0071E3
    primary_soft: int = 0xFFE8F2FC
    on_primary: int = 0xFFFFFFFF
    success: int = 0xFF248A3D
    success_soft: int = 0xFFE8F5E9
    on_success: int = 0xFFFFFFFF
    warning: int = 0xFF9A6700
    warning_text: int = 0xFF805500
    warning_soft: int = 0xFFFFF4D6
    danger: int = 0xFFD70015
    danger_soft: int = 0xFFFCE8E9
    on_danger: int = 0xFFFFFFFF
    info: int = 0xFF0071E3
    info_soft: int = 0xFFE8F2FC
    disabled_surface: int = 0xFFE5E5EA
    disabled_text: int = 0xFFAEAEB2
    focus: int = 0xFF409CFF

    # Extended semantic roles; names remain stable for API compatibility.
    secondary: int = 0xFF515154
    on_secondary: int = 0xFFFFFFFF
    secondary_soft: int = 0xFFEAEAEC
    tertiary: int = 0xFF7656A8
    on_tertiary: int = 0xFFFFFFFF
    tertiary_soft: int = 0xFFF0EAF8
    on_background: int = 0xFF1D1D1F
    on_surface: int = 0xFF1D1D1F
    surface_container_lowest: int = 0xFFFFFFFF
    surface_container_low: int = 0xFFFAFAFC
    surface_container: int = 0xFFF2F2F4
    surface_container_high: int = 0xFFEAEAEC
    surface_container_highest: int = 0xFFE0E0E5
    outline: int = 0xFF8E8E93
    outline_variant: int = 0xFFD2D2D7
    inverse_surface: int = 0xFF2C2C2E
    inverse_on_surface: int = 0xFFF5F5F7
    scrim: int = 0x66000000

    # Shape scale — soft but disciplined; pill is reserved for compact controls.
    radius_extra_small: float = 6.0
    radius_small: float = 10.0
    radius_medium: float = 14.0
    radius_large: float = 18.0
    radius_extra_large: float = 24.0
    radius_pill: float = 999.0

    # 4-point spacing scale
    space_1: float = 4.0
    space_2: float = 8.0
    space_3: float = 12.0
    space_4: float = 16.0
    space_5: float = 20.0
    space_6: float = 24.0
    space_8: float = 32.0
    space_10: float = 40.0
    space_12: float = 48.0

    # Shared control metrics
    control_height_small: float = 36.0
    control_height_medium: float = 44.0
    control_height_large: float = 52.0
    icon_button_size_small: float = 36.0
    icon_button_size_medium: float = 44.0
    icon_button_size_large: float = 52.0
    minimum_touch_target: float = 44.0

    # Typography roles, in logical pixels. Inter is the implicit font.
    type_display_large: float = 48.0
    type_display_medium: float = 40.0
    type_headline_large: float = 32.0
    type_headline_medium: float = 28.0
    type_title_large: float = 22.0
    type_title_medium: float = 18.0
    type_body_large: float = 16.0
    type_body_medium: float = 14.0
    type_body_small: float = 12.0
    type_label_large: float = 14.0
    type_label_medium: float = 12.0
    type_label_small: float = 11.0

    # Semantic elevation levels. Actual shadow compositor remains renderer work.
    elevation_0: float = 0.0
    elevation_1: float = 1.0
    elevation_2: float = 3.0
    elevation_3: float = 6.0

    font: FontConfig = FontConfig()

    @classmethod
    def dark(cls) -> "NativeTheme":
        """Return a purpose-designed dark palette, not an inverted light theme."""
        return cls(
            name="yuktara-clarity-dark",
            background=0xFF000000,
            surface=0xFF1C1C1E,
            surface_variant=0xFF2C2C2E,
            foreground=0xFFF5F5F7,
            muted=0xFF98989D,
            border=0xFF38383A,
            primary=0xFF0A84FF,
            primary_soft=0xFF172C43,
            on_primary=0xFFFFFFFF,
            success=0xFF30D158,
            success_soft=0xFF183A27,
            on_success=0xFF06210F,
            warning=0xFFFFD60A,
            warning_text=0xFFFFD60A,
            warning_soft=0xFF3A3214,
            danger=0xFFFF453A,
            danger_soft=0xFF3B1C1C,
            on_danger=0xFFFFFFFF,
            info=0xFF64D2FF,
            info_soft=0xFF173344,
            disabled_surface=0xFF2C2C2E,
            disabled_text=0xFF636366,
            focus=0xFF409CFF,
            secondary=0xFFAEAEB2,
            on_secondary=0xFF1C1C1E,
            secondary_soft=0xFF38383A,
            tertiary=0xFFBF9AF7,
            on_tertiary=0xFF27183D,
            tertiary_soft=0xFF382A4C,
            on_background=0xFFF5F5F7,
            on_surface=0xFFF5F5F7,
            surface_container_lowest=0xFF141416,
            surface_container_low=0xFF1C1C1E,
            surface_container=0xFF242426,
            surface_container_high=0xFF2C2C2E,
            surface_container_highest=0xFF3A3A3C,
            outline=0xFF8E8E93,
            outline_variant=0xFF48484A,
            inverse_surface=0xFFE5E5EA,
            inverse_on_surface=0xFF1C1C1E,
        )
