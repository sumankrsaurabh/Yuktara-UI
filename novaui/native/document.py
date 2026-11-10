"""Backend-neutral document pagination and native page painting.

The document layer composes existing paragraph-aware TextLayout objects into
fixed-size pages. It deliberately owns no platform window and can be tested
with an injected TextMeasurer and renderer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Iterable, Mapping, Sequence

from .text.measure import ParagraphStyle, TextLayout, TextMeasurer, TextStyleSpan
from .typography import FontConfig


@dataclass(frozen=True, slots=True)
class PageSize:
    """Logical page dimensions in points/pixels; defaults to ISO A4 portrait."""

    width: float = 595.28
    height: float = 841.89

    def __post_init__(self) -> None:
        if (not isfinite(float(self.width)) or not isfinite(float(self.height))
                or self.width <= 0 or self.height <= 0):
            raise ValueError("Page dimensions must be finite and positive")


@dataclass(frozen=True, slots=True)
class PageMargins:
    top: float = 72.0
    right: float = 72.0
    bottom: float = 72.0
    left: float = 72.0

    def __post_init__(self) -> None:
        for name in ("top", "right", "bottom", "left"):
            value = float(getattr(self, name))
            if not isfinite(value) or value < 0:
                raise ValueError(f"Page margin {name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class PageBreak:
    """An explicit hard page break between document blocks."""


@dataclass(frozen=True, slots=True)
class DocumentParagraph:
    """One independently formatted paragraph in a paginated document."""

    text: str
    style: ParagraphStyle = ParagraphStyle()
    spans: tuple[TextStyleSpan, ...] = ()
    font: FontConfig = FontConfig()
    keep_together: bool = False
    keep_with_next: bool = False
    widow_lines: int = 2
    orphan_lines: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("DocumentParagraph.text must be a string")
        if "\n" in self.text or "\r" in self.text:
            raise ValueError("DocumentParagraph represents one paragraph; use separate blocks for hard breaks")
        if not isinstance(self.style, ParagraphStyle):
            raise TypeError("style must be a ParagraphStyle")
        if not isinstance(self.font, FontConfig):
            raise TypeError("font must be a FontConfig")
        if not isinstance(self.keep_together, bool) or not isinstance(self.keep_with_next, bool):
            raise TypeError("keep_together and keep_with_next must be bool values")
        if not isinstance(self.widow_lines, int) or self.widow_lines < 1:
            raise ValueError("widow_lines must be a positive integer")
        if not isinstance(self.orphan_lines, int) or self.orphan_lines < 1:
            raise ValueError("orphan_lines must be a positive integer")
        # Reuse the source-range/grapheme validation used by RichText.
        normalized_spans = TextMeasurer._normalize_style_spans(self.text, self.spans)
        object.__setattr__(self, "spans", normalized_spans)


@dataclass(frozen=True, slots=True)
class PageTemplate:
    """Page decorations. Templates may use ``{page}`` and ``{pages}``."""

    header_left: str = ""
    header_center: str = ""
    header_right: str = ""
    footer_left: str = ""
    footer_center: str = ""
    footer_right: str = "Page {page} of {pages}"
    header_height: float = 28.0
    footer_height: float = 28.0
    font: FontConfig = FontConfig(size=9)
    color: object = 0xFF667085

    def __post_init__(self) -> None:
        for name in ("header_left", "header_center", "header_right",
                     "footer_left", "footer_center", "footer_right"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be a string")
        for name in ("header_height", "footer_height"):
            value = float(getattr(self, name))
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if not isinstance(self.font, FontConfig):
            raise TypeError("PageTemplate.font must be a FontConfig")


@dataclass(frozen=True, slots=True)
class PositionedPageText:
    text: str
    x: float
    baseline: float
    width: float
    font: FontConfig
    color: object


@dataclass(frozen=True, slots=True)
class ParagraphFragment:
    """The visible line range of a source paragraph on one page."""

    block_index: int
    paragraph: DocumentParagraph
    layout: TextLayout = field(repr=False, compare=False)
    line_indices: tuple[int, ...]
    line_y_offsets: tuple[float, ...]
    y: float
    continues_from_previous: bool = False
    continues_to_next: bool = False

    @property
    def lines(self):
        return tuple(self.layout.lines[index] for index in self.line_indices)


@dataclass(frozen=True, slots=True)
class DocumentPage:
    number: int
    width: float
    height: float
    margins: PageMargins
    body_top: float
    body_height: float
    fragments: tuple[ParagraphFragment, ...]
    header: tuple[PositionedPageText, ...] = ()
    footer: tuple[PositionedPageText, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentLayout:
    pages: tuple[DocumentPage, ...]
    page_size: PageSize
    margins: PageMargins

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def paint_page(self, renderer, page_index: int, *, x: float = 0.0, y: float = 0.0,
                   page_color: object = 0xFFFFFFFF,
                   border_color: object | None = 0xFFD0D5DD) -> None:
        """Paint one page using the native renderer protocol (no window needed)."""
        if not 0 <= page_index < len(self.pages):
            raise IndexError("page_index is outside this document")
        page = self.pages[page_index]
        from .rendering.tree_painter import parse_color
        draw_rect = getattr(renderer, "draw_rect", None)
        if not callable(draw_rect):
            raise TypeError("renderer must provide draw_rect()")
        draw_rect(x, y, page.width, page.height, parse_color(page_color))
        if border_color is not None:
            draw_stroke = getattr(renderer, "draw_stroke_rect", None)
            if callable(draw_stroke):
                draw_stroke(x, y, page.width, page.height, parse_color(border_color), stroke_width=1)
        for item in (*page.header, *page.footer):
            renderer.draw_text(item.text, x + item.x, y + item.baseline,
                               color=parse_color(item.color), font=item.font)

        for fragment in page.fragments:
            paragraph = fragment.paragraph
            marker_painted = False
            for fragment_line_index, line_index in enumerate(fragment.line_indices):
                line = fragment.layout.lines[line_index]
                local_y = fragment.y + fragment.line_y_offsets[fragment_line_index]
                baseline = y + page.body_top + local_y + (line.baseline - line.top)
                line_x = x + page.margins.left + line.x_offset
                if line.paint_runs:
                    self._paint_line_runs(renderer, line, line_x, baseline, y + page.body_top + local_y)
                elif line.glyph_runs:
                    draw_glyph_run = getattr(renderer, "draw_glyph_run", None)
                    if not callable(draw_glyph_run):
                        raise RuntimeError("Renderer does not support pre-shaped glyph runs")
                    for glyph_run in line.glyph_runs:
                        draw_glyph_run(glyph_run.glyph_ids, glyph_run.positions,
                                       line_x, baseline, color=0xFF202735,
                                       typeface=glyph_run.typeface, size=glyph_run.font_size)
                else:
                    renderer.draw_text(line.text, line_x, baseline,
                                       color=0xFF202735, font=paragraph.font)
                if (not marker_painted and not fragment.continues_from_previous
                        and fragment_line_index == 0 and paragraph.style.marker):
                    marker_x = x + page.margins.left + max(
                        0.0, paragraph.style.effective_left_indent - paragraph.style.marker_indent
                    )
                    renderer.draw_text(
                        paragraph.style.marker, marker_x, baseline,
                        color=parse_color(paragraph.style.marker_color
                                          if paragraph.style.marker_color is not None
                                          else 0xFF202735), font=paragraph.font,
                    )
                    marker_painted = True

    @staticmethod
    def _paint_line_runs(renderer, line, line_x: float, baseline: float,
                         line_top: float) -> None:
        draw_glyph_run = getattr(renderer, "draw_glyph_run", None)
        draw_rect = getattr(renderer, "draw_rect", None)
        for run in line.paint_runs:
            run_x = line_x + run.x
            from .rendering.tree_painter import parse_color
            color = parse_color(run.color if run.color is not None else 0xFF202735)
            if run.background is not None and callable(draw_rect):
                draw_rect(run_x, line_top, run.width, line.height or 1.0, parse_color(run.background))
            if run.glyph_runs:
                if not callable(draw_glyph_run):
                    raise RuntimeError("Renderer does not support pre-shaped glyph runs")
                for glyph_run in run.glyph_runs:
                    draw_glyph_run(glyph_run.glyph_ids, glyph_run.positions,
                                   line_x, baseline, color=color,
                                   typeface=glyph_run.typeface, size=glyph_run.font_size)
            else:
                renderer.draw_text(run.text, run_x, baseline, color=color, font=run.font_config)
            if run.underline and callable(draw_rect):
                underline_y = baseline + max(1.0, run.font_config.size * 0.08)
                draw_rect(run_x, underline_y, run.width,
                          max(1.0, run.font_config.size / 16.0), color)


class DocumentPaginator:
    """Paginate paragraph blocks using the framework's existing text engine."""

    def __init__(self, text_measurer: TextMeasurer):
        if not callable(getattr(text_measurer, "measure", None)):
            raise TypeError("text_measurer must provide measure()")
        self.text_measurer = text_measurer

    @staticmethod
    def _format_template(value: str, page: int, pages: int) -> str:
        class SafeValues(dict):
            def __missing__(self, key):
                return "{" + key + "}"
        return value.format_map(SafeValues(page=page, pages=pages))

    def _decoration(self, template: PageTemplate, values: Sequence[str], *,
                    y: float, page_size: PageSize, margins: PageMargins) -> tuple[PositionedPageText, ...]:
        result = []
        body_left = margins.left
        body_right = page_size.width - margins.right
        for alignment, raw in zip(("left", "center", "right"), values):
            if not raw:
                continue
            text = raw
            width = self.text_measurer.measure(text, template.font, wrap=False).width
            if alignment == "center":
                x = (page_size.width - width) / 2
            elif alignment == "right":
                x = body_right - width
            else:
                x = body_left
            result.append(PositionedPageText(text, x, y, width, template.font, template.color))
        return tuple(result)

    def paginate(self, blocks: Iterable[DocumentParagraph | PageBreak], *,
                 page_size: PageSize = PageSize(),
                 margins: PageMargins = PageMargins(),
                 template: PageTemplate = PageTemplate()) -> DocumentLayout:
        if not isinstance(page_size, PageSize) or not isinstance(margins, PageMargins):
            raise TypeError("page_size and margins must be PageSize and PageMargins")
        if not isinstance(template, PageTemplate):
            raise TypeError("template must be a PageTemplate")
        body_width = page_size.width - margins.left - margins.right
        body_height = page_size.height - margins.top - margins.bottom - template.header_height - template.footer_height
        if body_width <= 0 or body_height <= 0:
            raise ValueError("Page margins and header/footer reservations leave no usable body area")
        body_top = margins.top + template.header_height

        prepared: list[tuple[DocumentParagraph | PageBreak, TextLayout | None]] = []
        for block in blocks:
            if isinstance(block, PageBreak):
                prepared.append((block, None))
            elif isinstance(block, DocumentParagraph):
                layout = self.text_measurer.measure(
                    block.text, block.font, max_width=body_width, wrap=True,
                    style_spans=block.spans, paragraph_styles=(block.style,),
                )
                prepared.append((block, layout))
            else:
                raise TypeError("blocks must contain DocumentParagraph or PageBreak values")

        page_fragments: list[list[ParagraphFragment]] = [[]]
        cursor_y = 0.0

        def start_page() -> None:
            nonlocal cursor_y
            if page_fragments[-1]:
                page_fragments.append([])
                cursor_y = 0.0
            elif cursor_y > 0:
                page_fragments.append([])
                cursor_y = 0.0

        def has_content() -> bool:
            return bool(page_fragments[-1]) or cursor_y > 0

        index = 0
        while index < len(prepared):
            block, layout = prepared[index]
            if isinstance(block, PageBreak):
                if has_content():
                    page_fragments.append([])
                    cursor_y = 0.0
                index += 1
                continue

            assert layout is not None
            # Keep a heading/paragraph with its following block when the group
            # fits on a fresh page but not in the current remainder.
            group_height = 0.0
            group_end = index
            while group_end < len(prepared):
                group_block, group_layout = prepared[group_end]
                if not isinstance(group_block, DocumentParagraph) or group_layout is None:
                    break
                group_height += group_layout.height
                keep_next = group_block.keep_with_next
                group_end += 1
                if not keep_next:
                    break
            if (group_end > index + 1 and group_height <= body_height
                    and has_content() and group_height > body_height - cursor_y):
                start_page()

            paragraph = block
            lines = layout.lines
            if not lines:
                index += 1
                continue
            before = paragraph.style.space_before
            after = paragraph.style.space_after
            total_height = layout.height
            if (paragraph.keep_together and total_height <= body_height
                    and has_content() and total_height > body_height - cursor_y):
                start_page()

            if before and cursor_y + before + lines[0].height > body_height and has_content():
                start_page()
            cursor_y += before
            line_index = 0
            first_fragment = True
            while line_index < len(lines):
                available = body_height - cursor_y
                fit = 0
                for candidate in range(line_index, len(lines)):
                    line_top_delta = lines[candidate].top - lines[line_index].top
                    bottom = line_top_delta + lines[candidate].height
                    if bottom <= available + 1e-6:
                        fit += 1
                    else:
                        break
                if fit == 0:
                    if has_content():
                        start_page()
                        continue
                    # A single line taller than the available body must still
                    # be emitted to guarantee forward progress.
                    fit = 1

                remaining = len(lines) - line_index
                if fit < remaining:
                    if first_fragment and fit < paragraph.orphan_lines and has_content():
                        start_page()
                        continue
                    # Keep the configured widow count together on the next page
                    # whenever the current page can still hold the orphan count.
                    leave = remaining - fit
                    if leave < paragraph.widow_lines:
                        adjusted = remaining - paragraph.widow_lines
                        if adjusted >= paragraph.orphan_lines:
                            fit = adjusted
                        elif has_content():
                            start_page()
                            continue

                chosen = tuple(range(line_index, line_index + fit))
                selected_first_top = lines[line_index].top
                y_offsets = tuple(lines[item].top - selected_first_top for item in chosen)
                page_fragments[-1].append(ParagraphFragment(
                    block_index=index, paragraph=paragraph, layout=layout,
                    line_indices=chosen, line_y_offsets=y_offsets, y=cursor_y,
                    continues_from_previous=not first_fragment,
                    continues_to_next=(line_index + fit) < len(lines),
                ))
                last_line = lines[chosen[-1]]
                consumed = (last_line.top - selected_first_top) + last_line.height
                cursor_y += consumed
                line_index += fit
                first_fragment = False
                if line_index < len(lines):
                    page_fragments.append([])
                    cursor_y = 0.0
            cursor_y += after
            index += 1

        # A completely empty input still represents one printable page.
        fragments_by_page = page_fragments or [[]]
        page_count = len(fragments_by_page)
        pages = []
        for page_index, fragments in enumerate(fragments_by_page, 1):
            substitutions_header = tuple(self._format_template(value, page_index, page_count)
                                          for value in (template.header_left, template.header_center,
                                                        template.header_right))
            substitutions_footer = tuple(self._format_template(value, page_index, page_count)
                                          for value in (template.footer_left, template.footer_center,
                                                        template.footer_right))
            header_baseline = margins.top + max(template.font.size, template.header_height * 0.65)
            footer_baseline = page_size.height - margins.bottom - template.footer_height + max(
                template.font.size, template.footer_height * 0.65
            )
            header = self._decoration(template, substitutions_header, y=header_baseline,
                                      page_size=page_size, margins=margins)
            footer = self._decoration(template, substitutions_footer, y=footer_baseline,
                                      page_size=page_size, margins=margins)
            pages.append(DocumentPage(
                page_index, page_size.width, page_size.height, margins,
                body_top, body_height, tuple(fragments), header, footer,
            ))
        return DocumentLayout(tuple(pages), page_size, margins)


__all__ = [
    "PageSize", "PageMargins", "PageBreak", "DocumentParagraph", "PageTemplate",
    "PositionedPageText", "ParagraphFragment", "DocumentPage", "DocumentLayout",
    "DocumentPaginator",
]
