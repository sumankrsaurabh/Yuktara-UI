# Yuktara UI Native 2.8.0.dev0

Yuktara UI 2.8 adds native paragraph layout and rich inline text styling while
retaining the SDL3 + Skia architecture and the historical `novaui` import
namespace.

## Included

- `RichText` widget for source-indexed inline font, size, weight, color,
  background and underline spans.
- `TextStyleSpan` range validation: sorted, non-overlapping, within-source and
  grapheme-boundary-safe.
- Paragraph source metadata through `TextParagraph`, including original
  offsets, first line and line count.
- Better UAX #14-informed line-break opportunities for spaces, tabs, CJK,
  soft/zero-width break characters, common hyphens, slashes and punctuation.
- Preservation of non-breaking spaces, narrow no-break spaces, non-breaking
  hyphens, word joiners and ZWJ glue even when an unbreakable run overflows.
- Per-inline-run font metrics, Skia painting, backgrounds and underlines.
- Discontiguous visual selection rectangles for mixed visual runs.
- Injectable locale-specific line-break policy through
  `TextMeasurer(line_break_provider=...)`.
- Public helpers `line_break_offsets` and `can_break_between`.

## Quick example

```python
from novaui.native import RichText, TextStyleSpan

text = "Build native interfaces with Yuktara UI."
start = text.index("Yuktara UI")
body = RichText(
    text,
    size=16,
    spans=(TextStyleSpan(
        start, start + len("Yuktara UI"),
        font_weight="bold", color=0xFF6750A4,
    ),),
)
```

## Validation

- 189 native tests pass.
- Python compile checks pass.
- The source package and wheel are built and import-tested.
- Test renderers are injected; a real Skia/HarfBuzz desktop integration run
  still needs to be performed on supported operating systems.

## Known limits

The built-in line breaker is not a complete UAX #14 implementation and does
not provide Thai/Khmer dictionary segmentation or automatic hyphenation. The
mixed-direction path is still a heuristic, not full UAX #9. Rich styling can
split shaping runs and affect ligatures across style boundaries. OpenType GDEF
caret integration, complete IME composition and real desktop font testing
remain future work.

See [`docs/native-text-paragraphs.md`](docs/native-text-paragraphs.md) for the
full API and current limitations.
