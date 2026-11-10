# Native paragraphs and rich text (2.8)

Yuktara UI 2.8 extends the native text path with paragraph metadata, improved
Unicode line-break opportunities and source-indexed inline style spans. The
implementation continues to use the retained `LayoutNode` tree and the SDL3 +
Skia renderer. It does not introduce a browser, DOM, HTML or CSS text engine.

## RichText widget

Use `RichText` when one text node needs several visual styles:

```python
from novaui.native import RichText, TextStyleSpan

message = "Yuktara UI supports native rich text."
start = message.index("native")
end = start + len("native")

body = RichText(
    message,
    size=16,
    spans=(
        TextStyleSpan(
            start, end,
            font_weight="semibold",
            color=0xFF6750A4,
            background=0x1F6750A4,
            underline=True,
        ),
    ),
)
```

`RichText.build()` creates a normal text `LayoutNode`; it is not a separate
renderer or platform widget. The same style API is available directly through
`LayoutNode(text_style_spans=(...))`.

### TextStyleSpan

`TextStyleSpan(start, end, ...)` uses Python string/code-point offsets into the
original source string. The fields `font_family`, `font_size`, `font_weight`,
`color`, `background` and `underline` are optional. Unspecified fields inherit
the paragraph's base style.

Spans must be sorted, non-overlapping, within the source text, and must begin
and end at grapheme boundaries. This prevents a style boundary from splitting
a combining sequence, emoji ZWJ sequence or a grapheme cluster used by the text
editor. Source offsets remain stable through line wrapping.

The painter renders per-span text with the configured native font and paints
optional backgrounds and underlines. When HarfBuzz is enabled, each style span
is shaped using its effective font configuration. Register alternate font
families in `TextMeasurer(font_configs={...})` when an inline span changes the
font family.

## Paragraph metadata

`TextMeasurer.measure()` returns a `TextLayout`. Its `paragraphs` property is a
tuple of `TextParagraph` records containing:

- `text`, `start` and `end`: the original paragraph source range (the hard
  newline itself is outside the range).
- `first_line` and `line_count`: the paragraph's range in `TextLayout.lines`.

Trailing newlines and empty paragraphs are retained. `TextLine` also exposes
`paragraph_index` and `last_in_paragraph`, allowing a higher-level paragraph
formatter to distinguish wrapped lines from paragraph endings.

Selection geometry is generated per visual interval. A logical selection that
crosses discontiguous visual runs can therefore produce multiple rectangles
instead of one incorrect rectangle across unrelated text.


## Paragraph formatting (2.9)

`ParagraphStyle` configures individual paragraphs in a `RichText` node or
directly on a `LayoutNode` through `text_paragraph_styles`. One style entry maps
to one paragraph, in source order; omitted entries use the default style.

```python
from novaui.native import ParagraphStyle, RichText

body = RichText(
    "A centered heading\n"
    "A body paragraph with a first-line indent and extra spacing.\n"
    "A list item with a native marker.",
    size=16,
    paragraph_styles=(
        ParagraphStyle(alignment="center", line_height=24, space_after=12),
        ParagraphStyle(
            alignment="start", left_indent=12, first_line_indent=18,
            line_spacing=2, space_after=10,
        ),
        ParagraphStyle(marker="•", marker_indent=22),
    ),
)
```

Supported properties are `alignment` (`inherit`, `start`, `center`, `end`),
`left_indent`, `right_indent`, `first_line_indent`, `space_before`,
`space_after`, additive `line_spacing`, optional `line_height`, `marker`,
`marker_color` and `marker_indent`. A marker is painted only on the first visual
line and reserves a hanging indent for wrapped lines.

Paragraph styles update actual line geometry. Caret placement, pointer-to-offset
mapping, selection rectangles, text clipping and painting all use each line's
computed top, height and horizontal offset. Existing `RichText(text, spans,
size, ...)` positional arguments remain compatible; `paragraph_styles` is an
additional optional keyword.

Full justification and tab-stop leader layout are not included in this release.

## Unicode line breaking

The built-in line breaker is a dependency-free, UAX #14-informed subset. It
supports ordinary spaces and tabs, zero-width spaces, soft hyphens, common
hyphens and slashes, CJK ideographic boundaries, and common opening/closing
punctuation constraints. It keeps non-breaking spaces, narrow non-breaking
spaces, non-breaking hyphens, word joiners and ZWJ sequences glued together.

A project can inject a locale-specific provider:

```python
from novaui.native import TextMeasurer


def can_break(left_grapheme: str, right_grapheme: str) -> bool:
    # Return True when the line may break between these adjacent clusters.
    return left_grapheme.isspace() or right_grapheme.startswith("漢")

measurer = TextMeasurer(line_break_provider=can_break)
```

`line_break_offsets(text, grapheme_spans)` exposes the default logical break
positions for applications that need to inspect them.

## Limitations

This is not a complete Unicode Line Breaking Algorithm implementation. Thai,
Khmer and other dictionary-based segmentation, locale tailoring, automatic
hyphenation and every UAX #14 pair rule are not included. The default line
breaker intentionally prioritizes preserving words and grapheme clusters over
forcing every line to fit; a single unbreakable sequence may overflow its line.

Likewise, mixed-direction text still uses the earlier directional-run
heuristics rather than a complete Unicode Bidirectional Algorithm (UAX #9).
Rich style boundaries can create separate shaping runs and may affect ligature
formation across a style boundary. Production-grade document composition still
needs a full bidi engine, OpenType caret data, IME pre-edit composition and
real-font cross-platform validation.

## Verification

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```

The tests inject Skia and shaping-compatible backends where possible. They do
not replace real desktop verification with SDL3, Skia and installed fonts.
