from __future__ import annotations

import pytest

from novaui.native import (
    Label, LayoutEngine, LayoutNode, ListDetailItem, ListDetailPane, Rect,
)


def _pane():
    changes = []
    first = Label("First detail")
    second = Label("Second detail")
    pane = ListDetailPane(
        items=(
            ListDetailItem("First", first, key="first", subtitle="Overview"),
            ListDetailItem("Second", second, key="second", subtitle="Recent activity"),
            ListDetailItem("Locked", Label("Locked detail"), key="locked", disabled=True),
        ),
        on_select=changes.append,
    )
    return pane, changes, first, second


def test_list_detail_uses_single_pane_on_compact_and_two_panes_on_wide():
    pane, _changes, _first, _second = _pane()
    root = pane.build()
    engine = LayoutEngine()

    engine.layout(root, Rect(0, 0, 390, 844))
    assert root.responsive_active_index == 0
    assert root.children[0].children == [pane._list_pane]

    engine.layout(root, Rect(0, 0, 1200, 800))
    assert root.responsive_active_index == 1
    assert root.children[0].children[0] is pane._list_pane
    assert root.children[0].children[1].children[1] is pane._detail_body


def test_compact_list_selection_opens_detail_and_back_returns_to_list():
    pane, changes, first, _second = _pane()
    root = pane.build()
    compact = root.adaptive_variants[0][2]

    compact.children[0].children[1].on_click(None)
    assert pane.selected == "second"
    assert changes == [pane.items[1]]
    assert compact.children == [pane._compact_detail_view]
    assert pane._detail_body.children[0] is pane._content_nodes["second"]

    back = pane._compact_detail_view.children[0].children[0]
    back.on_click(None)
    assert compact.children == [pane._list_pane]
    assert pane.selected == "second"


def test_list_detail_selection_survives_resizing_between_modes():
    pane, _changes, _first, _second = _pane()
    root = pane.build()
    engine = LayoutEngine()

    engine.layout(root, Rect(0, 0, 390, 844))
    root.children[0].children[1].on_click(None)
    selected_content = pane._detail_body.children[0]

    engine.layout(root, Rect(0, 0, 1200, 800))
    assert root.responsive_active_index == 1
    assert pane._detail_body.children[0] is selected_content

    engine.layout(root, Rect(0, 0, 390, 844))
    assert root.responsive_active_index == 0
    assert root.children[0].children[0] is pane._compact_detail_view
    assert pane._detail_body.children[0] is selected_content


def test_list_detail_disabled_items_cannot_be_selected():
    pane, changes, _first, _second = _pane()
    pane.build()
    locked = pane._item_nodes["locked"]
    assert locked.on_click is None
    assert pane.selected is None
    assert changes == []


def test_list_detail_rejects_invalid_items_and_thresholds():
    with pytest.raises(ValueError, match="at least one"):
        ListDetailPane(items=())
    with pytest.raises(ValueError, match="unique"):
        ListDetailPane(items=(
            ListDetailItem("A", Label("A"), key="same"),
            ListDetailItem("B", Label("B"), key="same"),
        ))
    with pytest.raises(ValueError, match="positive"):
        ListDetailPane(
            items=(ListDetailItem("A", Label("A")),),
            min_expanded_width=0,
        )
