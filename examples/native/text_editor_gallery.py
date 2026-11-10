"""Native text, selection, multilingual fallback and clipboard gallery."""
from __future__ import annotations

import time

from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import (
    Badge, Button, Card, Label, NativeRuntime, NativeTheme, TextArea, TextField,
    column, row,
)
from novaui.native.platform import EventType, SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame
from novaui.native.renderer import RenderSize, SkiaRenderer


def main():
    width, height = 960, 720
    theme = NativeTheme()
    window = SDL3Window("Yuktara UI — Native Text Gallery", width, height)
    window.open()

    status = Label(
        "Select text, drag to highlight, then use Ctrl+C / Ctrl+X / Ctrl+V.",
        size=13, color=theme.muted, theme=theme,
    ).build()
    name_field = TextField(
        "Yuktara Technologies", placeholder="Application name",
        width=860, clipboard=window, font_size=16,
    )
    editor = TextArea(
        "Native text editing with measured caret geometry.\n"
        "Devanagari: नमस्ते दुनिया — क्षमा।\n"
        "Bengali: বাংলা লেখা — Tamil: தமிழ்\n"
        "Emoji: 👨‍👩‍👧‍👦  👍🏽  🇮🇳\n"
        "Use the mouse to select text and the keyboard to edit.",
        placeholder="Start writing…", width=860, height=270,
        clipboard=window, font_size=16, font_family="Inter",
    )

    def clear_editor(_event=None):
        editor.value = ""
        editor.cursor = editor.anchor = 0
        editor._sync_node()
        status.text = "Editor cleared."

    def insert_sample(_event=None):
        editor.value = (
            "Yuktara UI 2.6\n\n"
            "Text measurement and painting share the same Skia font metrics.\n"
            "Common grapheme clusters remain whole during cursor movement.\n"
            "Clipboard operations use the SDL3 operating-system service."
        )
        editor.cursor = editor.anchor = len(editor.value)
        editor._sync_node()
        status.text = "Sample text inserted."

    root = column(
        row(
            column(
                Label("Yuktara UI", size=28, weight="bold", theme=theme),
                Label("Native text and typography", color=theme.muted, theme=theme),
            ),
            Badge("2.6 development", "primary", theme),
            spacing=14,
        ),
        Card((
            Label("Single-line input", size=16, weight="semibold", theme=theme),
            name_field,
        ), theme=theme),
        Card((
            row(
                Label("Multiline editor", size=16, weight="semibold", theme=theme),
                Button("Insert sample", on_click=insert_sample, variant="secondary", theme=theme),
                Button("Clear", on_click=clear_editor, variant="ghost", theme=theme),
                spacing=10,
            ),
            editor,
            status,
        ), theme=theme),
        Card((
            Label("Editing support", size=15, weight="semibold", theme=theme),
            Label("• Grapheme-aware Backspace, Delete and arrow movement", size=13, theme=theme),
            Label("• Shift selection, pointer drag and measured caret positions", size=13, theme=theme),
            Label("• Ctrl+A / Ctrl+C / Ctrl+X / Ctrl+V", size=13, theme=theme),
            Label("• Script-specific fallback fonts when installed", size=13, theme=theme),
        ), theme=theme),
        spacing=16, padding=24, background=theme.background,
    )

    renderer = SkiaRenderer(RenderSize(width, height), skia_module=skia)
    runtime = NativeRuntime(lambda: root, renderer, width, height,
                            clear_color=theme.background)
    runtime.start()
    previous = time.monotonic()
    running = True
    try:
        while running:
            for event in window.poll_input_events():
                if event.type is EventType.QUIT:
                    running = False
                    break
                runtime.dispatch(event)
            if running:
                now = time.monotonic()
                runtime.advance_time((now - previous) * 1000.0)
                previous = now
                runtime.render()
                window.present(renderer_frame(renderer, skia_module=skia))
    finally:
        runtime.stop()
        window.close()


if __name__ == "__main__":
    main()
