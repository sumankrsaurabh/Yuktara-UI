from __future__ import annotations

import pytest

from novaui.native import (
    LayoutEngine,
    LayoutNode,
    NativeRuntime,
    Rect,
    Responsive,
    ResponsiveVariant,
)


def _variants():
    compact = LayoutNode.column(
        LayoutNode("text", text="compact"),
        key="compact-content",
    )
    medium = LayoutNode.row(
        LayoutNode("text", text="medium-main"),
        LayoutNode("text", text="medium-side"),
        key="medium-content",
    )
    expanded = LayoutNode(
        "grid",
        [
            LayoutNode("text", text="expanded-a"),
            LayoutNode("text", text="expanded-b"),
        ],
        grid_columns=2,
        key="expanded-content",
    )
    return compact, medium, expanded


def test_responsive_selects_compact_medium_and_expanded_variants():
    compact, medium, expanded = _variants()
    root = Responsive(
        variants=(
            ResponsiveVariant(0, compact),
            ResponsiveVariant(600, medium),
            ResponsiveVariant(960, expanded),
        )
    ).build()
    engine = LayoutEngine()

    engine.layout(root, Rect(0, 0, 390, 844))
    assert root.responsive_active_index == 0
    assert root.children == [compact]
    assert compact.bounds.width == pytest.approx(390)

    engine.layout(root, Rect(0, 0, 800, 900))
    assert root.responsive_active_index == 1
    assert root.children == [medium]
    assert medium.bounds.width == pytest.approx(800)

    engine.layout(root, Rect(0, 0, 1440, 900))
    assert root.responsive_active_index == 2
    assert root.children == [expanded]
    assert expanded.bounds.width == pytest.approx(1440)


def test_responsive_uses_first_variant_below_first_threshold():
    root = Responsive(
        variants=(
            (480, LayoutNode.column(LayoutNode("text", text="small"))),
            (900, LayoutNode.row(LayoutNode("text", text="large"))),
        )
    ).build()

    LayoutEngine().layout(root, Rect(0, 0, 360, 740))

    assert root.responsive_active_index == 0
    assert root.children[0].kind == "column"


def test_responsive_variants_must_be_ordered_and_unique():
    with pytest.raises(ValueError, match="strictly increasing"):
        Responsive(
            variants=(
                (0, LayoutNode.column()),
                (600, LayoutNode.row()),
                (600, LayoutNode("grid")),
            )
        ).build()


class _RecordingRenderer:
    size = None

    def clear(self, *_args, **_kwargs):
        pass

    def draw_rect(self, *_args, **_kwargs):
        pass

    def draw_stroke_rect(self, *_args, **_kwargs):
        pass

    def draw_text(self, *_args, **_kwargs):
        pass


def test_native_runtime_resize_reflows_responsive_tree_without_component_rebuild():
    compact, medium, expanded = _variants()
    responsive = Responsive(
        variants=(
            (0, compact),
            (600, medium),
            (960, expanded),
        )
    )
    runtime = NativeRuntime(
        lambda: responsive.build(),
        _RecordingRenderer(),
        390,
        844,
    )
    runtime.start()
    try:
        initial_build_count = runtime.component.build_count
        assert runtime.root.responsive_active_index == 0

        runtime.resize(800, 900)
        assert runtime.root.responsive_active_index == 1
        assert runtime.component.build_count == initial_build_count

        runtime.resize(1440, 900)
        assert runtime.root.responsive_active_index == 2
        assert runtime.component.build_count == initial_build_count

        runtime.resize(390, 844)
        assert runtime.root.responsive_active_index == 0
        assert runtime.component.build_count == initial_build_count
    finally:
        runtime.stop()
