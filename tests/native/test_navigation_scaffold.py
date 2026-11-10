from __future__ import annotations

from novaui.native import LayoutEngine, LayoutNode, NavigationItem, NavigationScaffold, Rect


def _scaffold():
    changes = []
    content = LayoutNode.column(LayoutNode("text", text="Workspace"), key="workspace")
    scaffold = NavigationScaffold(
        items=(
            NavigationItem("Home", icon="⌂", key="home"),
            NavigationItem("Projects", icon="▦", key="projects"),
            NavigationItem("Settings", icon="⚙", key="settings"),
        ),
        content=content,
        selected="home",
        on_select=changes.append,
    )
    return scaffold, changes, content


def test_navigation_scaffold_switches_bottom_rail_and_drawer_by_window_size():
    scaffold, _changes, _content = _scaffold()
    root = scaffold.build()
    engine = LayoutEngine()

    engine.layout(root, Rect(0, 0, 390, 844))
    assert root.responsive_active_index == 0
    assert root.children[0].children[1].accessibility_label == "Bottom navigation"

    engine.layout(root, Rect(0, 0, 800, 900))
    assert root.responsive_active_index == 1
    assert root.children[0].children[0].accessibility_label == "Navigation rail"

    engine.layout(root, Rect(0, 0, 1440, 900))
    assert root.responsive_active_index == 2
    assert root.children[0].children[0].accessibility_label == "Main navigation"


def test_navigation_scaffold_selection_is_preserved_across_all_modes():
    scaffold, changes, _content = _scaffold()
    root = scaffold.build()
    engine = LayoutEngine()

    engine.layout(root, Rect(0, 0, 390, 844))
    compact_items = root.children[0].children[1].children
    compact_items[1].on_click(None)

    assert scaffold.selected == "projects"
    assert changes == [scaffold.items[1]]
    assert all(
        node.accessibility_selected
        for node in scaffold._item_nodes["projects"]
    )
    assert all(
        not node.accessibility_selected
        for node in scaffold._item_nodes["home"]
    )

    engine.layout(root, Rect(0, 0, 800, 900))
    assert root.responsive_active_index == 1
    assert root.children[0].children[0].children[1].accessibility_selected

    engine.layout(root, Rect(0, 0, 1440, 900))
    assert root.responsive_active_index == 2
    assert root.children[0].children[0].children[1].accessibility_selected


def test_navigation_scaffold_retains_one_content_node_across_compositions():
    scaffold, _changes, content = _scaffold()
    root = scaffold.build()
    compact, rail, drawer = [entry[2] for entry in root.adaptive_variants]

    assert compact.children[0].children[0] is scaffold._content_node
    assert rail.children[1] is scaffold._content_node
    assert drawer.children[1] is scaffold._content_node
    assert scaffold._content_node.children[0] is content


def test_navigation_scaffold_disabled_item_cannot_be_selected():
    scaffold = NavigationScaffold(
        items=(NavigationItem("Home", key="home"),
               NavigationItem("Locked", disabled=True, key="locked")),
        content=LayoutNode.column(),
        selected="home",
    )
    root = scaffold.build()
    root.adaptive_variants[0][2].children[1].children[1].on_click(None)
    assert scaffold.selected == "home"


def test_navigation_scaffold_validates_items_and_breakpoints():
    import pytest

    with pytest.raises(ValueError, match="at least one"):
        NavigationScaffold(items=(), content=LayoutNode.column())
    with pytest.raises(ValueError, match="exceed"):
        NavigationScaffold(
            items=(NavigationItem("Home"),), content=LayoutNode.column(),
            min_rail_width=800, min_drawer_width=700,
        )
