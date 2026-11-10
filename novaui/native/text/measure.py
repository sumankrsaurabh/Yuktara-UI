"""Skia-backed Unicode-aware text measurement and line geometry.

The layout engine keeps source offsets in Python string indices (Unicode code
points), while cluster boundaries prevent caret/selection operations from
splitting common grapheme sequences such as combining accents, emoji modifiers,
ZWJ emoji and regional-indicator flags.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Any, Mapping, Sequence
import unicodedata

from ..typography import FontConfig, FontResolver
from .shaping import HarfBuzzShaper, ShapedGlyphRun
from .linebreak import can_break_between, is_nonbreaking_boundary


def _is_variation_selector(codepoint: int) -> bool:
    return 0xFE00 <= codepoint <= 0xFE0F or 0xE0100 <= codepoint <= 0xE01EF


def _is_emoji_modifier(codepoint: int) -> bool:
    return 0x1F3FB <= codepoint <= 0x1F3FF


def _is_regional_indicator(codepoint: int) -> bool:
    return 0x1F1E6 <= codepoint <= 0x1F1FF


def _is_virama(character: str) -> bool:
    return "VIRAMA" in unicodedata.name(character, "")


def grapheme_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Return dependency-free grapheme-like spans for common Unicode sequences.

    This covers combining marks, variation selectors, emoji skin tones, ZWJ
    sequences, paired regional indicators and common Indic virama conjuncts.
    It is intentionally not a complete implementation of Unicode Standard
    Annex #29; uncommon script-specific rules still need a full segmenter.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    spans: list[tuple[int, int]] = []
    index = 0
    regional_run = 0
    while index < len(text):
        start = index
        first = ord(text[index])
        index += 1
        if _is_regional_indicator(first):
            regional_run += 1
            if regional_run % 2 == 1 and index < len(text) and _is_regional_indicator(ord(text[index])):
                index += 1
        else:
            regional_run = 0
        while index < len(text):
            cp = ord(text[index])
            category = unicodedata.category(text[index])
            if _is_virama(text[index]):
                # Indic conjuncts retain the linker and following consonant in
                # the same editing unit, including explicit join controls.
                index += 1
                if index < len(text) and ord(text[index]) in (0x200C, 0x200D):
                    index += 1
                if index < len(text) and unicodedata.category(text[index]).startswith("L"):
                    index += 1
                continue
            if category.startswith("M") or _is_variation_selector(cp) or _is_emoji_modifier(cp):
                index += 1
                continue
            if cp == 0x200D and index + 1 < len(text):  # ZWJ + next base + extensions
                index += 2
                while index < len(text):
                    next_cp = ord(text[index])
                    if (unicodedata.category(text[index]).startswith("M")
                            or _is_variation_selector(next_cp)
                            or _is_emoji_modifier(next_cp)):
                        index += 1
                    else:
                        break
                continue
            break
        spans.append((start, index))
    return tuple(spans)


def previous_grapheme_boundary(text: str, offset: int) -> int:
    offset = max(0, min(len(text), int(offset)))
    previous = 0
    for start, end in grapheme_spans(text):
        if offset <= start:
            return previous
        if offset <= end:
            return start
        previous = end
    return previous


def next_grapheme_boundary(text: str, offset: int) -> int:
    offset = max(0, min(len(text), int(offset)))
    for start, end in grapheme_spans(text):
        if start >= offset or start < offset < end:
            return end
    return len(text)


def normalize_grapheme_boundary(text: str, offset: int, *, forward: bool = False) -> int:
    offset = max(0, min(len(text), int(offset)))
    for start, end in grapheme_spans(text):
        if start < offset < end:
            return end if forward else start
    return offset


@dataclass(frozen=True, slots=True)
class TextStyleSpan:
    """A non-overlapping styled source range in a paragraph.

    Offsets are Python string/code-point offsets in the original text. ``None``
    fields inherit the paragraph's default style. Colors use ARGB integers or
    the renderer's accepted hexadecimal color strings.
    """
    start: int
    end: int
    font_family: str | None = None
    font_size: float | None = None
    font_weight: str | None = None
    color: object | None = None
    underline: bool = False
    background: object | None = None

    def __post_init__(self):
        if self.start < 0 or self.end <= self.start:
            raise ValueError("TextStyleSpan requires start >= 0 and end > start")
        if self.font_family is not None and not self.font_family:
            raise ValueError("font_family must be non-empty when provided")
        if self.font_size is not None and (not isfinite(float(self.font_size)) or self.font_size <= 0):
            raise ValueError("font_size must be finite and positive")
        if self.font_weight is not None and self.font_weight not in {"normal", "medium", "semibold", "bold"}:
            raise ValueError("unsupported font_weight")


@dataclass(frozen=True, slots=True)
class TextPaintRun:
    """One visual, styled run ready for native painting."""
    text: str
    start: int
    end: int
    x: float
    width: float
    color: object | None
    font_config: FontConfig
    glyph_runs: tuple[ShapedGlyphRun, ...] = ()
    underline: bool = False
    background: object | None = None


@dataclass(frozen=True, slots=True)
class ParagraphStyle:
    """Layout and marker styling for one paragraph.

    ``alignment="inherit"`` delegates horizontal alignment to the containing
    text node. Indents and spacing use logical pixels. A marker is painted once
    on the paragraph's first visual line and reserves ``marker_indent`` space.
    """

    alignment: str = "inherit"
    left_indent: float = 0.0
    right_indent: float = 0.0
    first_line_indent: float = 0.0
    space_before: float = 0.0
    space_after: float = 0.0
    line_spacing: float = 0.0
    line_height: float | None = None
    marker: str | None = None
    marker_color: object | None = None
    marker_indent: float = 20.0

    def __post_init__(self) -> None:
        if self.alignment not in {"inherit", "start", "center", "end"}:
            raise ValueError("Paragraph alignment must be inherit, start, center or end")
        numeric = ("left_indent", "right_indent", "first_line_indent",
                   "space_before", "space_after", "line_spacing", "marker_indent")
        for name in numeric:
            value = float(getattr(self, name))
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.line_height is not None and (not isfinite(float(self.line_height)) or self.line_height <= 0):
            raise ValueError("line_height must be finite and positive")
        if self.marker is not None and (not isinstance(self.marker, str) or not self.marker):
            raise ValueError("marker must be a non-empty string or None")

    @property
    def effective_left_indent(self) -> float:
        if self.marker is None:
            return self.left_indent
        return max(self.left_indent, self.marker_indent)


@dataclass(frozen=True, slots=True)
class TextParagraph:
    """Paragraph source range, line range and computed vertical geometry."""
    text: str
    start: int
    end: int
    first_line: int
    line_count: int
    top: float = 0.0
    height: float = 0.0
    style: ParagraphStyle = ParagraphStyle()


@dataclass(frozen=True, slots=True)
class TextCluster:
    """One grapheme/shaping cluster positioned in visual line order."""
    start: int
    end: int
    x: float
    width: float
    rtl: bool = False


@dataclass(frozen=True, slots=True)
class TextLine:
    text: str
    width: float
    baseline: float
    start: int = 0
    end: int = 0
    clusters: tuple[TextCluster, ...] = ()
    glyph_runs: tuple[ShapedGlyphRun, ...] = ()
    rtl: bool = False
    paragraph_index: int = 0
    last_in_paragraph: bool = True
    paint_runs: tuple[TextPaintRun, ...] = ()
    top: float = 0.0
    height: float = 0.0
    x_offset: float = 0.0
    alignment: str = "inherit"


@dataclass(frozen=True, slots=True)
class TextLayout:
    lines: tuple[TextLine, ...]
    width: float
    height: float
    ascent: float
    descent: float
    leading: float
    line_height: float
    paragraphs: tuple[TextParagraph, ...] = ()

    def caret_position(self, offset: int) -> tuple[float, float, int]:
        """Return (x, y, line-index) for a logical source offset."""
        if not self.lines:
            return 0.0, 0.0, 0
        offset = max(0, int(offset))
        chosen = len(self.lines) - 1
        for i, line in enumerate(self.lines):
            if line.start <= offset <= line.end:
                chosen = i
                break
            if offset < line.start:
                chosen = i
                break
        line = self.lines[chosen]
        if not line.clusters:
            x = line.width if line.rtl else 0.0
        elif offset <= line.start:
            x = line.width if line.rtl else 0.0
        elif offset >= line.end:
            x = 0.0 if line.rtl else line.width
        else:
            x = line.width
            for cluster in line.clusters:
                if offset == cluster.start:
                    x = cluster.x + (cluster.width if cluster.rtl else 0.0)
                    break
                if offset == cluster.end:
                    x = cluster.x + (0.0 if cluster.rtl else cluster.width)
                    break
                if cluster.start < offset < cluster.end:
                    x = cluster.x + (cluster.width if cluster.rtl else 0.0)
                    break
        return line.x_offset + x, line.top, chosen

    def offset_at(self, x: float, y: float) -> int:
        """Map visual text coordinates to the nearest logical cluster boundary."""
        if not self.lines:
            return 0
        line_index = min(
            range(len(self.lines)),
            key=lambda index: (
                0.0 if self.lines[index].top <= y <= self.lines[index].top + max(1.0, self.lines[index].height)
                else min(abs(y - self.lines[index].top),
                         abs(y - (self.lines[index].top + self.lines[index].height)))
            ),
        )
        line = self.lines[line_index]
        local_x = x - line.x_offset
        if not line.clusters:
            return line.start
        if local_x <= line.clusters[0].x:
            first = line.clusters[0]
            return first.end if first.rtl else first.start
        for cluster in line.clusters:
            midpoint = cluster.x + cluster.width / 2
            if local_x < midpoint:
                return cluster.end if cluster.rtl else cluster.start
            if local_x < cluster.x + cluster.width:
                return cluster.start if cluster.rtl else cluster.end
        last = line.clusters[-1]
        return last.start if last.rtl else last.end

    def selection_rects(self, start: int, end: int) -> tuple[tuple[float, float, float, float], ...]:
        """Return local (x, y, width, height) rectangles for selected clusters."""
        left, right = sorted((max(0, int(start)), max(0, int(end))))
        if left == right:
            return ()
        result = []
        for line in self.lines:
            selected = sorted(
                (c for c in line.clusters if c.end > left and c.start < right),
                key=lambda cluster: cluster.x,
            )
            if not selected:
                continue
            intervals: list[list[float]] = []
            for cluster in selected:
                start_x = cluster.x + line.x_offset
                end_x = start_x + cluster.width
                if intervals and start_x <= intervals[-1][1] + 0.5:
                    intervals[-1][1] = max(intervals[-1][1], end_x)
                else:
                    intervals.append([start_x, end_x])
            for x0, x1 in intervals:
                result.append((x0, line.top, max(0.0, x1 - x0),
                               line.height or self.line_height))
        return tuple(result)


class TextMeasurer:
    """Measure text using Skia's typeface metrics and cluster-aware geometry.

    The shaping boundary is deliberately explicit: ``measureText`` provides
    Skia font advances for the installed font, but this implementation does not
    promise full bidirectional or complex-script shaping. Applications can
    replace this service with a HarfBuzz/SkParagraph-backed implementation.
    """
    def __init__(self, skia_module: Any = None, font_resolver: FontResolver | None = None,
                 *, shaper: HarfBuzzShaper | None = None, base_direction: str = "auto",
                 font_configs: Mapping[str, FontConfig] | None = None,
                 line_break_provider=None):
        if base_direction not in {"auto", "ltr", "rtl"}:
            raise ValueError("base_direction must be 'auto', 'ltr' or 'rtl'")
        if font_configs is not None and not isinstance(font_configs, Mapping):
            raise TypeError("font_configs must be a mapping of family names to FontConfig values")
        normalized_configs = {}
        for family, config in (font_configs or {}).items():
            if not isinstance(family, str) or not family:
                raise ValueError("font_configs keys must be non-empty family names")
            if not isinstance(config, FontConfig):
                raise TypeError(f"font_configs[{family!r}] must be a FontConfig")
            normalized_configs[family] = config
        self._skia = skia_module
        self._resolver = font_resolver or FontResolver(skia_module)
        self._shaper = shaper
        self._base_direction = base_direction
        self._font_configs = normalized_configs
        if line_break_provider is not None and not callable(line_break_provider):
            raise TypeError("line_break_provider must be callable or None")
        self._line_break_provider = line_break_provider

    def config_for(self, family: str, size: float, weight: str = "normal") -> FontConfig:
        """Resolve registered font resources while applying a node's style."""
        template = self._font_configs.get(family)
        if template is None:
            return FontConfig(family=family, size=size, weight=weight)
        return replace(template, family=family, size=size, weight=weight)

    @staticmethod
    def _normalize_style_spans(text: str, style_spans) -> tuple[TextStyleSpan, ...]:
        spans = tuple(style_spans or ())
        previous_end = 0
        boundaries = {0, len(text)}
        for start, end in grapheme_spans(text):
            boundaries.add(start)
            boundaries.add(end)
        for item in spans:
            if not isinstance(item, TextStyleSpan):
                raise TypeError("style_spans entries must be TextStyleSpan instances")
            if item.end > len(text):
                raise ValueError("TextStyleSpan end exceeds the source text length")
            if item.start < previous_end:
                raise ValueError("TextStyleSpan ranges must be sorted and non-overlapping")
            if item.start not in boundaries or item.end not in boundaries:
                raise ValueError(
                    "TextStyleSpan boundaries must not split a grapheme cluster"
                )
            previous_end = item.end
        return spans

    @staticmethod
    def _normalize_paragraph_styles(text: str, paragraph_styles) -> tuple[ParagraphStyle, ...]:
        styles = tuple(paragraph_styles or ())
        paragraph_count = text.count("\n") + 1
        if len(styles) > paragraph_count:
            raise ValueError("paragraph_styles cannot contain more entries than the paragraph count")
        if any(not isinstance(style, ParagraphStyle) for style in styles):
            raise TypeError("paragraph_styles entries must be ParagraphStyle instances")
        return styles

    def _segments(self, text: str, source_start: int, config: FontConfig,
                  style_spans: tuple[TextStyleSpan, ...]):
        """Yield text, source offset, font, foreground, underline and background."""
        source_end = source_start + len(text)
        cursor = source_start
        relevant = [span for span in style_spans
                    if span.end > source_start and span.start < source_end]
        for span in relevant:
            start = max(source_start, span.start)
            end = min(source_end, span.end)
            if cursor < start:
                yield text[cursor - source_start:start - source_start], cursor, config, None, False, None
            family = span.font_family or config.family
            template = self._font_configs.get(family)
            base_config = template if template is not None else (
                config if family == config.family else replace(config, family=family, font_path=None)
            )
            effective = replace(
                base_config, family=family,
                size=float(span.font_size or base_config.size),
                weight=span.font_weight or base_config.weight,
            )
            yield text[start - source_start:end - source_start], start, effective, span.color, span.underline, span.background
            cursor = end
        if cursor < source_end:
            yield text[cursor - source_start:], cursor, config, None, False, None
        if not relevant and not text:
            return

    def _measure_range(self, text: str, source_start: int, config: FontConfig,
                       style_spans: tuple[TextStyleSpan, ...], shape_cache: dict):
        width = 0.0
        for segment, offset, segment_config, _color, _underline, _background in self._segments(
                text, source_start, config, style_spans):
            if not segment:
                continue
            key = (segment, segment_config)
            shaped = None
            if self._shaper is not None:
                shaped = shape_cache.get(key)
                if shaped is None:
                    shaped = self._shaper.shape(
                        segment, segment_config, self._resolver,
                        base_direction=self._base_direction,
                    )
                    shape_cache[key] = shaped
            if shaped is not None:
                width += float(shaped.width)
            elif callable(getattr(self._resolver, "measure_text", None)):
                width += float(self._resolver.measure_text(segment_config, segment))
            else:
                width += float(self._font(segment_config).measureText(segment))
        return width

    def _module(self):
        if self._skia is None:
            try:
                from ..dependencies import ensure_skia_python
                ensure_skia_python()
                import skia
            except Exception as exc:
                raise RuntimeError(
                    "Yuktara UI could not prepare Skia Python (skia-python 144.1) "
                    "for text measurement. Check the network connection or disable "
                    "automatic setup with YUKTARA_UI_NO_AUTO_INSTALL=1."
                ) from exc
            self._skia = skia
            if self._resolver._skia is None:
                self._resolver = FontResolver(skia)
        return self._skia

    def _font(self, config: FontConfig):
        skia = self._module()
        typeface = self._resolver.resolve(config)
        return skia.Font(typeface, config.size)

    @staticmethod
    def _font_metrics(font):
        metrics = font.getMetrics()
        ascent = abs(float(getattr(metrics, "fAscent", 0.0)))
        descent = max(0.0, float(getattr(metrics, "fDescent", 0.0)))
        leading = max(0.0, float(getattr(metrics, "fLeading", 0.0)))
        if ascent + descent == 0:
            ascent = font.getSize() * 0.8
            descent = font.getSize() * 0.2
        return ascent, descent, leading

    def _break_after(self, left: str, right: str | None = None) -> bool:
        if right is None:
            return left.isspace() or left.endswith(("\u200b", "\u00ad", "-", "‐", "‑", "–", "/", "\\"))
        if self._line_break_provider is not None:
            return bool(self._line_break_provider(left, right))
        return can_break_between(left, right)

    def _wrap_paragraph(self, text: str, source_start: int, max_width: float | None,
                        measure, *, first_line_indent: float = 0.0):
        if text == "":
            return [("", source_start, source_start)]
        spans = grapheme_spans(text)
        if max_width is None or not isfinite(max_width):
            return [(text, source_start, source_start + len(text))]
        if max_width <= 0:
            return [(text[a:b], source_start + a, source_start + b) for a, b in spans]
        lines = []
        line_start = 0
        cursor = 0
        last_break = None
        emitted_lines = 0
        while cursor < len(spans):
            start_char = spans[line_start][0]
            end_char = spans[cursor][1]
            candidate = text[start_char:end_char]
            candidate_width = measure(candidate, source_start + start_char)
            line_limit = max(0.0, max_width - (first_line_indent if emitted_lines == 0 else 0.0))
            if cursor > line_start and candidate_width > line_limit:
                if (last_break is None and cursor < len(spans)
                        and is_nonbreaking_boundary(
                            text[spans[cursor - 1][0]:spans[cursor - 1][1]],
                            text[spans[cursor][0]:spans[cursor][1]],
                        )):
                    # Keep NBSP/WJ/ZWJ glue intact even when the resulting
                    # unbreakable sequence is wider than the available line.
                    cursor += 1
                    if cursor < len(spans):
                        left = text[spans[cursor - 1][0]:spans[cursor - 1][1]]
                        right = text[spans[cursor][0]:spans[cursor][1]]
                        if self._break_after(left, right):
                            last_break = cursor
                    continue
                split = last_break if last_break is not None and last_break > line_start else cursor
                emit_start = spans[line_start][0]
                emit_end = spans[split - 1][1]
                # Breakable spaces disappear at a soft wrap, while hard source
                # offsets remain intact for selection and caret navigation.
                while split > line_start and text[spans[split - 1][0]:spans[split - 1][1]].isspace():
                    emit_end = spans[split - 1][0]
                    split -= 1
                if split == line_start:
                    split = last_break if last_break is not None and last_break > line_start else cursor
                    emit_end = spans[split - 1][1]
                lines.append((text[emit_start:emit_end], source_start + emit_start,
                              source_start + emit_end))
                emitted_lines += 1
                line_start = split
                while line_start < len(spans) and text[spans[line_start][0]:spans[line_start][1]].isspace():
                    line_start += 1
                cursor = line_start
                last_break = None
                continue
            cursor += 1
            if cursor < len(spans):
                left = text[spans[cursor - 1][0]:spans[cursor - 1][1]]
                right = text[spans[cursor][0]:spans[cursor][1]]
                if self._break_after(left, right):
                    last_break = cursor
            # Oversized single graphemes are kept intact rather than looping.
            if cursor == line_start + 1 and candidate_width > line_limit:
                lines.append((candidate, source_start + start_char, source_start + end_char))
                emitted_lines += 1
                line_start = cursor
                last_break = None
        if line_start < len(spans):
            start_char = spans[line_start][0]
            end_char = spans[-1][1]
            lines.append((text[start_char:end_char], source_start + start_char,
                          source_start + end_char))
        return lines or [("", source_start, source_start)]

    def measure(self, text: str, config: FontConfig | None = None, *,
                max_width: float | None = None, wrap: bool = True,
                line_height: float | None = None, max_lines: int | None = None,
                style_spans=(), paragraph_styles: Sequence[ParagraphStyle] = ()) -> TextLayout:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        config = config or FontConfig()
        if max_width is not None and (not isfinite(max_width) or max_width < 0):
            raise ValueError("max_width must be finite and non-negative")
        if line_height is not None and (not isfinite(line_height) or line_height <= 0):
            raise ValueError("line_height must be finite and positive")
        if max_lines is not None and max_lines < 1:
            raise ValueError("max_lines must be at least 1")
        normalized_spans = self._normalize_style_spans(text, style_spans)
        normalized_paragraph_styles = self._normalize_paragraph_styles(text, paragraph_styles)
        font = self._font(config)
        metric_sets = [self._font_metrics(font)]
        for span in normalized_spans:
            family = span.font_family or config.family
            template = self._font_configs.get(family)
            base_config = template if template is not None else (
                config if family == config.family else replace(config, family=family, font_path=None)
            )
            effective = replace(
                base_config, family=family,
                size=float(span.font_size or base_config.size),
                weight=span.font_weight or base_config.weight,
            )
            metric_sets.append(self._font_metrics(self._font(effective)))
        ascent = max(metrics[0] for metrics in metric_sets)
        descent = max(metrics[1] for metrics in metric_sets)
        leading = max(metrics[2] for metrics in metric_sets)
        natural = ascent + descent + leading
        actual_line_height = float(line_height or natural)
        shaped_cache: dict[Any, Any] = {}

        def measure(value: str, source_offset: int) -> float:
            return self._measure_range(value, source_offset, config, normalized_spans, shaped_cache)

        paragraphs = []
        source_start = 0
        for index, char in enumerate(text):
            if char == "\n":
                paragraphs.append((text[source_start:index], source_start, index))
                source_start = index + 1
        paragraphs.append((text[source_start:], source_start, len(text)))

        lines = []
        paragraph_layouts = []
        cursor_y = 0.0
        for paragraph_index, (paragraph_text, paragraph_start, paragraph_end) in enumerate(paragraphs):
            style = (normalized_paragraph_styles[paragraph_index]
                     if paragraph_index < len(normalized_paragraph_styles)
                     else ParagraphStyle())
            first_line_index = len(lines)
            cursor_y += style.space_before
            paragraph_top = cursor_y
            left_indent = style.effective_left_indent
            available_width = (None if max_width is None else
                               max(0.0, max_width - left_indent - style.right_indent))
            if wrap:
                raw_lines = self._wrap_paragraph(
                    paragraph_text, paragraph_start, available_width, measure,
                    first_line_indent=style.first_line_indent,
                )
            else:
                raw_lines = [(paragraph_text, paragraph_start, paragraph_end)]
            paragraph_line_height = style.line_height or actual_line_height
            effective_line_height = paragraph_line_height + style.line_spacing
            for local_line_index, (line_text, line_start, line_end) in enumerate(raw_lines):
                clusters: list[TextCluster] = []
                paint_runs: list[TextPaintRun] = []
                x_offset = 0.0
                line_rtl = self._base_direction == "rtl" or (
                    self._base_direction == "auto"
                    and HarfBuzzShaper._base_direction(line_text) == "rtl"
                )
                line_glyph_runs: list[ShapedGlyphRun] = []
                for segment, segment_start, segment_config, segment_color, underline, background in self._segments(
                        line_text, line_start, config, normalized_spans):
                    if not segment:
                        continue
                    shaped = None
                    if self._shaper is not None:
                        key = (segment, segment_config)
                        shaped = shaped_cache.get(key)
                        if shaped is None:
                            shaped = self._shaper.shape(
                                segment, segment_config, self._resolver,
                                base_direction=self._base_direction,
                            )
                            shaped_cache[key] = shaped
                    if shaped is not None:
                        segment_clusters = tuple(TextCluster(
                            item.start + segment_start,
                            item.end + segment_start,
                            item.x + x_offset, item.width, item.rtl,
                        ) for item in shaped.clusters)
                        segment_glyphs = tuple(replace(
                            run,
                            start=run.start + segment_start,
                            end=run.end + segment_start,
                            positions=tuple((x + x_offset, y) for x, y in run.positions),
                            clusters=tuple(replace(
                                item, start=item.start + segment_start,
                                end=item.end + segment_start, x=item.x + x_offset,
                            ) for item in run.clusters),
                        ) for run in shaped.runs)
                        segment_width = float(shaped.width)
                        clusters.extend(segment_clusters)
                        line_glyph_runs.extend(segment_glyphs)
                        paint_runs.append(TextPaintRun(
                            segment, segment_start, segment_start + len(segment),
                            x_offset, segment_width, segment_color, segment_config,
                            segment_glyphs, underline, background,
                        ))
                    else:
                        segment_spans = grapheme_spans(segment)
                        segment_clusters = []
                        previous_advance = 0.0
                        for local_start, local_end in segment_spans:
                            piece = segment[:local_end]
                            piece_width = (float(self._resolver.measure_text(segment_config, piece))
                                           if callable(getattr(self._resolver, "measure_text", None))
                                           else float(self._font(segment_config).measureText(piece)))
                            cluster_width = max(0.0, piece_width - previous_advance)
                            segment_clusters.append(TextCluster(
                                segment_start + local_start, segment_start + local_end,
                                x_offset + previous_advance, cluster_width,
                            ))
                            previous_advance = piece_width
                        segment_width = (float(self._resolver.measure_text(segment_config, segment))
                                         if callable(getattr(self._resolver, "measure_text", None))
                                         else float(self._font(segment_config).measureText(segment)))
                        clusters.extend(segment_clusters)
                        paint_runs.append(TextPaintRun(
                            segment, segment_start, segment_start + len(segment),
                            x_offset, segment_width, segment_color, segment_config,
                            (), underline, background,
                        ))
                    x_offset += segment_width
                clusters.sort(key=lambda item: item.x)
                first_indent = style.first_line_indent if local_line_index == 0 else 0.0
                line_offset = left_indent + first_indent
                align_width = (None if available_width is None else
                               max(0.0, available_width - first_indent))
                if align_width is not None:
                    if style.alignment == "center":
                        line_offset += max(0.0, (align_width - x_offset) / 2.0)
                    elif style.alignment == "end":
                        line_offset += max(0.0, align_width - x_offset)
                line_top = cursor_y
                line_index = len(lines)
                is_last = local_line_index == len(raw_lines) - 1
                lines.append(TextLine(
                    line_text, x_offset, line_top + ascent,
                    line_start, line_end, tuple(clusters), tuple(line_glyph_runs), line_rtl,
                    paragraph_index, is_last, tuple(paint_runs),
                    line_top, effective_line_height, line_offset, style.alignment,
                ))
                cursor_y += effective_line_height
            paragraph_height = cursor_y - paragraph_top
            paragraph_layouts.append(TextParagraph(
                paragraph_text, paragraph_start, paragraph_end,
                first_line_index, len(lines) - first_line_index,
                paragraph_top, paragraph_height, style,
            ))
            cursor_y += style.space_after
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            # Paragraph line ranges are clipped to the visible line limit.
            clipped = []
            for paragraph in paragraph_layouts:
                count = max(0, min(paragraph.line_count, max_lines - paragraph.first_line))
                if count:
                    last_line = lines[paragraph.first_line + count - 1]
                    clipped.append(replace(
                        paragraph, line_count=count,
                        height=max(0.0, last_line.top + last_line.height - paragraph.top),
                    ))
            paragraph_layouts = clipped
            if lines:
                last_line = lines[-1]
                cursor_y = last_line.top + last_line.height
        visible_widths = [line.x_offset + line.width for line in lines]
        return TextLayout(
            tuple(lines), max(visible_widths, default=0.0),
            max(actual_line_height, cursor_y),
            ascent, descent, leading, actual_line_height,
            tuple(paragraph_layouts),
        )

