import pytest


def test_markdown_parser_maps_blocks_inline_styles_and_links():
    from novaui.native import parse_markdown, RichText
    from novaui.native.text import ParagraphStyle, TextStyleSpan

    source = (
        "# Heading\n\n"
        "A **bold** word, *emphasis*, and [Yuktara](https://example.com).\n\n"
        "- first item\n"
        "- second item\n\n"
        "`inline code`"
    )
    document = parse_markdown(source)
    assert document.text.startswith("Heading\nA bold word")
    assert "first item" in document.text and "second item" in document.text
    assert len(document.links) == 1
    link = document.links[0]
    assert document.text[link.start:link.end] == "Yuktara"
    assert link.url == "https://example.com"
    assert any(
        isinstance(span, TextStyleSpan)
        and document.text[span.start:span.end] == "bold"
        and span.font_weight == "bold"
        for span in document.spans
    )
    assert any(style.marker == "•" for style in document.paragraph_styles)
    assert any(span.underline for span in document.spans)

    widget = document.to_rich_text(size=15)
    assert isinstance(widget, RichText)
    assert widget.text == document.text
    assert widget.spans == document.spans
    assert widget.paragraph_styles == document.paragraph_styles


def test_markdown_parser_preserves_code_block_lines_and_styles():
    from novaui.native import parse_markdown

    document = parse_markdown("```python\nprint('hello')\nvalue = 42\n```")
    assert document.text == "print('hello')\nvalue = 42"
    assert document.text.count("\n") + 1 == len(document.paragraph_styles)
    assert any(
        span.font_family == "DejaVu Sans Mono" and span.background is not None
        for span in document.spans
    )


def test_markdown_parser_validates_input_and_size():
    from novaui.native import parse_markdown

    with pytest.raises(TypeError):
        parse_markdown(123)
    with pytest.raises(ValueError):
        parse_markdown("text", base_size=0)


def test_markdown_document_can_be_converted_without_losing_link_ranges():
    from novaui.native import parse_markdown

    document = parse_markdown("[docs](https://example.org/docs)")
    assert len(document.links) == 1
    link = document.links[0]
    assert document.text[link.start:link.end] == "docs"
    assert link.url == "https://example.org/docs"


def test_markdown_soft_breaks_keep_paragraph_style_indices_aligned():
    from novaui.native import parse_markdown

    document = parse_markdown("first line\nsecond line\n\nnext paragraph")
    assert document.text.count("\n") + 1 == len(document.paragraph_styles)
