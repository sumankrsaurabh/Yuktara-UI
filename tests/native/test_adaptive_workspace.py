from __future__ import annotations

import pytest

from novaui.native import AdaptiveWorkspace, Label, LayoutEngine, Rect


def _workspace():
    workspace = AdaptiveWorkspace(
        content=Label("Editor"),
        sidebar=Label("Files"),
        inspector=Label("Properties"),
    )
    return workspace


def test_workspace_selects_one_two_and_three_pane_compositions():
    workspace = _workspace()
    root = workspace.build()
    engine = LayoutEngine()

    engine.layout(root, Rect(0, 0, 390, 844))
    assert root.responsive_active_index == 0
    assert root.children[0].accessibility_label == "Compact workspace"

    engine.layout(root, Rect(0, 0, 900, 600))
    assert root.responsive_active_index == 1
    assert root.children[0].accessibility_label == "Two-pane workspace"

    engine.layout(root, Rect(0, 0, 1440, 900))
    assert root.responsive_active_index == 2
    assert root.children[0].accessibility_label == "Three-pane workspace"


def test_workspace_retains_all_pane_nodes_across_resizing():
    workspace = _workspace()
    root = workspace.build()
    compact, medium, expanded = [entry[2] for entry in root.adaptive_variants]

    assert compact.children == [workspace._content_node]
    assert medium.children == [workspace._sidebar_node, workspace._content_node]
    assert expanded.children == [
        workspace._sidebar_node, workspace._content_node, workspace._inspector_node
    ]


def test_workspace_can_omit_optional_panes():
    workspace = AdaptiveWorkspace(content=Label("Canvas"), sidebar=Label("Tools"))
    root = workspace.build()

    assert len(root.adaptive_variants) == 2
    LayoutEngine().layout(root, Rect(0, 0, 1000, 800))
    assert root.responsive_active_index == 1


def test_workspace_rejects_invalid_breakpoints_and_spacing():
    with pytest.raises(ValueError, match="exceed"):
        AdaptiveWorkspace(
            content=Label("Editor"),
            min_two_pane_width=900,
            min_three_pane_width=800,
        )
    with pytest.raises(ValueError, match="non-negative"):
        AdaptiveWorkspace(content=Label("Editor"), pane_spacing=-1)
