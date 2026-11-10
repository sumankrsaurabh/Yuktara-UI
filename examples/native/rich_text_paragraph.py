"""Native paragraph and rich text gallery for Yuktara UI 2.9.

Run: python examples/native/rich_text_paragraph.py
"""
from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import (
    Label, NativeRuntime, NativeTheme, ParagraphStyle, RichText, TextStyleSpan,
    column,
)
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame
from novaui.native.renderer import RenderSize, SkiaRenderer


def main():
    theme = NativeTheme()
    body = "A native paragraph can mix font weight, color, background and underline."
    native_start = body.index("native")
    weight_start = body.index("font weight")
    content = column(
        Label("Paragraph layout", size=26, weight="bold", theme=theme),
        Label("Rich inline typography using one retained text node", color=theme.muted, theme=theme),
        RichText(
            body,
            size=17,
            spans=(
                TextStyleSpan(
                    native_start, native_start + len("native"),
                    font_weight="bold", color=theme.primary,
                    background=theme.primary_soft,
                ),
                TextStyleSpan(
                    weight_start, weight_start + len("font weight"),
                    font_weight="semibold", underline=True,
                ),
            ),
        ),
        Label("CJK wrapping", size=16, weight="semibold", theme=theme),
        RichText("日本語と中文字符会在适当的字形边界换行。", size=18, theme=theme),
        Label("Non-breaking content", size=16, weight="semibold", theme=theme),
        RichText("Keep 12\u00a0GB together; do not split a non-breaking pair.", size=16, theme=theme),
        Label("Paragraph formatting", size=16, weight="semibold", theme=theme),
        RichText(
            "First-line indentation and paragraph spacing are independent.\n"
            "A native list marker is painted once, while wrapped lines align with the text.",
            size=16, theme=theme,
            paragraph_styles=(
                ParagraphStyle(
                    alignment="start", left_indent=8, first_line_indent=14,
                    space_before=4, space_after=10, line_spacing=2,
                ),
                ParagraphStyle(marker="•", marker_indent=22,
                               space_before=2, line_height=22),
            ),
        ),
        spacing=14,
        padding=28,
        background=theme.background,
    )

    renderer = SkiaRenderer(RenderSize(1000, 680), skia_module=skia)
    runtime = NativeRuntime(lambda: content, renderer, 1000, 680,
                            clear_color=theme.background)
    window = SDL3Window("Yuktara UI — Rich Text and Paragraphs", 1000, 680)
    window.run_runtime(
        runtime,
        lambda _runtime: renderer_frame(renderer, skia_module=skia),
    )


if __name__ == "__main__":
    main()
