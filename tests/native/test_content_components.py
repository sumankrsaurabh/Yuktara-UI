from __future__ import annotations

import pytest

from novaui.native import (
    Avatar, Chip, FloatingActionButton, ListTile, NativeTheme,
)


def test_floating_action_button_sizes_are_accessible_and_consistent():
    theme = NativeTheme()
    for size, expected in (("small", 48), ("regular", 56), ("large", 96)):
        node = FloatingActionButton("Create item", size=size, theme=theme).build()
        assert node.accessibility_role == "button"
        assert node.accessibility_label == "Create item"
        assert node.width == expected
        assert node.height == expected
        assert node.min_width == expected
        assert node.min_height == expected


def test_extended_fab_keeps_text_and_accessible_label():
    node = FloatingActionButton("New document", icon="+", extended=True).build()

    assert node.text == "+  New document"
    assert node.accessibility_label == "New document"
    assert node.width is None
    assert node.min_height == 56


def test_fab_disabled_state_has_no_activation():
    node = FloatingActionButton("Create", disabled=True).build()

    assert node.on_click is None
    assert node.accessibility_disabled is True


def test_chip_variants_and_selection_semantics():
    for variant in Chip.VARIANTS:
        node = Chip("Filter", variant=variant, selected=True).build()
        assert node.accessibility_label == "Filter"
        assert node.accessibility_selected is True
        assert node.min_height == 32


def test_chip_click_and_disabled_behavior():
    calls = []
    active = Chip("Selected", on_click=lambda event: calls.append("clicked")).build()
    active.on_click(None)
    disabled = Chip("Locked", disabled=True, on_click=lambda event: calls.append("bad")).build()

    assert calls == ["clicked"]
    assert disabled.on_click is None
    assert disabled.accessibility_disabled is True


def test_avatar_has_stable_dimensions_and_accessible_description():
    theme = NativeTheme()
    node = Avatar("Suman Kumar", initials="SK", size="large", theme=theme).build()

    assert node.text == "SK"
    assert node.width == 56
    assert node.height == 56
    assert node.radius == theme.radius_pill
    assert node.accessibility_role == "image"
    assert node.accessibility_label == "Suman Kumar"


def test_avatar_rejects_missing_accessible_name():
    with pytest.raises(ValueError, match="accessible label"):
        Avatar("")


def test_list_tile_composes_leading_title_subtitle_and_trailing():
    tile = ListTile(
        "Documents",
        subtitle="12 files",
        leading=Avatar("Documents", initials="D"),
        trailing=Chip("Synced"),
    ).build()

    assert tile.accessibility_role == "listitem"
    assert tile.accessibility_label == "Documents"
    assert len(tile.children) == 3
    title_block = tile.children[1]
    assert title_block.children[0].text == "Documents"
    assert title_block.children[1].text == "12 files"


def test_list_tile_click_reaches_deep_text_and_selected_semantics():
    calls = []
    tile = ListTile(
        "Open settings",
        selected=True,
        on_click=lambda event: calls.append("open"),
    ).build()
    title = tile.children[0].children[0]

    assert tile.accessibility_role == "button"
    assert tile.accessibility_selected is True
    assert title.on_click is None
    assert title.on_pointer_up is not None
    title.on_pointer_up(None)
    assert calls == ["open"]


def test_disabled_list_tile_does_not_install_row_activation():
    tile = ListTile(
        "Unavailable",
        disabled=True,
        on_click=lambda event: pytest.fail("disabled tile activated"),
    ).build()

    assert tile.accessibility_disabled is True
    assert tile.on_click is None


def test_content_components_validate_inputs():
    with pytest.raises(ValueError, match="size"):
        FloatingActionButton("Create", size="tiny")
    with pytest.raises(ValueError, match="variant"):
        Chip("Filter", variant="purple")
    with pytest.raises(TypeError, match="booleans"):
        ListTile("Title", selected="yes")
