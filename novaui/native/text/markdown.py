"""Optional Mistune adapter for native, Skia-rendered Markdown text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .measure import ParagraphStyle, TextStyleSpan, grapheme_spans


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    """Source range and destination for a link in the flattened document."""

    start: int
    end: int
    url: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class MarkdownDocument:
    """Plain source text plus native text styles and link metadata."""

    text: str
    spans: tuple[TextStyleSpan, ...]
    paragraph_styles: tuple[ParagraphStyle, ...]
    links: tuple[MarkdownLink, ...]

    def to_rich_text(self, **kwargs):
        """Create a native RichText widget without introducing a web renderer."""
        from ..widgets import RichText

        return RichText(
            self.text,
            spans=self.spans,
            paragraph_styles=self.paragraph_styles,
            **kwargs,
        )


def _style_span(start: int, end: int, style: Mapping[str, Any]) -> TextStyleSpan | None:
    if start >= end:
        return None
    allowed = {
        key: style[key]
        for key in ("font_family", "font_size", "font_weight", "color", "underline", "background")
        if key in style
    }
    if not allowed:
        return None
    return TextStyleSpan(start, end, **allowed)


def parse_markdown(
    source: str,
    *,
    base_size: float = 14.0,
    code_background: int = 0x142E7D32,
    list_indent: float = 24.0,
    paragraph_spacing: float = 8.0,
) -> MarkdownDocument:
    """Parse common Markdown into source-indexed native RichText styles.

    Mistune performs Markdown parsing only. The returned document is plain
    Python data; Yuktara retains layout, accessibility, interaction and Skia
    painting. Supported blocks include paragraphs, headings, lists, quotes,
    thematic breaks and fenced/indented code. Inline support includes strong,
    emphasis (represented as underline until italic font styles are supported),
    code spans, links and images' alt text.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    for name, value in (("base_size", base_size), ("list_indent", list_indent),
                        ("paragraph_spacing", paragraph_spacing)):
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{name} must be a non-negative number")
    if base_size <= 0:
        raise ValueError("base_size must be positive")
    try:
        import mistune
    except ImportError as exc:
        raise RuntimeError(
            "Markdown parsing requires Mistune. "
            "Install it with: pip install 'yuktara-ui[markdown]'"
        ) from exc

    parser = mistune.create_markdown(
        renderer="ast",
        plugins=["table", "task_lists"],
    )
    ast = parser(source)
    blocks: list[tuple[str, ParagraphStyle, tuple[tuple[int, int, dict], ...], tuple[tuple[int, int, str, str | None], ...]]] = []

    def inline(tokens, inherited=None):
        inherited = dict(inherited or {})
        pieces: list[str] = []
        spans: list[tuple[int, int, dict]] = []
        links: list[tuple[int, int, str, str | None]] = []
        cursor = 0

        def emit(value: str, style: dict):
            nonlocal cursor
            if not value:
                return
            start = cursor
            pieces.append(value)
            cursor += len(value)
            if style:
                spans.append((start, cursor, dict(style)))

        def walk(items, style):
            for item in items or ():
                kind = item.get("type", "")
                raw = item.get("raw")
                if kind in {"text", "codespan", "inline_html"}:
                    current = dict(style)
                    if kind == "codespan":
                        current.update({
                            "font_family": "DejaVu Sans Mono",
                            "background": 0x183B82F6,
                        })
                    emit(str(raw or ""), current)
                elif kind in {"softbreak", "linebreak"}:
                    emit("\n", style)
                elif kind in {"strong", "emphasis", "strikethrough"}:
                    current = dict(style)
                    if kind == "strong":
                        current["font_weight"] = "bold"
                    elif kind == "emphasis":
                        current["underline"] = True
                    walk(item.get("children"), current)
                elif kind == "link":
                    start = cursor
                    walk(item.get("children"), style)
                    end = cursor
                    attrs = item.get("attrs") or {}
                    url = attrs.get("url")
                    title = attrs.get("title")
                    if isinstance(url, str) and url and end > start:
                        links.append((start, end, url, title))
                        spans.append((start, end, {**style, "underline": True}))
                elif kind == "image":
                    attrs = item.get("attrs") or {}
                    alt = attrs.get("alt")
                    if alt:
                        emit(str(alt), style)
                    else:
                        walk(item.get("children"), style)
                elif item.get("children"):
                    walk(item["children"], style)
                elif raw:
                    emit(str(raw), style)

        walk(tokens, inherited)
        return "".join(pieces), tuple(spans), tuple(links)

    def add_block(text, paragraph_style=None, spans=(), links=()):
        if not text:
            return
        blocks.append((
            text,
            paragraph_style or ParagraphStyle(space_after=paragraph_spacing),
            tuple(spans),
            tuple(links),
        ))

    def visit(items, *, list_marker=None, quote_depth=0):
        for item in items or ():
            kind = item.get("type", "")
            attrs = item.get("attrs") or {}
            children = item.get("children") or ()
            if kind == "blank_line":
                continue
            if kind == "paragraph":
                text, spans, links = inline(children)
                marker = list_marker
                style = ParagraphStyle(
                    left_indent=quote_depth * list_indent,
                    marker=marker,
                    marker_indent=list_indent if marker else 20.0,
                    space_after=paragraph_spacing,
                )
                add_block(text, style, spans, links)
            elif kind == "heading":
                level = max(1, min(6, int(attrs.get("level", 1))))
                text, spans, links = inline(children, {
                    "font_size": base_size * (2.0 - 0.15 * (level - 1)),
                    "font_weight": "bold",
                })
                add_block(text, ParagraphStyle(
                    left_indent=quote_depth * list_indent,
                    space_before=paragraph_spacing,
                    space_after=paragraph_spacing,
                ), spans, links)
            elif kind == "block_code":
                raw = str(item.get("raw") or "").rstrip("\n")
                if raw:
                    code_style = {
                        "font_family": "DejaVu Sans Mono",
                        "font_size": base_size * 0.92,
                        "background": code_background,
                    }
                    lines = raw.split("\n")
                    for line in lines:
                        spans = ((0, len(line), code_style),) if line else ()
                        add_block(line, ParagraphStyle(
                            left_indent=quote_depth * list_indent,
                            space_after=0,
                        ), spans)
            elif kind == "list":
                ordered = bool(attrs.get("ordered"))
                start = int(attrs.get("start", 1) or 1)
                for index, child in enumerate(children):
                    marker = f"{start + index}." if ordered else "•"
                    visit((child,), list_marker=marker, quote_depth=quote_depth)
            elif kind == "list_item":
                visit(children, list_marker=list_marker, quote_depth=quote_depth)
            elif kind == "block_quote":
                visit(children, list_marker=list_marker, quote_depth=quote_depth + 1)
            elif kind == "thematic_break":
                add_block("────────", ParagraphStyle(
                    left_indent=quote_depth * list_indent,
                    space_before=paragraph_spacing,
                    space_after=paragraph_spacing,
                ))
            elif kind == "table":
                for row in children:
                    cells = row.get("children") or ()
                    values = []
                    for cell in cells:
                        value, _spans, _links = inline(cell.get("children") or ())
                        values.append(value)
                    add_block("   |   ".join(values), ParagraphStyle(
                        left_indent=quote_depth * list_indent,
                        space_after=paragraph_spacing / 2,
                    ))
            elif kind in {"block_html"}:
                add_block(str(item.get("raw") or ""), ParagraphStyle(
                    left_indent=quote_depth * list_indent,
                    space_after=paragraph_spacing,
                ))
            elif children:
                visit(children, list_marker=list_marker, quote_depth=quote_depth)

    visit(ast)
    text_parts: list[str] = []
    output_spans: list[TextStyleSpan] = []
    paragraph_styles: list[ParagraphStyle] = []
    output_links: list[MarkdownLink] = []
    offset = 0
    for index, (block_text, paragraph_style, local_spans, local_links) in enumerate(blocks):
        if index:
            text_parts.append("\n")
            offset += 1
        text_parts.append(block_text)
        paragraph_styles.extend([paragraph_style] * (block_text.count("\n") + 1))
        for start, end, style in local_spans:
            span = _style_span(offset + start, offset + end, style)
            if span is not None:
                output_spans.append(span)
        for start, end, url, title in local_links:
            output_links.append(MarkdownLink(offset + start, offset + end, url, title))
        offset += len(block_text)

    # Inline emphasis/link ranges can overlap. Merge their attributes into a
    # disjoint interval set before passing spans to the strict RichText model.
    boundaries = [0]
    boundaries.extend(end for _start, end in grapheme_spans("".join(text_parts)))
    merged: list[TextStyleSpan] = []
    for start, end in zip(boundaries, boundaries[1:]):
        active = [span for span in output_spans if span.start < end and span.end > start]
        if not active:
            continue
        values = {}
        for span in active:
            for key in ("font_family", "font_size", "font_weight", "color", "underline", "background"):
                value = getattr(span, key)
                if value is not None and value is not False:
                    values[key] = value
        current = _style_span(start, end, values)
        if current is None:
            continue
        if merged and merged[-1].end == start and all(
            getattr(merged[-1], key) == getattr(current, key)
            for key in ("font_family", "font_size", "font_weight", "color", "underline", "background")
        ):
            previous = merged[-1]
            merged[-1] = TextStyleSpan(previous.start, end, **{
                key: getattr(previous, key)
                for key in ("font_family", "font_size", "font_weight", "color", "underline", "background")
            })
        else:
            merged.append(current)

    return MarkdownDocument(
        "".join(text_parts),
        tuple(merged),
        tuple(paragraph_styles),
        tuple(output_links),
    )


__all__ = ["MarkdownDocument", "MarkdownLink", "parse_markdown"]
