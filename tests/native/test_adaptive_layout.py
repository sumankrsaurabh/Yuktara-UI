from __future__ import annotations

import pytest

from novaui.native import LayoutEngine, LayoutNode, Rect
from novaui.native.widgets import AdaptiveLayout, AdaptiveVariant


def _variants():
    compact = LayoutNode.column(LayoutNode("text", text="compact"), key="compact")
    wide = LayoutNode.row(
        LayoutNode("text", text="wide-main"),
        LayoutNode("text", text="wide-side"),
        key="wide",
    )
    tall_wide = LayoutNode.grid(
        LayoutNode("text", text="grid-a"),
        LayoutNode("text", text="grid-b"),
        columns=2,
    ) if hasattr(LayoutNode, "grid") else LayoutNode("grid", [
        LayoutNode("text", text="grid-a"), LayoutNode("text", text="grid-b")
    ], grid_columns=2)
    return compact, wide, tall_wide


def test_adaptive_layout_selects_by_both_width_and_height():
    compact, wide, tall_wide = _variants()
    root = AdaptiveLayout(
        variants=(
            AdaptiveVariant(0, 0, compact),
            AdaptiveVariant(700, 0, wide),
            AdaptiveVariant(1000, 700, tall_wide),
        )
    ).build()
    engine = LayoutEngine()

    engine.layout(root, Rect(0, 0, 390, 844))
    assert root.responsive_active_index == 0
    assert root.children == [compact]

    engine.layout(root, Rect(0, 0, 900, 600))
    assert root.responsive_active_index == 1
    assert root.children == [wide]

    engine.layout(root, Rect(0, 0, 1200, 800))
    assert root.responsive_active_index == 2
    assert root.children == [tall_wide]


def test_adaptive_layout_falls_back_when_width_fits_but_height_does_not():
    compact, wide, tall_wide = _variants()
    root = AdaptiveLayout(
        variants=((0, 0, compact), (700, 0, wide), (1000, 700, tall_wide))
    ).build()

    LayoutEngine().layout(root, Rect(0, 0, 1200, 650))

    assert root.children == [wide]


def test_adaptive_layout_reflows_on_resize_without_rebuilding_component():
    from novaui.native import NativeRuntime

    compact, wide, tall_wide = _variants()
    adaptive = AdaptiveLayout(
        variants=((0, 0, compact), (700, 0, wide), (1000, 700, tall_wide))
    )
    class Renderer:
        size = None
        def clear(self, *_args, **_kwargs): pass
        def draw_rect(self, *_args, **_kwargs): pass
        def draw_stroke_rect(self, *_args, **_kwargs): pass
        def draw_text(self, *_args, **_kwargs): pass

    runtime = NativeRuntime(adaptive.build, Renderer(), 390, 844)
    runtime.start()
    try:
        builds = runtime.component.build_count
        runtime.resize(1200, 650)
        assert runtime.root.children == [wide]
        runtime.resize(1200, 800)
        assert runtime.root.children == [tall_wide]
        assert runtime.component.build_count == builds
    finally:
        runtime.stop()


def test_adaptive_variant_thresholds_must_be_unique():
    with pytest.raises(ValueError, match="unique"):
        AdaptiveLayout(variants=((0, 0, LayoutNode.column()), (0, 0, LayoutNode.row()))).build()
    with pytest.raises(ValueError, match="unique"):
        AdaptiveLayout(variants=((0, 0, LayoutNode.column()), (0, 0, LayoutNode.row()))).build()


def test_adaptive_layout_requires_valid_variants():
    with pytest.raises(ValueError, match="at least one"):
        AdaptiveLayout(variants=()).build()
    with pytest.raises(ValueError, match="non-negative"):
        AdaptiveLayout(variants=((-1, 0, LayoutNode.column()),)).build()
