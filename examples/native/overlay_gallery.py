"""Interactive gallery for Yuktara UI's native overlay system."""
from __future__ import annotations

from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import (
    Badge, Button, Card, ContextMenu, Dialog, Label, MenuItem, NativeRuntime,
    NativeTheme, Popover, Toast, Tooltip, column, row,
)
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame
from novaui.native.renderer import RenderSize, SkiaRenderer


def main():
    theme = NativeTheme()
    runtime_ref = {"runtime": None}
    status = Label("Choose an overlay to preview", color=theme.muted, size=13).build()

    dialog_button = Button("Show dialog", theme=theme).build()
    popover_button = Button("Show popover", variant="secondary", theme=theme).build()
    tooltip_button = Button("Show tooltip", variant="secondary", theme=theme).build()
    menu_button = Button("Context menu", variant="secondary", theme=theme).build()
    toast_button = Button("Show toast", variant="success", theme=theme).build()

    def get_runtime():
        return runtime_ref["runtime"]

    def show_dialog(_event=None):
        runtime = get_runtime()
        runtime.overlays.show_dialog(Dialog(
            "Native dialog",
            "This modal surface is painted above the app tree.\nEscape or the scrim dismisses it.",
            actions=(Button("Cancel", variant="secondary", on_click=lambda _e: runtime.overlays.dismiss(), theme=theme),
                     Button("Done", on_click=lambda _e: runtime.overlays.dismiss(), theme=theme)),
            theme=theme,
        ))

    def show_popover(_event=None):
        runtime = get_runtime()
        runtime.overlays.show_popover(
            Popover((Label("Anchored popover", weight="semibold", theme=theme),
                     Label("Placement flips when the preferred edge has no room.", size=12,
                           color=theme.muted, theme=theme)), theme=theme),
            anchor=popover_button,
            placement="bottom",
        )

    def show_tooltip(_event=None):
        get_runtime().overlays.show_tooltip(
            Tooltip("Tooltips are pointer-transparent", theme=theme),
            anchor=tooltip_button,
        )

    def show_menu(event=None):
        pointer = getattr(event, "pointer", None)
        if pointer is not None:
            position = (pointer.x, pointer.y)
        else:
            position = (menu_button.bounds.x, menu_button.bounds.bottom)
        runtime = get_runtime()
        runtime.overlays.show_context_menu(ContextMenu((
            MenuItem("Open item", lambda _e: setattr(status, "text", "Context menu: Open item")),
            MenuItem("Rename", lambda _e: setattr(status, "text", "Context menu: Rename")),
            MenuItem("Delete", disabled=True),
        ), theme=theme), position=position)

    def show_toast(_event=None):
        get_runtime().overlays.show_toast(Toast("Settings saved successfully", "success", theme=theme))
        status.text = "Toast added — lifetime is advanced by the host clock"

    dialog_button.on_click = show_dialog
    popover_button.on_click = show_popover
    tooltip_button.on_click = show_tooltip
    menu_button.on_click = show_menu
    toast_button.on_click = show_toast

    root = column(
        row(
            column(
                Label("Yuktara UI", size=28, weight="bold", theme=theme),
                Label("Native overlay system", color=theme.muted, theme=theme),
            ),
            Badge("2.5 development", "primary", theme),
            spacing=16,
        ),
        Card((
            Label("Floating surfaces", size=18, weight="semibold", theme=theme),
            Label("Modal, anchored, passive and pointer-positioned overlays", size=13,
                  color=theme.muted, theme=theme),
            row(dialog_button, popover_button, spacing=10),
            row(tooltip_button, menu_button, spacing=10),
            toast_button,
            status,
        ), theme=theme),
        Card((
            Label("Interaction notes", size=16, weight="semibold", theme=theme),
            Label("• Dialogs trap keyboard focus and block the app underneath", size=13, theme=theme),
            Label("• Popovers flip and clamp to the window viewport", size=13, theme=theme),
            Label("• Tooltips and toasts do not capture pointer input", size=13, theme=theme),
            Label("• Toast expiry is driven by NativeRuntime.advance_time()", size=13, theme=theme),
        ), theme=theme),
        spacing=16, padding=24, background=theme.background,
    )

    width, height = 900, 620
    renderer = SkiaRenderer(RenderSize(width, height), skia_module=skia)
    runtime = NativeRuntime(lambda: root, renderer, width, height, clear_color=theme.background)
    runtime_ref["runtime"] = runtime
    window = SDL3Window("Yuktara UI — Overlay Gallery", width, height)
    window.run_runtime(
        runtime,
        lambda _runtime: renderer_frame(renderer, skia_module=skia),
    )


if __name__ == "__main__":
    main()
