from __future__ import annotations

import pytest

from novaui.native import Alert, AppBar, Button, IconButton, NativeTheme


def test_app_bar_has_consistent_toolbar_semantics_and_height():
    theme = NativeTheme()
    node = AppBar("Workspace", theme=theme).build()

    assert node.accessibility_role == "toolbar"
    assert node.accessibility_label == "Workspace"
    assert node.height == 64
    assert node.background == theme.surface_container_low
    assert len(node.children) == 1


def test_app_bar_composes_leading_title_subtitle_and_actions():
    theme = NativeTheme()
    leading = IconButton("←", "Back", theme=theme)
    action = IconButton("＋", "Create", theme=theme)
    node = AppBar(
        "Documents",
        subtitle="All your files",
        leading=leading,
        actions=(action,),
        size="prominent",
        variant="outlined",
        theme=theme,
    ).build()

    assert node.height == 88
    assert node.border_width == 1
    assert len(node.children) == 3
    assert node.children[0].accessibility_label == "Back"
    title_block = node.children[1]
    assert [child.text for child in title_block.children] == ["Documents", "All your files"]
    assert node.children[2].accessibility_label == "Create"
    assert title_block.weight == 1


def test_app_bar_supports_compact_flat_variant():
    theme = NativeTheme()
    node = AppBar("Settings", size="compact", variant="flat", theme=theme).build()

    assert node.height == 56
    assert node.background == theme.background
    assert node.border_width == 0


@pytest.mark.parametrize("kwargs,match", [
    ({"title": ""}, "title"),
    ({"title": "Home", "variant": "glass"}, "variant"),
    ({"title": "Home", "size": "tiny"}, "size"),
    ({"title": "Home", "actions": "not-a-list"}, "actions"),
    ({"title": "Home", "actions": (None,)}, "None"),
])
def test_app_bar_rejects_invalid_configuration(kwargs, match):
    with pytest.raises((ValueError, TypeError), match=match):
        AppBar(**kwargs)


@pytest.mark.parametrize("variant", sorted(Alert.VARIANTS))
def test_alert_uses_semantic_color_and_live_region_roles(variant):
    theme = NativeTheme()
    node = Alert("Connection restored", title="You're back", variant=variant, theme=theme).build()

    assert node.accessibility_label == "You're back"
    assert node.accessibility_value == "Connection restored"
    assert node.accessibility_live == ("assertive" if variant == "danger" else "polite")
    assert node.border_width == 1
    assert node.background is not None
    assert node.children[1].children[0].text == "You're back"
    assert node.children[1].children[1].text == "Connection restored"


def test_alert_without_title_uses_message_as_accessible_name():
    node = Alert("Your changes were saved", variant="success").build()

    assert node.accessibility_role == "status"
    assert node.accessibility_label == "Your changes were saved"
    assert node.accessibility_value is None


@pytest.mark.parametrize("kwargs,match", [
    ({"message": ""}, "message"),
    ({"message": "Hello", "variant": "neutral"}, "variant"),
    ({"message": "Hello", "icon": 5}, "icon"),
])
def test_alert_rejects_invalid_configuration(kwargs, match):
    with pytest.raises((ValueError, TypeError), match=match):
        Alert(**kwargs)
