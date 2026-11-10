import pytest

from novaui.native.layout import Alignment, Constraints, LayoutEngine, LayoutNode, Rect, Size, hit_test
from novaui.native.widgets.core import column, row


def box(width, height, **kwargs):
    return LayoutNode("box", width=width, height=height,
                      intrinsic_size=Size(width, height), **kwargs)


def test_percentage_dimensions_resolve_against_parent_content_box():
    child = LayoutNode("box", width="50%", height="25%", intrinsic_size=Size(10, 10))
    root = LayoutNode.box(child, width=400, height=200)
    LayoutEngine().layout(root, Rect(0, 0, 400, 200))
    assert child.bounds == Rect(0, 0, 200, 50)


def test_percentage_dimensions_fall_back_to_intrinsic_when_unbounded():
    node = LayoutNode("box", width="50%", height="50%", intrinsic_size=Size(72, 24))
    assert LayoutEngine().measure(node, Constraints()) == Size(72, 24)


def test_minimum_and_maximum_constraints_clamp_intrinsic_size():
    node = LayoutNode("box", intrinsic_size=Size(200, 10),
                      min_width=80, max_width=120, min_height=30, max_height=50)
    assert LayoutEngine().measure(node, Constraints(0, 400, 0, 100)) == Size(120, 30)


def test_percentage_minimum_and_maximum_constraints():
    node = LayoutNode("box", intrinsic_size=Size(100, 10),
                      min_width="50%", max_width="75%")
    assert LayoutEngine().measure(node, Constraints(0, 400, 0, 100)).width == 200
    node.intrinsic_size = Size(390, 10)
    assert LayoutEngine().measure(node, Constraints(0, 400, 0, 100)).width == 300


def test_minimum_cannot_exceed_maximum_after_percentage_resolution():
    node = LayoutNode("box", min_width="80%", max_width="50%")
    with pytest.raises(ValueError, match="Resolved min_width"):
        LayoutEngine().measure(node, Constraints(0, 300, 0, 100))


def test_flex_row_wraps_children_and_adds_cross_axis_gap():
    children = [box(60, 10) for _ in range(3)]
    root = row(*children, spacing=10, wrap=True, wrap_spacing=5,
               cross_align=Alignment.START)
    LayoutEngine().layout(root, Rect(0, 0, 130, 100))
    assert children[0].bounds == Rect(0, 0, 60, 10)
    assert children[1].bounds == Rect(70, 0, 60, 10)
    assert children[2].bounds == Rect(0, 15, 60, 10)


def test_flex_wrap_keeps_oversized_child_on_own_line():
    children = [box(70, 10), box(180, 20), box(70, 10)]
    root = row(*children, spacing=5, wrap=True, wrap_spacing=4,
               cross_align=Alignment.START)
    LayoutEngine().layout(root, Rect(0, 0, 150, 100))
    assert children[0].bounds.y == 0
    assert children[1].bounds.y == 14
    assert children[2].bounds.y == 38


def test_weighted_children_expand_within_their_wrapped_line():
    fixed = box(80, 10)
    flexible = LayoutNode("box", weight=1, intrinsic_size=Size(0, 10))
    second_line = box(80, 10)
    root = row(fixed, flexible, second_line, wrap=True, spacing=0,
               wrap_spacing=5, cross_align=Alignment.START)
    LayoutEngine().layout(root, Rect(0, 0, 150, 100))
    assert fixed.bounds.width == 80
    assert flexible.bounds.width == 70
    assert second_line.bounds.y == 15


def test_column_wraps_into_additional_columns():
    children = [box(20, 40) for _ in range(3)]
    root = column(*children, spacing=5, wrap=True, wrap_spacing=8,
                  cross_align=Alignment.START)
    LayoutEngine().layout(root, Rect(0, 0, 100, 90))
    assert children[0].bounds == Rect(0, 0, 20, 40)
    assert children[1].bounds == Rect(0, 45, 20, 40)
    assert children[2].bounds == Rect(28, 0, 20, 40)


def test_default_non_wrapping_stretch_behavior_is_preserved():
    child = box(40, 10)
    root = column(child)
    LayoutEngine().layout(root, Rect(0, 0, 100, 80))
    assert child.bounds == Rect(0, 0, 100, 10)


def test_baseline_alignment_uses_each_child_baseline():
    first = box(30, 20, baseline=12)
    second = box(30, 30, baseline=20)
    root = row(first, second, cross_align=Alignment.BASELINE)
    LayoutEngine().layout(root, Rect(0, 0, 100, 60))
    assert first.bounds.y == 8
    assert second.bounds.y == 0
    assert first.bounds.y + first.first_baseline == second.bounds.y + second.first_baseline


def test_absolute_child_does_not_change_intrinsic_flow_size():
    flow = box(50, 40)
    overlay = box(20, 10, position="absolute", right=5, bottom=6)
    root = LayoutNode.stack(flow, overlay)
    assert LayoutEngine().measure(root, Constraints(0, 500, 0, 500)) == Size(50, 40)
    LayoutEngine().layout(root, Rect(0, 0, 200, 100))
    assert overlay.bounds == Rect(175, 84, 20, 10)


def test_absolute_child_can_stretch_between_opposing_edges():
    overlay = LayoutNode("box", position="absolute", left=10, right=20,
                        top=5, bottom=15, intrinsic_size=Size(5, 5))
    root = LayoutNode.stack(overlay)
    LayoutEngine().layout(root, Rect(0, 0, 200, 100))
    assert overlay.bounds == Rect(10, 5, 170, 80)


