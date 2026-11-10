"""Create a native A4 document preview with headers, footers and pagination.

Run: python examples/native/document_pagination.py [output.png]
"""
from __future__ import annotations

import sys
from pathlib import Path

from novaui.native import (
    DocumentParagraph,
    DocumentPaginator,
    FontConfig,
    PageBreak,
    PageMargins,
    PageSize,
    PageTemplate,
    ParagraphStyle,
    SkiaRenderer,
    RenderSize,
    TextMeasurer,
    TextStyleSpan,
)


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "yuktara-document-page-1.png")
    renderer = SkiaRenderer(RenderSize(595.28, 841.89))
    measurer = TextMeasurer(renderer._skia, renderer._fonts)
    paginator = DocumentPaginator(measurer)

    title = "Yuktara UI: native document composition"
    title_start = title.index("native")
    paragraphs = [
        DocumentParagraph(
            title,
            style=ParagraphStyle(alignment="center", line_height=28, space_after=16),
            spans=(TextStyleSpan(title_start, title_start + len("native"),
                                 font_weight="bold", color=0xFF2457A7),),
            font=FontConfig(size=19, weight="semibold"),
            keep_with_next=True,
        ),
        DocumentParagraph(
            "Yuktara UI 3.0 introduces a backend-neutral page composition layer. "
            "Applications can lay out paragraphs on fixed-size pages, insert hard "
            "page breaks, and add page-numbered headers and footers without "
            "depending on a browser or web rendering engine.",
            style=ParagraphStyle(space_after=12, line_spacing=2),
            font=FontConfig(size=11),
            orphan_lines=2,
            widow_lines=2,
        ),
        DocumentParagraph(
            "Paragraph formatting remains part of the native text pipeline. "
            "Alignment, indentation, paragraph spacing, list markers and inline "
            "style spans are measured before pagination. Each page fragment keeps "
            "the original text layout and source offsets, which allows selection "
            "and editor features to be layered on later.",
            style=ParagraphStyle(left_indent=10, first_line_indent=18,
                                 space_after=14),
            font=FontConfig(size=11),
        ),
        DocumentParagraph(
            "A heading that stays with its next paragraph",
            style=ParagraphStyle(line_height=20, space_before=6, space_after=5),
            font=FontConfig(size=13, weight="semibold"),
            keep_with_next=True,
        ),
        DocumentParagraph(
            "The paginator supports keep-together blocks, keep-with-next groups, "
            "and configurable widow/orphan line counts. When a paragraph crosses "
            "a page boundary, it is represented by multiple page fragments while "
            "the underlying source text and measured clusters remain unchanged.",
            style=ParagraphStyle(space_after=10),
            font=FontConfig(size=11),
        ),
        PageBreak(),
        DocumentParagraph(
            "Second page",
            style=ParagraphStyle(alignment="center", line_height=25, space_after=15),
            font=FontConfig(size=18, weight="semibold"),
        ),
        DocumentParagraph(
            "The same document can be rendered by Skia, inspected in tests with a "
            "recording renderer, or consumed by a future export backend. The page "
            "model is independent from SDL3 window ownership and does not assume "
            "a particular display surface.",
            style=ParagraphStyle(space_after=10),
            font=FontConfig(size=11),
        ),
    ]
    layout = paginator.paginate(
        paragraphs,
        page_size=PageSize(),
        margins=PageMargins(64, 64, 64, 64),
        template=PageTemplate(
            header_left="YUKTARA UI",
            header_right="DOCUMENT LAYOUT",
            footer_left="Native SDL3 + Skia",
            footer_right="Page {page} of {pages}",
            header_height=26,
            footer_height=26,
            font=FontConfig(size=8),
        ),
    )
    layout.paint_page(renderer, 0)
    output.write_bytes(renderer.to_png_bytes())
    print(f"Rendered page 1 of {layout.page_count} to {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
