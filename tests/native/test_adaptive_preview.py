from __future__ import annotations

import pytest

from novaui.native import (
    AdaptiveLayout, AdaptivePreviewHarness, AdaptiveVariant, LayoutNode,
    Responsive, ViewportProfile,
)


def _profiles():
    return (
        ViewportProfile("phone", 390, 844, 1),
        ViewportProfile("tablet", 900, 1200, 2),
        ViewportProfile("desktop", 1440, 900, 1.5),
    )


def test_preview_runs_real_adaptive_layout_at_each_profile():
    compact = LayoutNode.column(LayoutNode("text", text="phone"), key="compact")
    wide = LayoutNode.row(
        LayoutNode("text", text="main"),
        LayoutNode("text", text="inspector"),
        key="wide",
    )
    root = AdaptiveLayout((
        AdaptiveVariant(0, 0, compact),
        AdaptiveVariant(700, 0, wide),
    )).build()

    previews = AdaptivePreviewHarness(root, _profiles()).run()

    assert [preview.active_variant_index for preview in previews] == [0, 1, 1]
    assert previews[0].nodes[-1].key == "compact"
    assert previews[1].nodes[-1].key == "wide"
    assert previews[1].backing_pixel_size == (1800, 2400)
    assert previews[2].backing_pixel_size == (2160, 1350)


def test_preview_records_bounds_and_active_nested_variants():
    inner = Responsive((
        (0, LayoutNode.column(LayoutNode("text", text="narrow"))),
        (500, LayoutNode.row(LayoutNode("text", text="wide"))),
    )).build()
    root = LayoutNode.column(inner)
    previews = AdaptivePreviewHarness(
        root,
        (ViewportProfile("small", 360, 700), ViewportProfile("large", 800, 700)),
    ).run()

    assert previews[0].nodes[1].active_variant_index == 0
    assert previews[1].nodes[1].active_variant_index == 1
    assert previews[1].nodes[1].bounds == pytest.approx((0, 0, 800, 700))
    assert previews[0].active_variant_index is None


def test_preview_uses_same_root_across_viewports_and_does_not_rebuild_nodes():
    compact = LayoutNode.column(LayoutNode("text", text="compact"))
    expanded = LayoutNode.row(LayoutNode("text", text="expanded"))
    root = AdaptiveLayout(((0, 0, compact), (700, 0, expanded))).build()
    harness = AdaptivePreviewHarness(root, _profiles())

    first = harness.run()
    second = harness.run()

    assert first[0].nodes == second[0].nodes
    assert root.adaptive_variants[0][2] is compact
    assert root.adaptive_variants[1][2] is expanded


@pytest.mark.parametrize(
    "profile",
    [
        ViewportProfile("", 390, 844),
        ViewportProfile("zero-width", 0, 844),
        ViewportProfile("negative-height", 390, -1),
        ViewportProfile("zero-scale", 390, 844, 0),
    ],
)
def test_viewport_profile_rejects_invalid_dimensions(profile):
    # Construction is expected to fail before this test body is reached.
    assert profile.width > 0


def test_preview_rejects_invalid_roots_profiles_and_duplicate_names():
    with pytest.raises(TypeError, match="LayoutNode"):
        AdaptivePreviewHarness(object(), _profiles())
    with pytest.raises(ValueError, match="at least one"):
        AdaptivePreviewHarness(LayoutNode.column(), ())
    with pytest.raises(ValueError, match="unique"):
        AdaptivePreviewHarness(
            LayoutNode.column(),
            (ViewportProfile("same", 400, 800), ViewportProfile("same", 800, 600)),
        )