def test_percentage_absolute_offsets_and_size():
    overlay = LayoutNode("box", position="absolute", left="10%", top="20%",
                        width="25%", height="50%", intrinsic_size=Size(1, 1))
    root = LayoutNode.stack(overlay)
    LayoutEngine().layout(root, Rect(0, 0, 400, 200))
    assert overlay.bounds == Rect(40, 40, 100, 100)


def test_absolute_children_are_hit_tested_above_flow_siblings():
    flow = box(100, 100)
    overlay = box(20, 20, position="absolute", left=10, top=10)
    root = LayoutNode.stack(flow, overlay)
    LayoutEngine().layout(root, Rect(0, 0, 100, 100))
    assert hit_test(root, 15, 15) is overlay


def test_grid_column_span_occupies_multiple_tracks():
    wide = box(10, 20, grid_row=0, grid_column=0, grid_column_span=2)
    right = box(10, 10, grid_row=0, grid_column=2)
    bottom = box(10, 12)
    grid = LayoutNode("grid", [wide, right, bottom], grid_columns=3,
                     grid_column_gap=5, grid_row_gap=4)
    LayoutEngine().layout(grid, Rect(0, 0, 300, 100))
    assert wide.bounds.x == 0
    assert wide.bounds.y == 0
    assert wide.bounds.width == pytest.approx(198.3333333333)
    assert wide.bounds.height == 20
    assert right.bounds.x == pytest.approx(203.3333333333)
    assert bottom.bounds.y == 24


def test_grid_row_span_distributes_required_height_across_rows():
    tall = box(10, 60, grid_row=0, grid_column=0, grid_row_span=2)
    first = box(10, 20, grid_row=0, grid_column=1)
    second = box(10, 30, grid_row=1, grid_column=1)
    grid = LayoutNode("grid", [tall, first, second], grid_columns=2, grid_row_gap=4)
    LayoutEngine().layout(grid, Rect(0, 0, 200, 100))
    assert tall.bounds.height == pytest.approx(60)
    assert first.bounds.height == pytest.approx(23)
    assert second.bounds.y == pytest.approx(27)
    assert second.bounds.height == pytest.approx(33)


def test_grid_auto_placement_skips_cells_used_by_spanning_items():
    span = box(1, 10, grid_row=0, grid_column=0, grid_column_span=2)
    next_auto = box(1, 10)
    grid = LayoutNode("grid", [span, next_auto], grid_columns=3)
    LayoutEngine().layout(grid, Rect(0, 0, 300, 100))
    assert next_auto.bounds.x == pytest.approx(205.3333333333)
    assert next_auto.bounds.y == 0


def test_grid_rejects_overlapping_explicit_cells():
    first = box(1, 10, grid_row=0, grid_column=0, grid_column_span=2)
    second = box(1, 10, grid_row=0, grid_column=1)
    grid = LayoutNode("grid", [first, second], grid_columns=2)
    with pytest.raises(ValueError, match="overlapping"):
        LayoutEngine().measure(grid, Constraints(0, 200, 0, 100))


def test_layout_node_rejects_invalid_position_and_grid_spans():
    with pytest.raises(ValueError, match="position"):
        LayoutNode("box", position="sticky")
    with pytest.raises(ValueError, match="spans"):
        LayoutNode("box", grid_column_span=0)
    with pytest.raises(ValueError, match="percentage"):
        LayoutNode("box", width="wide%")


def test_grid_widget_exposes_grid_item_spans_and_explicit_positions():
    from novaui.native import Grid, GridItem, Label

    grid = Grid(
        [GridItem(Label("Wide"), row=0, column=0, column_span=2),
         GridItem(Label("Right"), row=0, column=2),
         Label("Next")],
        columns=3, column_gap=6,
    ).build()
    LayoutEngine().layout(grid, Rect(0, 0, 300, 100))
    assert grid.children[0].bounds.width > grid.children[1].bounds.width
    assert grid.children[1].bounds.x > grid.children[0].bounds.x
    assert grid.children[2].bounds.y > grid.children[0].bounds.y


def test_positioned_widget_is_excluded_from_parent_flow():
    from novaui.native import Label, Positioned

    content = box(80, 60)
    floating = Positioned(Label("Overlay"), right=8, bottom=6,
                          width=60, height=20).build()
    root = LayoutNode.stack(content, floating)
    assert LayoutEngine().measure(root, Constraints(0, 400, 0, 300)) == Size(80, 60)
    LayoutEngine().layout(root, Rect(0, 0, 200, 100))
    assert floating.bounds == Rect(132, 74, 60, 20)


def test_container_accepts_percentage_size_and_min_max_constraints():
    from novaui.native import Container, Label

    container = Container(
        child=Label("Responsive"), width="75%", height="50%",
        min_width=120, max_width=240,
    ).build()
    root = LayoutNode.box(container, width=300, height=200, align=Alignment.START)
    LayoutEngine().layout(root, Rect(0, 0, 300, 200))
    assert container.measured_size.width == pytest.approx(225)
    assert container.measured_size.height == pytest.approx(100)


def test_row_helper_accepts_flex_wrap_alias():
    children = [box(70, 10), box(70, 10)]
    root = row(*children, flex_wrap=True, spacing=5, cross_align=Alignment.START)
    LayoutEngine().layout(root, Rect(0, 0, 100, 100))
    assert children[1].bounds.y == 10


def test_grid_auto_placement_reserves_explicit_cells_that_appear_later():
    auto_first = box(1, 10)
    explicit_later = box(1, 10, grid_row=0, grid_column=0)
    grid = LayoutNode("grid", [auto_first, explicit_later], grid_columns=3)
    LayoutEngine().layout(grid, Rect(0, 0, 300, 100))
    assert auto_first.bounds.x > explicit_later.bounds.x
    assert auto_first.bounds.y == explicit_later.bounds.y
