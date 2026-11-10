"""Gallery for Yuktara UI's general-purpose native controls.

Run ``python examples/native/advanced_component_gallery.py`` after
``python -m novaui setup``. Pass ``--image PATH`` to preview a local image.
"""
from __future__ import annotations

import argparse
from datetime import date

from novaui.native.dependencies import ensure_skia_python


def main() -> None:
    parser = argparse.ArgumentParser(description="Yuktara UI advanced component gallery")
    parser.add_argument("--image", help="Optional local image path to preview")
    args = parser.parse_args()

    ensure_skia_python()
    import skia

    from novaui.native import (
        Badge, Button, Calendar, Card, Container, DatePicker, FilePicker,
        Grid, Image, Label, NavigationDrawer, NavigationItem, NativeRuntime,
        NativeTheme, Responsive, ResponsiveVariant, ScrollView, Table,
        TreeItem, TreeView, column, row,
    )
    from novaui.native.platform import SDL3Window
    from novaui.native.platform.skia_bridge import renderer_frame
    from novaui.native.renderer import RenderSize, SkiaRenderer

    theme = NativeTheme()
    window = SDL3Window("Yuktara UI — Advanced Component Gallery", 1160, 820)
    date_label = Label("No date selected", color=theme.muted, size=12)
    file_label = Label("No file selected", color=theme.muted, size=12)

    navigation_items = [
        NavigationItem("Overview", icon="⌂", key="overview"),
        NavigationItem("Components", icon="▦", key="components"),
        NavigationItem("Documents", icon="▤", badge="3", key="documents"),
        NavigationItem("Settings", icon="⚙", key="settings"),
    ]
    navigation = NavigationDrawer(
        navigation_items, selected="overview", width=210, theme=theme,
    )
    compact_navigation = NavigationDrawer(
        navigation_items, selected="overview", width=72, compact=True, theme=theme,
    )

    summary_cards = Grid(
        [
            Card((Label("Components", size=12, color=theme.muted, theme=theme),
                  Label("32+", size=25, weight="bold", theme=theme),
                  Badge("Native controls", "success", theme)), theme=theme),
            Card((Label("Rendering", size=12, color=theme.muted, theme=theme),
                  Label("SDL3 + Skia", size=18, weight="bold", theme=theme),
                  Badge("No browser", "primary", theme)), theme=theme),
            Card((Label("Release", size=12, color=theme.muted, theme=theme),
                  Label("3.1 dev", size=25, weight="bold", theme=theme),
                  Badge("Experimental", "warning", theme)), theme=theme),
        ],
        columns=3, min_column_width=175, column_gap=12, row_gap=12,
    )

    table = Table(
        headers=("Component", "Category", "Status"),
        rows=(
            ("Grid", "Layout", "Ready"),
            ("Image", "Visual", "Ready"),
            ("NavigationDrawer", "Navigation", "Ready"),
            ("DatePicker", "Input", "Ready"),
        ),
        column_widths=(1.5, 1.0, 0.8), theme=theme,
    )

    def on_date(value: date) -> None:
        date_label.text = f"Selected: {value.isoformat()}"

    def on_files(paths: tuple[str, ...]) -> None:
        file_label.text = "Selected: " + ", ".join(paths)

    image_content = (
        Image(args.image, width=280, height=150, fit="cover",
              alt="User supplied preview image", radius=theme.radius_medium)
        if args.image else
        Container(
            child=column(
                Label("Image component", weight="semibold", theme=theme),
                Label("Run this gallery with --image PATH to preview a file.",
                      size=12, color=theme.muted, theme=theme),
                spacing=6,
            ),
            width=280, height=150, padding=14,
            background=theme.surface_variant, radius=theme.radius_medium,
        )
    )

    content = ScrollView(
        column(
            Label("General-purpose components", size=25, weight="bold", theme=theme),
            Label("Native layout, navigation, data and system controls", size=13,
                  color=theme.muted, theme=theme),
            summary_cards,
            row(
                Card((Label("Responsive grid", size=17, weight="semibold", theme=theme),
                      Label("Columns adapt to available width.", size=12,
                            color=theme.muted, theme=theme),
                      Grid([Badge(f"Cell {index}", "neutral", theme) for index in range(1, 7)],
                           columns=3, min_column_width=90, column_gap=8, row_gap=8)),
                     theme=theme),
                Card((Label("Image and container", size=17, weight="semibold", theme=theme),
                      image_content), theme=theme),
                spacing=12,
            ),
            Card((Label("Native data table", size=17, weight="semibold", theme=theme),
                  table), theme=theme),
            row(
                Card((Label("Calendar", size=17, weight="semibold", theme=theme),
                      Calendar(value=date.today(), width=270, theme=theme)), theme=theme),
                Card((Label("Date picker", size=17, weight="semibold", theme=theme),
                      DatePicker(value=date.today(), on_change=on_date, width=270, theme=theme),
                      date_label), theme=theme),
                spacing=12,
            ),
            row(
                Card((Label("Tree view", size=17, weight="semibold", theme=theme),
                      TreeView([
                          TreeItem("Documents", key="docs", children=(
                              TreeItem("Reports", key="reports"),
                              TreeItem("Invoices", key="invoices"),
                          )),
                          TreeItem("Images", key="images", children=(
                              TreeItem("Screenshots", key="screens"),
                          )),
                          TreeItem("Archive", key="archive", disabled=True),
                      ], expanded=("docs",), width=270, theme=theme)), theme=theme),
                Card((Label("Native file dialogs", size=17, weight="semibold", theme=theme),
                      FilePicker(window, label="Open a file", filters=(
                          ("Documents", "pdf;docx;txt"),), on_change=on_files, theme=theme),
                      Button("Save file…", on_click=lambda _event=None: window.show_save_file_dialog(
                          lambda paths, _index: on_files(paths or ()),
                          filters=(("Text", "txt"),)), variant="outline", theme=theme),
                      file_label), theme=theme),
                spacing=12,
            ),
            Label("Yuktara UI 3.1.0.dev0 · experimental native framework",
                  size=11, color=theme.muted, theme=theme),
            spacing=14, padding=20,
        ),
        axis="vertical", width=900, height=780,
        accessibility_label="Advanced component gallery",
    )
    root = Responsive(
        variants=(
            ResponsiveVariant(
                0,
                column(
                    compact_navigation,
                    content,
                    spacing=8,
                    padding=8,
                    background=theme.background,
                ),
            ),
            ResponsiveVariant(
                640,
                row(
                    compact_navigation,
                    content,
                    spacing=10,
                    padding=10,
                    background=theme.background,
                ),
            ),
            ResponsiveVariant(
                1040,
                row(
                    navigation,
                    content,
                    spacing=14,
                    padding=16,
                    background=theme.background,
                ),
            ),
        )
    ).build()

    renderer = SkiaRenderer(RenderSize(1160, 820), skia_module=skia)
    runtime = NativeRuntime(lambda: root, renderer, 1160, 820,
                             clear_color=theme.background)
    window.run_runtime(
        runtime,
        lambda _runtime: renderer_frame(renderer, skia_module=skia),
    )


if __name__ == "__main__":
    main()
