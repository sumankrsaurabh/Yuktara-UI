"""Interactive responsive-layout gallery for Yuktara UI.

Resize the native window from phone-width to desktop-width to see the
composition switch between stacked, two-column and three-column layouts.
"""

from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import (
    Card,
    Grid,
    GridItem,
    Label,
    NativeRuntime,
    NativeTheme,
    RenderSize,
    Responsive,
    ResponsiveVariant,
    SkiaRenderer,
    column,
    row,
)
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame


def main() -> None:
    theme = NativeTheme()
    compact = column(
        Card((Label("Overview"), Label("A compact, vertically stacked layout.")), theme=theme),
        Card((Label("Activity"), Label("Content remains readable in a narrow window.")), theme=theme),
        Card((Label("Details"), Label("Resize wider to reveal the other arrangements.")), theme=theme),
        spacing=12,
    )
    medium = row(
        column(
            Card((Label("Overview"), Label("Two-column composition.")), theme=theme),
            Card((Label("Activity"), Label("The main content stays on the left.")), theme=theme),
            spacing=12,
        ),
        Card((Label("Details"), Label("Secondary information moves beside the main content.")), theme=theme),
        spacing=12,
        wrap=True,
    )
    expanded = Grid(
        [
            GridItem(Card((Label("Overview"), Label("Expanded desktop layout.")), theme=theme)),
            GridItem(Card((Label("Activity"), Label("Three equal responsive tracks.")), theme=theme)),
            GridItem(Card((Label("Details"), Label("All panels are visible together.")), theme=theme)),
        ],
        columns=3,
        min_column_width=240,
        column_gap=14,
        row_gap=14,
    )
    responsive = Responsive(
        variants=(
            ResponsiveVariant(0, compact),
            ResponsiveVariant(640, medium),
            ResponsiveVariant(1024, expanded),
        )
    )
    root = column(
        Label("Yuktara UI — Responsive Layout", size=26, weight="bold", theme=theme),
        Label(
            "Resize this window. Layout breakpoints are measured in device-independent UI units.",
            color=theme.muted,
            theme=theme,
        ),
        responsive,
        spacing=16,
        padding=20,
        background=theme.background,
    )
    renderer = SkiaRenderer(RenderSize(1024, 768), skia_module=skia)
    runtime = NativeRuntime(
        lambda: root,
        renderer,
        1024,
        768,
        clear_color=theme.background,
    )
    window = SDL3Window(
        "Yuktara UI — Responsive Layout",
        1024,
        768,
        high_dpi=True,
        min_width=320,
        min_height=240,
    )
    window.run_runtime(
        runtime,
        lambda _runtime: renderer_frame(renderer, skia_module=skia),
    )


if __name__ == "__main__":
    main()
