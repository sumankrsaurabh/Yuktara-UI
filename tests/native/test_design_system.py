from __future__ import annotations

import pytest

from novaui.native import (
    Button, IconButton, NativeTheme, Surface,
)


def test_theme_exposes_consistent_color_shape_spacing_and_type_tokens():
    light = NativeTheme()
    dark = NativeTheme.dark()

    assert light.surface_container_lowest == light.surface
    assert light.surface_container_highest != light.surface_container_lowest
    assert light.radius_extra_large > light.radius_large
    assert [light.space_1, light.space_2, light.space_3, light.space_4] == [4, 8, 12, 16]
    assert light.control_height_medium >= light.minimum_touch_target
    assert light.type_title_large > light.type_body_large
    assert dark.on_surface != light.on_surface
    assert dark.secondary_soft != light.secondary_soft


@pytest.mark.parametrize("variant", sorted(Button.VARIANTS))
def test_button_variants_share_accessibility_and_minimum_control_metrics(variant):
    theme = NativeTheme()
    node = Button("Continue", variant=variant, theme=theme).build()

    assert node.accessibility_role == "button"
    assert node.accessibility_label == "Continue"
    assert node.min_height == theme.control_height_medium
    assert node.on_pointer_enter is not None
    assert node.on_pointer_down is not None


def test_button_has_distinct_hover_pressed_and_focus_visual_states():
    theme = NativeTheme()
    node = Button("Save", theme=theme).build()
    resting = node.background

    node.on_pointer_enter(None)
    hovered = node.background
    assert hovered != resting

    node.on_pointer_down(None)
    pressed = node.background
    assert pressed != hovered

    node.on_focus(None)
    assert node.border_color == theme.focus
    assert node.border_width == 2

    node.on_pointer_up(None)
    node.on_pointer_leave(None)
    node.on_blur(None)
    assert node.background == resting
    assert node.border_color is None
    assert node.border_width == 0


def test_disabled_button_does_not_install_interaction_handlers():
    node = Button("Unavailable", disabled=True).build()

    assert node.on_click is None
    assert node.on_pointer_enter is None
    assert node.on_pointer_down is None
    assert node.on_focus is None
    assert node.accessibility_disabled is True


def test_icon_button_has_accessible_name_and_consistent_square_target():
    theme = NativeTheme()
    node = IconButton("＋", "Create item", theme=theme).build()

    assert node.text == "＋"
    assert node.accessibility_role == "button"
    assert node.accessibility_label == "Create item"
    assert node.width == theme.icon_button_size_medium
    assert node.min_width == theme.icon_button_size_medium
    assert node.min_height == theme.icon_button_size_medium


def test_icon_button_requires_accessible_label_and_valid_variant():
    with pytest.raises(ValueError, match="accessible name"):
        IconButton("⚙", "")
    with pytest.raises(ValueError, match="variant"):
        IconButton("⚙", "Settings", variant="neon")


def test_surface_variants_use_semantic_container_roles():
    theme = NativeTheme()
    low = Surface(variant="low", theme=theme).build()
    high = Surface(variant="high", theme=theme).build()
    outlined = Surface(variant="outlined", theme=theme).build()

    assert low.background == theme.surface_container_low
    assert high.background == theme.surface_container_high
    assert outlined.background == theme.surface
    assert outlined.border_color == theme.outline_variant
    assert outlined.border_width == 1
    assert low.accessibility_role == "group"


def test_surface_rejects_invalid_variant_and_negative_padding():
    with pytest.raises(ValueError, match="variant"):
        Surface(variant="glass")
    with pytest.raises(ValueError, match="padding"):
        Surface(padding=-1)
