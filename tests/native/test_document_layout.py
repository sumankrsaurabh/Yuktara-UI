from types import SimpleNamespace

import pytest

from novaui.native import (
    DocumentParagraph, DocumentPaginator, PageBreak, PageMargins,
    PageSize, PageTemplate, ParagraphStyle, TextStyleSpan,
)
from novaui.native.text import TextMeasurer
from novaui.native.typography import FontConfig


class FakeFont:
    def __init__(self, typeface, size):
        self.size = size

    def measureText(self, text):
        return len(text) * self.size * 0.5

    def getMetrics(self):
        return SimpleNamespace(fAscent=-self.size * 0.8,
                               fDescent=self.size * 0.2, fLeading=0)


class FakeSkia:
    class FontStyle:
        kNormal_Weight = 0
        kMedium_Weight = 1
        kSemiBold_Weight = 2
        kBold_Weight = 3
        kNormal_Width = 0
        kUpright_Slant = 0
        kItalic_Slant = 1

        def __init__(self, *args):
            pass

    class Typeface:
        @staticmethod
        def MakeFromName(name, style):
            return object()

        @staticmethod
        def MakeDefault():
            return object()

    Font = FakeFont


class RecordingRenderer:
    def __init__(self):
        self.rects = []
        self.strokes = []
        self.text = []

    def draw_rect(self, x, y, width, height, color, **kwargs):
        self.rects.append((x, y, width, height, color))

    def draw_stroke_rect(self, x, y, width, height, color, **kwargs):
        self.strokes.append((x, y, width, height, color))

    def draw_text(self, text, x, baseline, *, color, font):
        self.text.append((text, x, baseline, color, font))


def paginator():
    return DocumentPaginator(TextMeasurer(FakeSkia))


def small_page():
    return PageSize(80, 50), PageMargins(5, 5, 5, 5)


def test_a4_document_uses_print_friendly_default_geometry():
    result = paginator().paginate([DocumentParagraph("A4 page")])
    assert result.page_count == 1
    assert result.pages[0].width == pytest.approx(595.28)
    assert result.pages[0].height == pytest.approx(841.89)
    assert result.pages[0].body_top == 100
    assert result.pages[0].body_height == pytest.approx(641.89)


def test_document_paginates_long_paragraph_across_multiple_pages():
    size, margins = small_page()
    result = paginator().paginate(
        [DocumentParagraph("one two three four five six seven eight nine ten")],
        page_size=size, margins=margins,
        template=PageTemplate(header_height=0, footer_height=0),
    )
    assert result.page_count >= 2
    fragments = [fragment for page in result.pages for fragment in page.fragments]
    assert len(fragments) >= 2
    assert fragments[0].continues_to_next
    assert fragments[-1].continues_from_previous
    assert all(fragment.line_indices for fragment in fragments)


def test_explicit_page_break_starts_new_page_without_blank_page_at_document_start():
    size, margins = small_page()
    result = paginator().paginate(
        [PageBreak(), DocumentParagraph("first"), PageBreak(), DocumentParagraph("second")],
        page_size=size, margins=margins,
        template=PageTemplate(header_height=0, footer_height=0),
    )
    assert result.page_count == 2
    assert len(result.pages[0].fragments) == 1
    assert len(result.pages[1].fragments) == 1
    assert result.pages[0].fragments[0].paragraph.text == "first"
    assert result.pages[1].fragments[0].paragraph.text == "second"


def test_page_header_footer_resolve_page_and_total_placeholders():
    result = paginator().paginate(
        [DocumentParagraph("page one"), PageBreak(), DocumentParagraph("page two")],
        template=PageTemplate(
            header_left="Yuktara UI", footer_center="{page}/{pages}",
            footer_right="Page {page} of {pages}",
        ),
    )
    assert result.page_count == 2
    assert result.pages[0].header[0].text == "Yuktara UI"
    assert result.pages[0].footer[0].text == "1/2"
    assert result.pages[0].footer[1].text == "Page 1 of 2"
    assert result.pages[1].footer[0].text == "2/2"


