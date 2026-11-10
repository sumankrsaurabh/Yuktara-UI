"""Backend-neutral demo of Yuktara UI's 3.3 layout features.

Run with ``python examples/native/advanced_layout.py``. This example only
computes logical bounds; it does not require SDL3 or Skia.
"""
from novaui.native import (
    Alignment, Container, Grid, GridItem, Label, LayoutEngine,
    Positioned, Rect, column, row, stack,
)


def main() -> None:
    wrapped_tags = row(
        Label("Native"), Label("Responsive"), Label("Flex wrap"),
        Label("Baseline"),
        wrap=True, spacing=8, wrap_spacing=10,
        cross_align=Alignment.CENTER,
    )

    responsive_container = Container(
        child=Label("This container is 90% of the available width."),
        width="90%", min_width=260, max_width=900, padding=14,
    ).build()

    dashboard_grid = Grid(
        [
            GridItem(Container(child=Label("Wide summary"), padding=12),
                     row=0, column=0, column_span=2),
            GridItem(Container(child=Label("Activity"), padding=12),
                     row=0, column=2),
            Container(child=Label("Auto-placed card"), padding=12),
        ],
        columns=3, column_gap=12, row_gap=12,
    ).build()

    content = column(
        Label("Yuktara UI 3.3 — Advanced layout", size=24, weight="bold"),
        responsive_container,
        wrapped_tags,
        dashboard_grid,
        spacing=16, padding=20,
    )
    floating_badge = Positioned(
        Label("NEW"), right=12, top=12, width=64, height=26,
    ).build()
    root = stack(content, floating_badge)
    root.width = 960
    root.height = 640

    LayoutEngine().layout(root, Rect(0, 0, 960, 640))
    print("Root:", root.bounds)
    print("Responsive container:", responsive_container.bounds)
    print("Grid columns:", dashboard_grid.grid_actual_columns)
    print("Floating badge:", floating_badge.bounds)
    print("Computed layout successfully (no SDL3/Skia required).")


if __name__ == "__main__":
    main()
