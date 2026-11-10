"""Interactive gallery for native opacity animation and reduced motion."""
from __future__ import annotations

import time

from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import Badge, Button, Card, Label, NativeRuntime, NativeTheme, column, row
from novaui.native.platform import EventType, SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame
from novaui.native.renderer import RenderSize, SkiaRenderer


def main():
    theme = NativeTheme()
    runtime_ref = {"runtime": None}
    reduced_motion = {"enabled": False}
    status = Label("Ready — use the controls to animate the panel", size=13,
                   color=theme.muted, theme=theme).build()
    panel = Card((
        Label("Animated native surface", size=18, weight="semibold", theme=theme),
        Label("This panel uses LayoutNode.opacity and Skia group compositing.",
              size=13, color=theme.muted, theme=theme),
    ), theme=theme).build()

    def runtime():
        return runtime_ref["runtime"]

    def fade_out(_event=None):
        runtime().animate(panel, "opacity", 0.18, duration_ms=420,
                          easing="ease_out_cubic",
                          on_complete=lambda: setattr(status, "text", "Fade-out completed"))
        status.text = "Fading out…"

    def fade_in(_event=None):
        runtime().animate(panel, "opacity", 1.0, duration_ms=360,
                          easing="ease_in_out",
                          on_complete=lambda: setattr(status, "text", "Panel restored"))
        status.text = "Fading in…"

    def toggle_reduced_motion(_event=None):
        reduced_motion["enabled"] = not reduced_motion["enabled"]
        runtime().set_reduced_motion(reduced_motion["enabled"])
        motion_button.text = ("Reduced motion: On" if reduced_motion["enabled"]
                              else "Reduced motion: Off")
        status.text = "Reduced motion enabled" if reduced_motion["enabled"] else "Reduced motion disabled"

    fade_out_button = Button("Fade out", on_click=fade_out, theme=theme)
    fade_in_button = Button("Restore", on_click=fade_in, variant="secondary", theme=theme)
    motion_button = Button("Reduced motion: Off", on_click=toggle_reduced_motion,
                           variant="outline", theme=theme).build()

    root = column(
        row(
            column(
                Label("Yuktara UI", size=28, weight="bold", theme=theme),
                Label("Native animation and accessibility", color=theme.muted, theme=theme),
            ),
            Badge("2.5 development", "primary", theme),
            spacing=16,
        ),
        Card((
            Label("Opacity transition", size=18, weight="semibold", theme=theme),
            Label("Animations advance only when the host supplies elapsed time.",
                  size=13, color=theme.muted, theme=theme),
            row(fade_out_button, fade_in_button, motion_button, spacing=10),
            status,
        ), theme=theme),
        panel,
        Card((
            Label("Accessibility details", size=16, weight="semibold", theme=theme),
            Label("• Keyboard focus uses a visible native focus ring", size=13, theme=theme),
            Label("• Context menus support Up/Down and Enter/Space", size=13, theme=theme),
            Label("• Modal dialogs own the active semantic scope", size=13, theme=theme),
            Label("• Closing overlays restores focus when possible", size=13, theme=theme),
        ), theme=theme),
        spacing=16, padding=24, background=theme.background,
    )

    width, height = 900, 620
    renderer = SkiaRenderer(RenderSize(width, height), skia_module=skia)
    runtime_instance = NativeRuntime(lambda: root, renderer, width, height,
                                     clear_color=theme.background)
    runtime_ref["runtime"] = runtime_instance
    window = SDL3Window("Yuktara UI — Animation Gallery", width, height)
    window.open()
    runtime_instance.start()
    previous = time.monotonic()
    running = True
    try:
        while running:
            now = time.monotonic()
            runtime_instance.advance_time((now - previous) * 1000.0)
            previous = now
            for event in window.poll_input_events():
                if event.type is EventType.QUIT:
                    running = False
                    break
                runtime_instance.dispatch(event)
            if running:
                runtime_instance.render()
                window.present(renderer_frame(renderer, skia_module=skia))
    finally:
        runtime_instance.stop()
        window.close()


if __name__ == "__main__":
    main()