def test_keep_together_moves_a_paragraph_to_next_page_when_it_fits_there():
    size, margins = small_page()
    template = PageTemplate(header_height=0, footer_height=0)
    result = paginator().paginate(
        [DocumentParagraph("short"),
         DocumentParagraph("two lines here", keep_together=True)],
        page_size=size, margins=margins, template=template,
    )
    # With the configured font, the short first block leaves enough room only
    # for the heading, so the keep-together block moves as one unit.
    assert result.page_count == 2
    assert result.pages[0].fragments[-1].paragraph.text == "short"
    assert all(f.paragraph.text == "two lines here" for f in result.pages[1].fragments)


def test_keep_with_next_keeps_heading_and_following_paragraph_on_same_page():
    size, margins = PageSize(80, 90), PageMargins(5, 5, 5, 5)
    result = paginator().paginate(
        [DocumentParagraph("body filler words filler words filler words"),
         DocumentParagraph("Heading", keep_with_next=True),
         DocumentParagraph("following paragraph")],
        page_size=size, margins=margins,
        template=PageTemplate(header_height=0, footer_height=0),
    )
    page_for_heading = next(i for i, page in enumerate(result.pages)
                            if any(f.paragraph.text == "Heading" for f in page.fragments))
    texts = [f.paragraph.text for f in result.pages[page_for_heading].fragments]
    assert "following paragraph" in texts


def test_paragraph_markers_are_visible_only_on_first_fragment():
    size, margins = small_page()
    style = ParagraphStyle(marker="•", marker_indent=18)
    result = paginator().paginate(
        [DocumentParagraph("one two three four five six seven eight nine ten", style=style)],
        page_size=size, margins=margins,
        template=PageTemplate(header_height=0, footer_height=0),
    )
    assert len(result.pages) >= 2
    fragments = [f for p in result.pages for f in p.fragments]
    assert fragments[0].continues_from_previous is False
    assert all(f.continues_from_previous for f in fragments[1:])


def test_inline_spans_survive_page_fragmentation_and_paint():
    size, margins = small_page()
    text = "styled content repeated many times styled content repeated many times"
    start = text.index("styled")
    result = paginator().paginate(
        [DocumentParagraph(text, spans=(TextStyleSpan(start, start + 6,
                                                       color=0xFFCC0000,
                                                       underline=True),))],
        page_size=size, margins=margins,
        template=PageTemplate(header_height=0, footer_height=0),
    )
    renderer = RecordingRenderer()
    result.paint_page(renderer, 0, x=5, y=7)
    assert renderer.rects  # page background
    assert renderer.strokes  # page outline
    assert renderer.text


def test_paint_page_rejects_invalid_index_and_uses_page_origin():
    result = paginator().paginate([DocumentParagraph("Hello")],
                                  template=PageTemplate(footer_right=""))
    renderer = RecordingRenderer()
    result.paint_page(renderer, 0, x=20, y=30)
    assert renderer.rects[0][:4] == (20, 30, 595.28, 841.89)
    assert renderer.text[0][0] == "Hello"
    with pytest.raises(IndexError):
        result.paint_page(renderer, 1)


@pytest.mark.parametrize("size,margins,template", [
    (PageSize(100, 100), PageMargins(60, 10, 10, 10), PageTemplate()),
    (PageSize(100, 100), PageMargins(10, 90, 10, 10), PageTemplate()),
])
def test_paginator_rejects_pages_without_usable_body(size, margins, template):
    with pytest.raises(ValueError, match="no usable body area"):
        paginator().paginate([], page_size=size, margins=margins, template=template)


def test_document_paragraph_rejects_hard_newlines_and_invalid_spans():
    with pytest.raises(ValueError, match="one paragraph"):
        DocumentParagraph("first\nsecond")
    with pytest.raises(ValueError, match="exceeds"):
        DocumentParagraph("abc", spans=(TextStyleSpan(1, 4),))


def test_template_unknown_placeholders_are_preserved():
    result = paginator().paginate(
        [DocumentParagraph("text")],
        template=PageTemplate(footer_left="{page} {custom}"),
    )
    assert result.pages[0].footer[0].text == "1 {custom}"
