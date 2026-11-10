from __future__ import annotations

import pytest

from novaui.native import (
    Button,
    Dropdown,
    LayoutNode,
    ProgressBar,
    Slider,
    TextField,
    build_accessibility_tree,
)
from novaui.native.layout import LayoutEngine, Rect
from novaui.native.overlays import OverlayManager


def test_semantic_snapshot_preserves_provider_metadata_and_logical_bounds():
    control = LayoutNode(
        "box",
        accessibility_role="textbox",
        accessibility_label="Email address",
        accessibility_identifier="profile.email",
        accessibility_role_description="Email input",
        accessibility_read_only=False,
        accessibility_required=True,
        accessibility_invalid=False,
        accessibility_live="polite",
        accessibility_actions=("focus", "set_value"),
    )
    root = LayoutNode.column(control, accessibility_role="group")
    LayoutEngine().layout(root, Rect(0, 0, 320, 120))

    snapshot = build_accessibility_tree(root)
    semantic = snapshot.children[0]

    assert semantic.identifier == "profile.email"
    assert semantic.role_description == "Email input"
    assert semantic.read_only is False
    assert semantic.required is True
    assert semantic.invalid is False
    assert semantic.live == "polite"
    assert semantic.actions == ("focus", "set_value")
    assert semantic.bounds == control.bounds


def test_hidden_node_prunes_entire_subtree():
    hidden = LayoutNode.column(
        LayoutNode("text", text="Secret", accessibility_role="text",
                   accessibility_identifier="secret.text"),
        accessibility_role="group",
        accessibility_identifier="secret.group",
        accessibility_hidden=True,
    )
    visible = LayoutNode("text", text="Public", accessibility_role="text",
                         accessibility_identifier="public.text")
    root = LayoutNode.column(hidden, visible, accessibility_role="group")

    snapshot = build_accessibility_tree(root)

    assert [child.identifier for child in snapshot.children] == ["public.text"]


def test_visible_accessibility_identifiers_must_be_unique():
    root = LayoutNode.column(
        LayoutNode("box", accessibility_role="button", accessibility_identifier="save"),
        LayoutNode("box", accessibility_role="button", accessibility_identifier="save"),
    )

    with pytest.raises(ValueError, match="duplicate accessibility identifier: save"):
        build_accessibility_tree(root)


def test_hidden_duplicate_identifiers_do_not_conflict_with_visible_nodes():
    root = LayoutNode.column(
        LayoutNode("box", accessibility_role="group", accessibility_identifier="same",
                   accessibility_hidden=True),
        LayoutNode("box", accessibility_role="button", accessibility_identifier="same"),
    )

    snapshot = build_accessibility_tree(root)

    assert len(snapshot.children) == 1
    assert snapshot.children[0].identifier == "same"


def test_modal_scope_is_built_before_unique_identifier_validation():
    root = LayoutNode("box", accessibility_role="group", accessibility_identifier="shared")
    manager = OverlayManager()
    dialog = LayoutNode("box", accessibility_role="dialog", accessibility_identifier="shared")
    manager.show_dialog(dialog)

    snapshot = build_accessibility_tree(root, overlays=manager.entries)

    assert snapshot.role == "application"
    assert len(snapshot.children) == 1
    assert snapshot.children[0].role == "dialog-overlay"
    assert snapshot.children[0].children[0].identifier == "shared"


def test_non_modal_overlay_duplicate_identifier_is_rejected():
    root = LayoutNode("box", accessibility_role="group", accessibility_identifier="shared")
    manager = OverlayManager()
    manager.show_popover(
        LayoutNode("box", accessibility_role="group", accessibility_identifier="shared"),
        anchor=Rect(0, 0, 20, 20),
    )

    with pytest.raises(ValueError, match="duplicate accessibility identifier"):
        build_accessibility_tree(root, overlays=manager.entries)


def test_range_metadata_round_trips_and_rejects_invalid_bounds():
    slider = LayoutNode(
        "box", accessibility_role="slider",
        accessibility_range_min=5, accessibility_range_max=25,
        accessibility_range_value=15,
    )
    semantic = build_accessibility_tree(slider)
    assert (semantic.range_min, semantic.range_max, semantic.range_value) == (5, 25, 15)

    with pytest.raises(ValueError, match="cannot exceed"):
        LayoutNode("box", accessibility_range_min=10, accessibility_range_max=2)
    with pytest.raises(ValueError, match="below"):
        LayoutNode("box", accessibility_range_min=2, accessibility_range_value=1)
    with pytest.raises(ValueError, match="finite number"):
        LayoutNode("box", accessibility_range_value=float("nan"))


def test_accessibility_metadata_validation_is_explicit():
    with pytest.raises(ValueError, match="orientation"):
        LayoutNode("box", accessibility_orientation="diagonal")
    with pytest.raises(ValueError, match="live"):
        LayoutNode("box", accessibility_live="urgent")
    with pytest.raises(ValueError, match="supported actions"):
        LayoutNode("box", accessibility_actions=("teleport",))
    with pytest.raises(ValueError, match="duplicates"):
        LayoutNode("box", accessibility_actions=("activate", "activate"))
    with pytest.raises(ValueError, match="non-empty string"):
        LayoutNode("box", accessibility_identifier="   ")


def test_standard_widgets_publish_range_read_only_and_action_metadata():
    progress = build_accessibility_tree(ProgressBar(65, label="Upload").build())
    assert (progress.range_min, progress.range_max, progress.range_value) == (0, 100, 65)
    assert progress.read_only is True

    slider_widget = Slider(value=10, minimum=0, maximum=20, step=2)
    slider_node = slider_widget.build()
    slider = build_accessibility_tree(slider_node)
    assert (slider.range_min, slider.range_max, slider.range_value) == (0, 20, 10)
    assert slider.orientation == "horizontal"
    assert slider.actions == ("decrement", "increment", "set_value")
    slider_widget._set_value(14)
    assert build_accessibility_tree(slider_node).range_value == 14

    field = build_accessibility_tree(TextField("locked", read_only=True).build())
    assert field.read_only is True

    button = build_accessibility_tree(Button("Save").build())
    assert button.actions == ("activate",)

    dropdown = build_accessibility_tree(Dropdown(("One", "Two")).build())
    assert dropdown.role_description == "Option selector"
    assert dropdown.actions == ("collapse", "expand", "set_value")


def test_semantic_snapshot_excludes_content_behind_the_topmost_modal():
    root = LayoutNode.column(
        LayoutNode("box", accessibility_role="button", accessibility_identifier="underlying"),
        accessibility_role="group",
    )
    manager = OverlayManager()
    manager.show_popover(
        LayoutNode("box", accessibility_role="group", accessibility_identifier="behind"),
        anchor=Rect(0, 0, 10, 10),
    )
    manager.show_dialog(
        LayoutNode("box", accessibility_role="dialog", accessibility_identifier="active")
    )

    snapshot = build_accessibility_tree(root, overlays=manager.entries)

    assert len(snapshot.children) == 1
    assert snapshot.children[0].children[0].identifier == "active"
