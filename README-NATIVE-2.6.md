# Yuktara UI Native 2.6.0.dev0

Yuktara UI 2.6 advances native typography, text layout and editing while
preserving the SDL3 + Skia architecture and the `novaui` compatibility import.

## Included

- Inter-first font resolution with per-grapheme fallback font runs across
  configured Noto Sans script families, CJK, emoji and system fallback families.
- Shared Skia-backed text measurement when `NativeRuntime` uses `SkiaRenderer`.
- `TextCluster`, `TextLine` and `TextLayout` geometry with source offsets,
  caret mapping and multi-line selection rectangles.
- Grapheme-aware cursor movement and deletion for combining marks, emoji
  modifiers, ZWJ sequences, flags and common Indic virama conjuncts.
- Native selection highlight and caret painting; text controls no longer inject
  a visual caret glyph into the underlying string.
- TextField/TextArea content clipping and scroll-to-caret behavior.
- SDL3-backed UTF-8 clipboard methods and Ctrl+C/Ctrl+X/Ctrl+V integration when
  a `TextField` or `TextArea` receives the SDL3 window as `clipboard`.
- Updated typography docs, text-editor gallery and regression tests.

## Quick usage

```python
from novaui.native import TextArea
from novaui.native.platform import SDL3Window

window = SDL3Window("Editor", 900, 640).open()
editor = TextArea(
    "Type here — नमस्ते — 👨‍👩‍👧‍👦",
    font_family="Inter",
    clipboard=window,
    width=720,
    height=220,
)
```

For a real `SkiaRenderer`, `NativeRuntime` automatically installs the matching
`TextMeasurer`. Custom renderers can pass a `TextMeasurer` explicitly.

## Known limitations

This is not yet a complete desktop publishing text engine. The segmenter covers
common grapheme cases but is not a full UAX #29 implementation. Font fallback
runs do not replace HarfBuzz/SkParagraph shaping: complete bidirectional text,
Arabic joining, Indic ligatures, advanced line breaking, IME pre-edit
composition and rich inline spans remain future work. The SDL3 clipboard
adapter and real font coverage still need end-to-end desktop validation on
Windows, Linux and macOS.

See [docs/native-text-editor.md](docs/native-text-editor.md) for API details.
