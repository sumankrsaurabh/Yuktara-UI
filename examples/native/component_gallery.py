"""Interactive gallery for Yuktara UI's native built-in components."""
from novaui.native.dependencies import ensure_skia_python
ensure_skia_python()
import skia

from novaui.native import (
    Badge, Button, Card, Checkbox, Divider, Label, NativeRuntime, NativeTheme,
    ProgressBar, RadioGroup, Switch, column, row,
)
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame
from novaui.native.renderer import RenderSize, SkiaRenderer


def main():
    theme = NativeTheme()
    checkbox = Checkbox("Accept the terms", checked=True)
    notifications = Switch("Enable notifications", checked=True)
    density = RadioGroup(("Comfortable", "Compact", "Spacious"), value="Comfortable")
    counter = {"value": 0}

    def increment(_event=None):
        counter["value"] += 1
        status.text = f"Button clicks: {counter['value']}"

    status = Label("Button clicks: 0", color=theme.muted, size=13).build()
    content = column(
        Label("Yuktara UI", size=28, weight="bold", theme=theme),
        Label("Native component library", size=15, color=theme.muted, theme=theme),
        row(Badge("2.5 development", "primary", theme), Badge("SDL3 + Skia", "success", theme), spacing=8),
        Card((
            Label("Buttons", size=18, weight="semibold", theme=theme),
            row(
                Button("Primary", on_click=increment, variant="primary", theme=theme),
                Button("Secondary", variant="secondary", theme=theme),
                Button("Outline", variant="outline", theme=theme),
                Button("Disabled", disabled=True, theme=theme),
                spacing=8,
            ),
            row(
                Button("Danger", variant="danger", theme=theme),
                Button("Success", variant="success", theme=theme),
                Button("Ghost", variant="ghost", theme=theme),
                spacing=8,
            ),
            status,
        ), theme=theme),
        Card((
            Label("Inputs and status", size=18, weight="semibold", theme=theme),
            checkbox,
            notifications,
            Label("Density", weight="medium", theme=theme),
            density,
            Divider(color=theme.border),
            Label("Storage", size=13, color=theme.muted, theme=theme),
            ProgressBar(68, label="Storage used", theme=theme),
            Label("68% used", size=12, color=theme.muted, theme=theme),
        ), theme=theme),
        spacing=16, padding=24, background=theme.background,
    )

    renderer = SkiaRenderer(RenderSize(1000, 720), skia_module=skia)
    runtime = NativeRuntime(lambda: content, renderer, 1000, 720, clear_color=theme.background)
    window = SDL3Window("Yuktara UI — Component Gallery", 1000, 720)
    window.run_runtime(
        runtime,
        lambda _runtime: renderer_frame(renderer, skia_module=skia),
    )


if __name__ == "__main__":
    main()
