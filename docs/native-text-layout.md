# Native text measurement

Yuktara UI native text now has a Skia-backed measurement service. It resolves the configured typeface through the existing Inter-first `FontResolver`, reads real font ascent/descent/leading metrics, measures glyph runs, wraps paragraphs to a maximum width, and calculates per-line baselines.

## Usage

```python
from novaui.native.text import TextMeasurer
from novaui.native.layout import LayoutEngine, LayoutNode, Rect
from novaui.native.typography import FontConfig

measurer = TextMeasurer()
engine = LayoutEngine(text_measurer=measurer)
label = LayoutNode("text", text="A long line that wraps", font_size=16,
                   text_wrap=True, text_align="center")
engine.layout(label, Rect(0, 0, 240, 100))
```

The layout node supports `text_wrap`, `text_align` (`start`, `center`, `end`), `text_line_height`, and `text_max_lines`. `LayoutTreePainter` draws each measured line at its computed baseline. Inject a compatible Skia module into `TextMeasurer` for isolated tests.

## Boundaries

Wrapping currently uses whitespace word breaks and splits overlong words by Unicode code point. It does not yet implement grapheme-cluster segmentation, bidirectional shaping, complex-script shaping guarantees, inline spans, ellipsis, selection, caret geometry, font caching, or platform-specific fallback-run segmentation. Actual Skia integration must be validated against the target `skia-python` version and fonts installed/bundled by the app.
