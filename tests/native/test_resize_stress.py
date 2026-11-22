from __future__ import annotations

from math import isfinite

import pytest

from novaui.native import LayoutNode, NativeRuntime
from novaui.native.layout import Size


class RecordingRenderer:
    size = None

    def clear(self, *_args, **_kwargs):
        pass

    def draw_rect(self, *_args, **_kwargs):
        pass

    def draw_stroke_rect(self, *_args, **_kwargs):
        pass

    def draw_text(self, *_args, **_kwargs):
        pass


def _assert_finite_layout(node):
    for value in (node.bounds.x, node.bounds.y, node.bounds.width, node.bounds.height):
        assert isfinite(value)
    assert node.bounds.width >= 0
    assert node.bounds.height >= 0
    for child in node.children:
        _assert_finite_layout(child)


def _build_responsive_tree():
    compact = LayoutNode.column(
        LayoutNode("text", text="Header", height=48),
        LayoutNode(
            "scroll",
            [LayoutNode.column(*[
                LayoutNode("text", text=f"Compact item {index}", height=36)
                for index in range(24)
            ], spacing=6)],
            scroll_axis="vertical",
            key="compact-scroll",
        ),
        spacing=12,
        key="compact-layout",
    )
    expanded = LayoutNode.column(
        LayoutNode("row", children=[
            LayoutNode("text", text=f"Toolbar {index}", width=140, height=40)
            for index in range(8)
        ], spacing=8, flex_wrap=True, wrap_spacing=8),
        LayoutNode(
            "grid",
            children=[
                LayoutNode("box", intrinsic_size=Size(100, 72))
                for _ in range(18)
            ],
            grid_columns=4,
            grid_min_column_width=120,
            grid_column_gap=12,
            grid_row_gap=12,
        ),
        spacing=16,
        key="expanded-layout",
    )
    return LayoutNode(
        "responsive",
        responsive_variants=((0, compact), (720, expanded)),
        key="root",
    )


@pytest.mark.parametrize(
    "width,height,scale_x,scale_y",
    [
        (320, 568, 1.0, 1.0),
        (360, 800, 2.0, 2.0),
        (568, 320, 1.5, 1.5),
        (768, 1024, 1.25, 1.5),
        (1024, 768, 2.0, 2.0),
        (1366, 768, 1.0, 1.0),
        (1920, 1080, 1.5, 1.5),
        (2560, 1440, 2.0, 2.0),
        (3840, 2160, 1.0, 1.0),
    ],
)
def test_runtime_layout_remains_finite_across_viewports_and_dpi(
    width, height, scale_x, scale_y
):
    runtime = NativeRuntime(_build_responsive_tree, RecordingRenderer(), 800, 600)
    runtime.start()
    try:
        runtime.resize(
            width,
            height,
            pixel_width=round(width * scale_x),
            pixel_height=round(height * scale_y),
        )

        assert (runtime.width, runtime.height) == (float(width), float(height))
        assert runtime.scale_x == pytest.approx(scale_x)
        assert runtime.scale_y == pytest.approx(scale_y)
        assert runtime.root.bounds.width == pytest.approx(width)
        assert runtime.root.bounds.height == pytest.approx(height)
        assert runtime.root.responsive_active_index == (1 if width >= 720 else 0)
        _assert_finite_layout(runtime.root)
    finally:
        runtime.stop()


def test_rapid_resize_sequence_reflows_without_rebuilding_component():
    runtime = NativeRuntime(_build_responsive_tree, RecordingRenderer(), 390, 844)
    runtime.start()
    try:
        initial_build_count = runtime.component.build_count
        sizes = [
            (1280, 800), (640, 360), (1920, 1080), (375, 812),
            (900, 600), (320, 568), (2560, 1440), (540, 960),
            (1440, 900), (390, 844),
        ] * 5

        for width, height in sizes:
            runtime.resize(width, height)
            assert runtime.root.bounds.width == pytest.approx(width)
            assert runtime.root.bounds.height == pytest.approx(height)
            assert runtime.root.responsive_active_index == (1 if width >= 720 else 0)
            _assert_finite_layout(runtime.root)

        assert runtime.component.build_count == initial_build_count
        assert runtime.frame_count == 1 + len(sizes)
    finally:
        runtime.stop()


def test_resize_clamps_scroll_offsets_when_viewport_shrinks_then_grows():
    scroll = LayoutNode(
        "scroll",
        [LayoutNode("column", children=[
            LayoutNode("text", text=f"Row {index}", height=40)
            for index in range(30)
        ])],
        scroll_axis="vertical",
    )
    runtime = NativeRuntime(lambda: scroll, RecordingRenderer(), 400, 800)
    runtime.start()
    try:
        assert scroll.max_scroll_y > 0
        scroll.scroll_y = scroll.max_scroll_y

        runtime.resize(400, 160)
        assert scroll.scroll_y <= scroll.max_scroll_y
        assert scroll.max_scroll_y > 0

        runtime.resize(400, 1600)
        assert scroll.max_scroll_y == 0
        assert scroll.scroll_y == 0
    finally:
        runtime.stop()
