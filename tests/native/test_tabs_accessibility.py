from __future__ import annotations

from types import SimpleNamespace

import pytest

from novaui.native import NativeTheme, TabItem, Tabs


def key_event(keycode):
    return SimpleNamespace(key=SimpleNamespace(keycode=keycode))


LEFT = (1 << 30) | 80
RIGHT = (1 << 30) | 79
HOME = (1 << 30) | 74
END = (1 << 30) | 77


def test_tabs_skip_disabled_items_and_select_next_enabled_item_with_arrow_keys():
    changed = []
    tabs = Tabs(
        [TabItem("Overview"), TabItem("Billing", disabled=True), TabItem("Members")],
        on_change=changed.append,
    )
    root = tabs.build()

    assert tabs.value == "Overview"
    assert root.children[0].accessibility_role == "tablist"
    assert root.children[1].accessibility_role == "tabpanel"
    assert root.children[1].accessibility_label == "Overview panel"

    assert tabs._tab_nodes["Overview"].on_key_down(key_event(RIGHT)) is True
    assert tabs.value == "Members"
    assert changed == ["Members"]
    assert tabs._tab_nodes["Billing"].accessibility_disabled is True
    assert tabs._tab_nodes["Billing"].on_click is None


def test_tabs_support_home_and_end_navigation():
    tabs = Tabs(["One", "Two", "Three"])
    tabs.build()

    assert tabs._tab_nodes["One"].on_key_down(key_event(END)) is True
    assert tabs.value == "Three"
    assert tabs._tab_nodes["Three"].on_key_down(key_event(HOME)) is True
    assert tabs.value == "One"


def test_tabs_keyboard_navigation_wraps_and_syncs_selected_panel():
    tabs = Tabs(["One", "Two", "Three"])
    root = tabs.build()

    tabs._tab_nodes["One"].on_key_down(key_event(LEFT))
    assert tabs.value == "Three"
    assert tabs._tab_nodes["Three"].accessibility_selected is True
    assert tabs._tab_nodes["One"].accessibility_selected is False
    assert root.children[1].accessibility_label == "Three panel"


def test_tabs_click_updates_value_and_calls_change_callback():
    changed = []
    tabs = Tabs(["One", "Two"], on_change=changed.append)
    tabs.build()

    tabs._tab_nodes["Two"].on_click(None)

    assert tabs.value == "Two"
    assert changed == ["Two"]


def test_tabs_reject_all_disabled_or_disabled_initial_selection():
    with pytest.raises(ValueError, match="at least one enabled"):
        Tabs([TabItem("Unavailable", disabled=True)])

    with pytest.raises(ValueError, match="disabled tab"):
        Tabs([TabItem("Unavailable", disabled=True), TabItem("Available")], value="Unavailable")


def test_tabs_reject_invalid_item_and_callback_configuration():
    with pytest.raises(ValueError, match="label"):
        TabItem(" ")

    with pytest.raises(TypeError, match="disabled"):
        TabItem("Overview", disabled=1)

    with pytest.raises(TypeError, match="on_change"):
        Tabs(["Overview"], on_change="not-callable")


def test_tabs_use_shared_theme_metrics():
    theme = NativeTheme()
    tabs = Tabs(["Overview"], theme=theme)
    root = tabs.build()
    tablist = root.children[0]
    tab = tablist.children[0]

    assert tablist.spacing == theme.space_1
    assert tab.padding.left == theme.space_4
    assert tab.padding.top == theme.space_3
    assert tab.font_size == theme.type_label_large
