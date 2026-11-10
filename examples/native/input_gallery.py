"""Interactive gallery for Yuktara UI's native input components."""
from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import (
    Alignment,
    Badge, Card, Dropdown, Label, NativeRuntime, NativeTheme, SegmentedControl,
    Slider, TabItem, Tabs, TextArea, TextField, column, row,
)
from novaui.native.platform import EventType, SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame
from novaui.native.renderer import RenderSize, SkiaRenderer


def main():
    theme = NativeTheme()
    name = TextField(placeholder="Your name", width=300)
    notes = TextArea("Write a few lines...", width=420, height=112)
    period = Dropdown(("Daily", "Weekly", "Monthly"), value="Weekly", width=240)
    zoom = Slider(value=70, minimum=0, maximum=100, step=5, label="Zoom", width=320)
    density = SegmentedControl(("Compact", "Comfortable", "Spacious"), value="Comfortable")
    tabs = Tabs((
        TabItem("Overview", Label("Overview panel content", theme=theme)),
        TabItem("Settings", Label("Settings panel content", theme=theme)),
        TabItem("About", Label("Yuktara UI native component library", theme=theme)),
    ), theme=theme)

    root = column(
        row(
            column(
                Label("Yuktara UI", size=28, weight="bold", theme=theme),
                Label("Native inputs and navigation", color=theme.muted, theme=theme),
            ),
            Badge("2.5 development", "primary", theme),
            spacing=18,
            cross_align=Alignment.CENTER,
        ),
        Card((
            Label("Text input", size=18, weight="semibold", theme=theme),
            name,
            Label("Multiline editor", size=13, color=theme.muted, theme=theme),
            notes,
            Label("Profile name: " + name.value, color=theme.muted, size=12, theme=theme),
        ), theme=theme),
        row(
            Card((
                Label("Dropdown", size=17, weight="semibold", theme=theme),
                period,
                Label("Choose a reporting interval", color=theme.muted, size=12, theme=theme),
            ), theme=theme),
            Card((
                Label("Slider", size=17, weight="semibold", theme=theme),
                zoom,
                Label("Zoom level is adjusted with arrows or drag", color=theme.muted, size=12, theme=theme),
            ), theme=theme),
            spacing=14,
        ),
        Card((
            Label("Segmented control", size=17, weight="semibold", theme=theme),
            density,
            Label("Tabs", size=17, weight="semibold", theme=theme),
            tabs,
        ), theme=theme),
        spacing=14,
        padding=22,
        background=theme.background,
    )

    renderer = SkiaRenderer(RenderSize(1000, 820), skia_module=skia)
    runtime = NativeRuntime(lambda: root, renderer, 1000, 820, clear_color=theme.background)
    window = SDL3Window("Yuktara UI — Input Components", 1000, 820)
    window.open()
    runtime.start()
    running = True
    try:
        while running:
            for event in window.poll_input_events():
                if event.type is EventType.QUIT:
                    running = False
                    break
                runtime.dispatch(event)
            if running:
                runtime.render()
                window.present(renderer_frame(renderer, skia_module=skia))
    finally:
        runtime.stop()
        window.close()


if __name__ == "__main__":
    main()
