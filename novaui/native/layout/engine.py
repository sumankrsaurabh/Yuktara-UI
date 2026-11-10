"""Measure/arrange layout engine for Yuktara UI.

The engine works in logical pixels and is backend-neutral. It supports linear
and wrapped flex layouts, responsive equal-track grids, percentage dimensions,
per-node size constraints, baseline alignment, and absolute positioning.
"""
from __future__ import annotations

from math import inf, isfinite

from .geometry import Alignment, Constraints, MainAxisAlignment, Rect, Size
from .node import LayoutNode, LayoutResult


def _resolve_length(value, available: float) -> float | None:
    """Resolve a pixel or percentage length against a finite parent extent.

    Percentage values intentionally resolve to ``None`` when the parent extent
    is unbounded. In that case the child falls back to its intrinsic size rather
    than creating an infinite dimension.
    """
    if value is None:
        return None
    if isinstance(value, str):
        if not isfinite(available):
            return None
        return max(0.0, float(value.strip()[:-1].strip()) * available / 100.0)
    return float(value)


def _clamp(value: float, minimum: float | None, maximum: float | None) -> float:
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return max(0.0, value)


def _is_absolute(node: LayoutNode) -> bool:
    return node.position == "absolute"


class LayoutEngine:
    """Two-phase layout engine with row/column, flex-wrap and grid support.

    ``width``/``height`` and min/max constraints accept logical pixels or
    percentage strings such as ``"50%"``. Percentage values are relative to
    the corresponding finite parent constraint. Absolute-position offsets are
    relative to the parent's content box.
    """

    def __init__(self, text_measurer=None):
        self.text_measurer = text_measurer

    def measure(self, node: LayoutNode, constraints: Constraints = Constraints()) -> Size:
        resolved_width = _resolve_length(node.width, constraints.max_width)
        resolved_height = _resolve_length(node.height, constraints.max_height)
        max_width = min(constraints.max_width, resolved_width) if resolved_width is not None else constraints.max_width
        max_height = min(constraints.max_height, resolved_height) if resolved_height is not None else constraints.max_height

        pad = node.padding
        content_constraints = Constraints(
            0.0, max(0.0, max_width - pad.horizontal),
            0.0, max(0.0, max_height - pad.vertical),
        )
        node.first_baseline = None

        if node.kind == "text":
            content = self._measure_text(node, content_constraints, resolved_width, resolved_height)
        elif node.kind == "box":
            content = self._measure_box(node, content_constraints)
        elif node.kind in ("row", "column"):
            content = self._measure_linear(node, content_constraints)
        elif node.kind == "scroll":
            content = self._measure_scroll(node, content_constraints)
        elif node.kind == "grid":
            content = self._measure_grid(node, content_constraints)
        else:
            content = self._measure_stack(node, content_constraints)

        desired_width = resolved_width if resolved_width is not None else content.width + pad.horizontal
        desired_height = resolved_height if resolved_height is not None else content.height + pad.vertical

        min_width = _resolve_length(node.min_width, constraints.max_width)
        max_width_limit = _resolve_length(node.max_width, constraints.max_width)
        min_height = _resolve_length(node.min_height, constraints.max_height)
        max_height_limit = _resolve_length(node.max_height, constraints.max_height)
        if min_width is not None and max_width_limit is not None and min_width > max_width_limit:
            raise ValueError("Resolved min_width cannot exceed max_width")
        if min_height is not None and max_height_limit is not None and min_height > max_height_limit:
            raise ValueError("Resolved min_height cannot exceed max_height")

        desired = Size(
            _clamp(desired_width, min_width, max_width_limit),
            _clamp(desired_height, min_height, max_height_limit),
        )
        node.measured_size = constraints.constrain(desired)
        if node.baseline is not None:
            node.first_baseline = min(node.measured_size.height, node.baseline)
        elif node.first_baseline is not None:
            node.first_baseline += pad.top
        elif node.kind != "text":
            node.first_baseline = node.measured_size.height
        return node.measured_size

    def _measure_text(self, node, constraints, resolved_width, resolved_height) -> Size:
        if self.text_measurer is None:
            content = node.intrinsic_size
        else:
            from ..typography import FontConfig
            config_for = getattr(self.text_measurer, "config_for", None)
            font_config = (
                config_for(node.font_family, node.font_size, node.font_weight)
                if callable(config_for) else
                FontConfig(family=node.font_family, size=node.font_size, weight=node.font_weight)
            )
            text_max_width = constraints.max_width
            if resolved_width is not None:
                text_max_width = min(text_max_width, max(0.0, resolved_width - node.padding.horizontal))
            layout = self.text_measurer.measure(
                node.text or "", font_config, max_width=text_max_width,
                wrap=node.text_wrap, line_height=node.text_line_height,
                max_lines=node.text_max_lines, style_spans=node.text_style_spans,
                paragraph_styles=node.text_paragraph_styles,
            )
            node.text_layout = layout
            content = Size(layout.width, layout.height)
            if layout.lines:
                node.first_baseline = layout.lines[0].baseline
            if node.text_clip and node.text_cursor is not None:
                caret_x, caret_y, _line = layout.caret_position(node.text_cursor)
                visible_width = max(0.0, (resolved_width if resolved_width is not None else constraints.max_width)
                                    - node.padding.horizontal)
                visible_height = max(0.0, (resolved_height if resolved_height is not None else constraints.max_height)
                                     - node.padding.vertical)
                if caret_x - node.text_scroll_x > visible_width - 3:
                    node.text_scroll_x = max(0.0, caret_x - visible_width + 3)
                elif caret_x < node.text_scroll_x:
                    node.text_scroll_x = caret_x
                if node.text_wrap:
                    if caret_y + layout.line_height - node.text_scroll_y > visible_height:
                        node.text_scroll_y = max(0.0, caret_y + layout.line_height - visible_height)
                    elif caret_y < node.text_scroll_y:
                        node.text_scroll_y = caret_y
        return content

    def _measure_child(self, child, constraints):
        if _is_absolute(child):
            return self._measure_absolute_child(child, constraints)
        return self.measure(child, constraints)

    def _measure_absolute_child(self, child, constraints):
        left = _resolve_length(child.left, constraints.max_width)
        right = _resolve_length(child.right, constraints.max_width)
        top = _resolve_length(child.top, constraints.max_height)
        bottom = _resolve_length(child.bottom, constraints.max_height)
        width = _resolve_length(child.width, constraints.max_width)
        height = _resolve_length(child.height, constraints.max_height)

        max_width = constraints.max_width
        max_height = constraints.max_height
        min_width = 0.0
        min_height = 0.0
        if width is None and left is not None and right is not None and isfinite(max_width):
            width = max(0.0, max_width - left - right)
        if height is None and top is not None and bottom is not None and isfinite(max_height):
            height = max(0.0, max_height - top - bottom)
        if child.width is None and left is not None and right is not None and isfinite(max_width):
            min_width = max_width = width
        if child.height is None and top is not None and bottom is not None and isfinite(max_height):
            min_height = max_height = height
        return self.measure(child, Constraints(min_width, max_width, min_height, max_height))

    def _measure_box(self, node, constraints):
        flow_children = [child for child in node.children if not _is_absolute(child)]
        for child in node.children:
            if _is_absolute(child):
                self._measure_absolute_child(child, constraints)
        if not flow_children:
            return node.intrinsic_size
        # Box is a single-child primitive. Additional children should use Stack.
        size = self.measure(flow_children[0], constraints)
        return Size(max(node.intrinsic_size.width, size.width),
                    max(node.intrinsic_size.height, size.height))

    def _measure_stack(self, node, constraints):
        sizes = []
        for child in node.children:
            if _is_absolute(child):
                self._measure_absolute_child(child, constraints)
            else:
                sizes.append(self.measure(child, constraints))
        return Size(
            max([node.intrinsic_size.width] + [size.width for size in sizes]),
            max([node.intrinsic_size.height] + [size.height for size in sizes]),
        )

    def _measure_scroll(self, node, constraints):
        if not node.children:
            node.content_size = Size()
            return node.intrinsic_size
        child = node.children[0]
        max_width = inf if node.scroll_axis in {"horizontal", "both"} else constraints.max_width
        max_height = inf if node.scroll_axis in {"vertical", "both"} else constraints.max_height
        child_size = self.measure(child, Constraints(0, max_width, 0, max_height))
        node.content_size = child_size
        return Size(min(child_size.width, constraints.max_width),
                    min(child_size.height, constraints.max_height))

    def _measure_linear(self, node, constraints):
        horizontal = node.kind == "row"
        main_max = constraints.max_width if horizontal else constraints.max_height
        cross_max = constraints.max_height if horizontal else constraints.max_width
        flow_children = [child for child in node.children if not _is_absolute(child)]
        for child in node.children:
            if _is_absolute(child):
                self._measure_absolute_child(child, constraints)

        node.flex_lines = []
        if not flow_children:
            return node.intrinsic_size

        def main_size(size):
            return size.width if horizontal else size.height

        def make_child_constraints(main_min=0.0, main_limit=main_max, *, tight=False):
            if horizontal:
                return Constraints(main_min if tight else 0.0, main_limit, 0.0, cross_max)
            return Constraints(0.0, cross_max, main_min if tight else 0.0, main_limit)

        # Establish flex bases before deciding which children fit on each line.
        base_sizes = []
        for child in flow_children:
            if child.weight > 0:
                basis_value = child.flex_basis
                if basis_value is None:
                    dimension = child.width if horizontal else child.height
                    basis_value = dimension if isinstance(dimension, (int, float)) else None
                basis = _resolve_length(basis_value, main_max) if basis_value is not None else 0.0
                basis = 0.0 if basis is None else basis
                size = self.measure(child, make_child_constraints(basis, basis, tight=True))
            else:
                size = self.measure(child, make_child_constraints())
            base_sizes.append(size)

        # Greedy, stable flex line construction. Oversized children occupy a
        # line by themselves rather than being silently dropped or reordered.
        lines: list[list[int]] = []
        current: list[int] = []
        current_main = 0.0
        for index, size in enumerate(base_sizes):
            item_main = main_size(size)
            proposed = item_main if not current else current_main + node.spacing + item_main
            if node.flex_wrap and isfinite(main_max) and current and proposed > main_max:
                lines.append(current)
                current = [index]
                current_main = item_main
            else:
                if current:
                    current_main += node.spacing
                current.append(index)
                current_main += item_main
        if current:
            lines.append(current)

        total_cross = 0.0
        max_line_main = 0.0
        for line_indices in lines:
            line_children = [flow_children[index] for index in line_indices]
            line_sizes = [base_sizes[index] for index in line_indices]
            gaps = node.spacing * max(0, len(line_children) - 1)
            used = sum(main_size(size) for size in line_sizes) + gaps
            weighted = [(i, child) for i, child in enumerate(line_children) if child.weight > 0]
            weight_sum = sum(child.weight for _, child in weighted)
            remaining = max(0.0, main_max - used) if isfinite(main_max) else 0.0
            if weighted and weight_sum > 0 and remaining > 0:
                for local_index, child in weighted:
                    allocation = main_size(line_sizes[local_index]) + remaining * child.weight / weight_sum
                    line_sizes[local_index] = self.measure(
                        child, make_child_constraints(allocation, allocation, tight=True)
                    )
            line_main = sum(main_size(size) for size in line_sizes) + gaps
            line_cross = max((size.height if horizontal else size.width for size in line_sizes), default=0.0)
            max_line_main = max(max_line_main, line_main)
            total_cross += line_cross
            node.flex_lines.append({
                "children": line_children,
                "sizes": line_sizes,
                "main": line_main,
                "cross": line_cross,
            })
        total_cross += node.wrap_spacing * max(0, len(node.flex_lines) - 1)
        if horizontal:
            return Size(max_line_main, total_cross)
        return Size(total_cross, max_line_main)

    def _grid_place(self, node, flow_children, columns):
        occupied: set[tuple[int, int]] = set()
        coordinates: dict[int, tuple[int, int]] = {}
        cursor = 0

        def fits(row, column, row_span, column_span):
            return all((r, c) not in occupied
                       for r in range(row, row + row_span)
                       for c in range(column, column + column_span))

        # Reserve every explicitly positioned cell first, so auto-placement
        # cannot accidentally occupy a cell that belongs to a later child.
        for index, child in enumerate(flow_children):
            if child.grid_row is None and child.grid_column is None:
                continue
            row = child.grid_row or 0
            column = child.grid_column or 0
            columns = max(columns, column + child.grid_column_span)
            if not fits(row, column, child.grid_row_span, child.grid_column_span):
                raise ValueError("Grid items cannot occupy overlapping explicit cells")
            coordinates[index] = (row, column)
            for r in range(row, row + child.grid_row_span):
                for c in range(column, column + child.grid_column_span):
                    occupied.add((r, c))

        for index, child in enumerate(flow_children):
            if index in coordinates:
                continue
            row_span = child.grid_row_span
            column_span = child.grid_column_span
            if column_span > columns:
                columns = column_span
            while True:
                row, column = divmod(cursor, columns)
                if column + column_span > columns:
                    cursor = (row + 1) * columns
                    continue
                if fits(row, column, row_span, column_span):
                    break
                cursor += 1
            coordinates[index] = (row, column)
            for r in range(row, row + row_span):
                for c in range(column, column + column_span):
                    occupied.add((r, c))
            cursor = row * columns + column + 1

        placements = []
        for index, child in enumerate(flow_children):
            row, column = coordinates[index]
            placements.append((child, row, column, child.grid_row_span, child.grid_column_span))
        return columns, placements

    def _measure_grid(self, node, constraints):
        flow_children = [child for child in node.children if not _is_absolute(child)]
        for child in node.children:
            if _is_absolute(child):
                self._measure_absolute_child(child, constraints)
        if not flow_children:
            node.grid_actual_columns = node.grid_columns
            node.grid_actual_rows = 0
            node.grid_placements = []
            node.grid_column_widths = [0.0] * node.grid_actual_columns
            node.grid_row_heights = []
            return node.intrinsic_size

        available_width = constraints.max_width
        columns = node.grid_columns
        min_width = node.grid_min_column_width
        if min_width is not None and isfinite(available_width):
            fit = max(1, int((available_width + node.grid_column_gap) //
                             (min_width + node.grid_column_gap)))
            columns = min(columns, fit)
        has_explicit_placement = any(
            child.grid_row is not None or child.grid_column is not None
            or child.grid_row_span > 1 or child.grid_column_span > 1
            for child in flow_children
        )
        if not has_explicit_placement:
            columns = max(1, min(columns, max(len(flow_children), 1)))
        else:
            required_columns = max(
                (child.grid_column or 0) + child.grid_column_span
                for child in flow_children if child.grid_column is not None
            ) if any(child.grid_column is not None for child in flow_children) else 1
            required_span = max((child.grid_column_span for child in flow_children), default=1)
            columns = max(columns, required_columns, required_span)
        columns, placements = self._grid_place(node, flow_children, columns)
        node.grid_actual_columns = columns
        node.grid_placements = placements
        rows = max((row + row_span for _child, row, _column, row_span, _span in placements), default=0)
        node.grid_actual_rows = rows

        finite_width = isfinite(available_width)
        if finite_width:
            track_widths = [max(0.0, (available_width - node.grid_column_gap * (columns - 1)) / columns)] * columns
        else:
            track_widths = [0.0] * columns

        measured_children = []
        for child, row, column, row_span, column_span in placements:
            span_width = (sum(track_widths[column:column + column_span])
                          + node.grid_column_gap * (column_span - 1)) if finite_width else inf
            measured = self.measure(child, Constraints(0.0, span_width, 0.0, constraints.max_height))
            measured_children.append((child, row, column, row_span, column_span, measured))
            if not finite_width:
                share = max(0.0, measured.width - node.grid_column_gap * (column_span - 1)) / column_span
                for index in range(column, column + column_span):
                    track_widths[index] = max(track_widths[index], share)

        row_heights = [0.0] * rows
        for child, row, column, row_span, column_span, measured in measured_children:
            if row_span == 1:
                row_heights[row] = max(row_heights[row], measured.height)
        # Multi-row items contribute their measured height across the spanned
        # tracks. Any deficit is distributed evenly and deterministically.
        for child, row, column, row_span, column_span, measured in measured_children:
            if row_span > 1:
                current = sum(row_heights[row:row + row_span]) + node.grid_row_gap * (row_span - 1)
                deficit = max(0.0, measured.height - current) / row_span
                if deficit:
                    for index in range(row, row + row_span):
                        row_heights[index] += deficit

        node.grid_column_widths = track_widths
        node.grid_row_heights = row_heights
        total_width = sum(track_widths) + node.grid_column_gap * (columns - 1)
        total_height = sum(row_heights) + node.grid_row_gap * max(0, rows - 1)
        if finite_width:
            total_width = available_width
        return Size(total_width, total_height)

    def arrange(self, node: LayoutNode, bounds: Rect) -> LayoutResult:
        node.bounds = bounds
        content = bounds.inset(node.padding)
        node.content_bounds = content

        if node.kind == "box":
            flow = [child for child in node.children if not _is_absolute(child)]
            if flow:
                self._arrange_aligned(flow[0], content, node.align)
            self._arrange_absolute_children(node, content)
        elif node.kind == "stack":
            for child in node.children:
                if not _is_absolute(child):
                    self._arrange_aligned(child, content, node.align)
            self._arrange_absolute_children(node, content)
        elif node.kind == "scroll":
            node.max_scroll_x = max(0.0, node.content_size.width - content.width) if node.scroll_axis in {"horizontal", "both"} else 0.0
            node.max_scroll_y = max(0.0, node.content_size.height - content.height) if node.scroll_axis in {"vertical", "both"} else 0.0
            node.scroll_x = min(node.scroll_x, node.max_scroll_x)
            node.scroll_y = min(node.scroll_y, node.max_scroll_y)
            if node.children:
                child = node.children[0]
                child_width = max(content.width, node.content_size.width)
                child_height = max(content.height, node.content_size.height)
                self.arrange(child, Rect(content.x - node.scroll_x, content.y - node.scroll_y,
                                         child_width, child_height))
        elif node.kind in ("row", "column"):
            self._arrange_linear(node, content)
            self._arrange_absolute_children(node, content)
        elif node.kind == "grid":
            self._arrange_grid(node, content)
            self._arrange_absolute_children(node, content)
        return LayoutResult(node.measured_size, bounds)

    def _child_limits(self, child, area):
        min_width = _resolve_length(child.min_width, area.width)
        max_width = _resolve_length(child.max_width, area.width)
        min_height = _resolve_length(child.min_height, area.height)
        max_height = _resolve_length(child.max_height, area.height)
        return min_width, max_width, min_height, max_height

    def _arrange_aligned(self, child, area, align):
        size = child.measured_size
        align = child.align_self or align
        min_width, max_width, min_height, max_height = self._child_limits(child, area)
        if align == Alignment.STRETCH:
            width = _clamp(area.width, min_width, max_width)
            height = _clamp(area.height, min_height, max_height)
        else:
            width = _clamp(min(size.width, area.width), min_width, max_width)
            height = _clamp(min(size.height, area.height), min_height, max_height)
        x = area.x if align in (Alignment.START, Alignment.STRETCH, Alignment.BASELINE) else (
            area.x + (area.width - width) / 2 if align == Alignment.CENTER else area.right - width
        )
        y = area.y if align in (Alignment.START, Alignment.STRETCH, Alignment.BASELINE) else (
            area.y + (area.height - height) / 2 if align == Alignment.CENTER else area.bottom - height
        )
        self.arrange(child, Rect(x, y, width, height))

    def _arrange_absolute_children(self, parent, area):
        for child in parent.children:
            if not _is_absolute(child):
                continue
            left = _resolve_length(child.left, area.width)
            right = _resolve_length(child.right, area.width)
            top = _resolve_length(child.top, area.height)
            bottom = _resolve_length(child.bottom, area.height)
            width = child.measured_size.width
            height = child.measured_size.height
            if child.width is None and left is not None and right is not None:
                width = max(0.0, area.width - left - right)
            if child.height is None and top is not None and bottom is not None:
                height = max(0.0, area.height - top - bottom)
            x = area.x + left if left is not None else (area.right - right - width if right is not None else area.x)
            y = area.y + top if top is not None else (area.bottom - bottom - height if bottom is not None else area.y)
            min_width, max_width, min_height, max_height = self._child_limits(child, area)
            width = _clamp(width, min_width, max_width)
            height = _clamp(height, min_height, max_height)
            self.arrange(child, Rect(x, y, width, height))

    def _line_main_alignment(self, area, used, count, main_align):
        extra = max(0.0, area - used)
        if main_align == MainAxisAlignment.CENTER:
            return extra / 2, 0.0
        if main_align == MainAxisAlignment.END:
            return extra, 0.0
        if main_align == MainAxisAlignment.SPACE_BETWEEN and count > 1:
            return 0.0, extra / (count - 1)
        if main_align == MainAxisAlignment.SPACE_AROUND and count:
            gap = extra / count
            return gap / 2, gap
        if main_align == MainAxisAlignment.SPACE_EVENLY:
            gap = extra / (count + 1)
            return gap, gap
        return 0.0, 0.0

    def _arrange_linear(self, node, area):
        horizontal = node.kind == "row"
        lines = node.flex_lines
        if not lines:
            return
        cross_total = sum(line["cross"] for line in lines) + node.wrap_spacing * max(0, len(lines) - 1)
        cross_extent = area.height if horizontal else area.width
        cross_extra = max(0.0, cross_extent - cross_total)
        if not node.flex_wrap:
            cross_cursor = area.y if horizontal else area.x
            line_gap = 0.0
            stretch_extra = 0.0
        elif node.align_content == Alignment.CENTER:
            cross_cursor = (area.y if horizontal else area.x) + cross_extra / 2
            line_gap = node.wrap_spacing
            stretch_extra = 0.0
        elif node.align_content == Alignment.END:
            cross_cursor = (area.bottom - cross_total if horizontal else area.right - cross_total)
            line_gap = node.wrap_spacing
            stretch_extra = 0.0
        else:
            cross_cursor = area.y if horizontal else area.x
            line_gap = node.wrap_spacing
            stretch_extra = (cross_extra / len(lines)
                             if node.align_content == Alignment.STRETCH and lines else 0.0)
        for line in lines:
            children = line["children"]
            sizes = line["sizes"]
            # A non-wrapping row/column has one cross-axis line spanning the
            # full available cross extent, preserving the original stretch
            # behavior. Wrapped layouts use each measured line's own extent.
            line_cross = (cross_extent if not node.flex_wrap else line["cross"] + stretch_extra)
            main_extent = area.width if horizontal else area.height
            main_offset, justified_gap = self._line_main_alignment(
                main_extent, line["main"], len(children), node.main_align
            )
            base_gap = node.spacing + justified_gap
            main_cursor = (area.x if horizontal else area.y) + main_offset

            line_baseline = 0.0
            if horizontal and any(
                (child.align_self or node.cross_align) == Alignment.BASELINE
                for child in children
            ):
                line_baseline = max(
                    (child.first_baseline if child.first_baseline is not None else size.height)
                    for child, size in zip(children, sizes)
                    if (child.align_self or node.cross_align) == Alignment.BASELINE
                )

            for child, size in zip(children, sizes):
                child_main = size.width if horizontal else size.height
                child_cross = size.height if horizontal else size.width
                align = child.align_self or node.cross_align
                min_width, max_width, min_height, max_height = self._child_limits(
                    child, Rect(area.x, cross_cursor, area.width, line_cross) if horizontal
                    else Rect(cross_cursor, area.y, line_cross, area.height)
                )
                if align == Alignment.STRETCH:
                    child_cross = _clamp(line_cross,
                                         min_height if horizontal else min_width,
                                         max_height if horizontal else max_width)
                else:
                    child_cross = min(child_cross, line_cross)
                    child_cross = _clamp(child_cross,
                                         min_height if horizontal else min_width,
                                         max_height if horizontal else max_width)

                if horizontal:
                    if align == Alignment.BASELINE:
                        baseline = child.first_baseline if child.first_baseline is not None else size.height
                        cross_pos = cross_cursor + line_baseline - baseline
                    elif align in (Alignment.START, Alignment.STRETCH):
                        cross_pos = cross_cursor
                    elif align == Alignment.CENTER:
                        cross_pos = cross_cursor + (line_cross - child_cross) / 2
                    else:
                        cross_pos = cross_cursor + line_cross - child_cross
                    child_rect = Rect(main_cursor, cross_pos, child_main, child_cross)
                else:
                    if align in (Alignment.START, Alignment.STRETCH, Alignment.BASELINE):
                        cross_pos = cross_cursor
                    elif align == Alignment.CENTER:
                        cross_pos = cross_cursor + (line_cross - child_cross) / 2
                    else:
                        cross_pos = cross_cursor + line_cross - child_cross
                    child_rect = Rect(cross_pos, main_cursor, child_cross, child_main)
                self.arrange(child, child_rect)
                main_cursor += child_main + base_gap
            cross_cursor += line_cross + line_gap

    def _arrange_grid(self, node, area):
        if not node.grid_placements:
            return
        columns = max(1, node.grid_actual_columns)
        column_widths = node.grid_column_widths
        row_heights = node.grid_row_heights
        column_positions = [area.x]
        for index in range(1, columns):
            column_positions.append(column_positions[-1] + column_widths[index - 1] + node.grid_column_gap)
        row_positions = [area.y]
        for index in range(1, len(row_heights)):
            row_positions.append(row_positions[-1] + row_heights[index - 1] + node.grid_row_gap)

        for child, row, column, row_span, column_span in node.grid_placements:
            width = sum(column_widths[column:column + column_span]) + node.grid_column_gap * (column_span - 1)
            height = sum(row_heights[row:row + row_span]) + node.grid_row_gap * (row_span - 1)
            cell = Rect(column_positions[column], row_positions[row], width, height)
            self._arrange_aligned(child, cell, node.cross_align)

    def layout(self, root: LayoutNode, bounds: Rect) -> LayoutResult:
        self.measure(root, Constraints(bounds.width, bounds.width, bounds.height, bounds.height))
        return self.arrange(root, bounds)


def hit_test(root: LayoutNode, x: float, y: float) -> LayoutNode | None:
    """Return the deepest topmost node, respecting scroll viewport clips."""
    from .geometry import Point
    point = Point(x, y)

    def visit(node, clip=None):
        if clip is not None and not clip.contains(point):
            return None
        if node.kind == "scroll":
            viewport = node.content_bounds
            if not viewport.contains(point):
                return node if node.bounds.contains(point) else None
            child_clip = viewport if clip is None else _intersect(clip, viewport)
        else:
            child_clip = clip
        for child in reversed(node.children):
            hit = visit(child, child_clip)
            if hit is not None:
                return hit
        return node if node.bounds.contains(point) else None

    return visit(root)


def _intersect(a: Rect, b: Rect) -> Rect:
    left = max(a.x, b.x)
    top = max(a.y, b.y)
    right = min(a.right, b.right)
    bottom = min(a.bottom, b.bottom)
    return Rect(left, top, max(0.0, right - left), max(0.0, bottom - top))
