# Yuktara UI Native 2.9.0.dev0

Yuktara UI 2.9 extends the paragraph-aware text system with document-style
paragraph formatting while preserving the native SDL3 + Skia architecture and
the historical `novaui` Python import namespace.

## Included

- `ParagraphStyle` for per-paragraph start/center/end/inherited alignment.
- Left/right indentation and first-line indentation with paragraph-aware line
  wrapping.
- Paragraph space before/after, additive line spacing and line-height overrides.
- Native list markers painted once per paragraph with configurable marker color
  and a hanging indent for wrapped lines.
- Paragraph-specific visual geometry used consistently by text painting, caret
  placement, hit testing, selection rectangles and scroll-to-caret logic.
- `RichText(paragraph_styles=...)` integration with positional compatibility
  retained for the earlier `text, spans, size, ...` constructor shape.

## Quick example

```python
from novaui.native import ParagraphStyle, RichText

content = RichText(
    "Centered heading\nBody copy with an indent.\nA list item.",
    size=16,
    paragraph_styles=(
        ParagraphStyle(alignment="center", line_height=24, space_after=10),
        ParagraphStyle(left_indent=12, first_line_indent=18, space_after=8),
        ParagraphStyle(marker="•", marker_indent=22),
    ),
)
```

## Verification

- Full native test suite and compile checks are run for the release archive.
- The suite uses backend-injected test renderers; real SDL3 + Skia desktop
  rendering and platform accessibility still require separate OS validation.

## Known limits

- Full justification and tab-stop leader layout are not implemented.
- The built-in line-breaker remains a UAX #14-informed subset; complete UAX #9
  bidi processing, dictionary segmentation and IME composition remain future work.
- The optional HarfBuzz/Skia real-font path needs an installed desktop runtime
  verification pass.
