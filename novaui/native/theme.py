"""Yuktara UI semantic color, typography and component design tokens."""
from __future__ import annotations

from dataclasses import dataclass
from .typography import FontConfig


@dataclass(frozen=True, slots=True)
class NativeTheme:
    """Immutable semantic design system consumed by native components.

    Colors use ARGB integers. The original palette and radius names remain
    available for compatibility; newer tokens provide consistent surface,
    spacing, typography and control metrics across the component catalogue.
    """
    name: str = "yuktara-light"

    # Semantic color roles
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

    # Extended Material-style semantic roles
    secondary: int = 0xFF53627D
    on_secondary: int = 0xFFFFFFFF
    secondary_soft: int = 0xFFE9EDF5
    tertiary: int = 0xFF7656A8
    on_tertiary: int = 0xFFFFFFFF
    tertiary_soft: int = 0xFFF0EAF8
    on_background: int = 0xFF202735
    on_surface: int = 0xFF202735
    surface_container_lowest: int = 0xFFFFFFFF
    surface_container_low: int = 0xFFFAFBFC
    surface_container: int = 0xFFF4F5F7
    surface_container_high: int = 0xFFEAEDF1
    surface_container_highest: int = 0xFFE2E6EC
    outline: int = 0xFF8A93A2
    outline_variant: int = 0xFFD9DEE6
    inverse_surface: int = 0xFF293140
    inverse_on_surface: int = 0xFFF3F5F8
    scrim: int = 0x66000000

    # Shape scale; legacy radius names remain stable.
    radius_small: float = 6.0
    radius_medium: float = 10.0
    radius_large: float = 16.0
    radius_pill: float = 999.0
    radius_extra_small: float = 4.0
    radius_extra_large: float = 24.0

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

    # Typography roles, in logical pixels
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

    # Elevation levels are semantic tokens. Current CPU renderer expresses
    # elevation through surface roles and outlines; shadow rendering is future work.
    elevation_0: float = 0.0
    elevation_1: float = 1.0
    elevation_2: float = 3.0
    elevation_3: float = 6.0

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
            secondary=0xFFB8C5E0,
            on_secondary=0xFF263247,
            secondary_soft=0xFF344158,
            tertiary=0xFFD0B7F5,
            on_tertiary=0xFF38264F,
            tertiary_soft=0xFF49365F,
            on_background=0xFFF4F6FA,
            on_surface=0xFFF4F6FA,
            surface_container_lowest=0xFF171D27,
            surface_container_low=0xFF1B222E,
            surface_container=0xFF202735,
            surface_container_high=0xFF2A3444,
            surface_container_highest=0xFF354153,
            outline=0xFF8793A7,
            outline_variant=0xFF465266,
            inverse_surface=0xFFE4EAF4,
            inverse_on_surface=0xFF293140,
        )
