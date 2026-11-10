# Native text and typography — 2.6

Yuktara UI 2.6 upgrades the native text pipeline with glyph-aware font fallback,
cluster-based line geometry, measured caret placement, selection painting,
text-field scrolling and SDL3 system clipboard access. It remains a retained
Python UI tree rendered by Skia and hosted by SDL3; it does not add a browser
or web rendering stack.

## Typography and fallback

`FontConfig` keeps Inter as the preferred family and now includes fallback
families for Noto Sans script variants, CJK, emoji, Arial and DejaVu Sans.
`FontResolver.resolve_runs(config, text)` splits a string into contiguous
`FontRun` items. When the active Skia binding exposes
`Typeface.unicharToGlyph`, the resolver selects a family that contains each
cluster; otherwise it deterministically uses the first available typeface.

`SkiaRenderer.draw_text` draws the resolved runs in order. A real
`SkiaRenderer` also receives a `TextMeasurer` automatically through
`NativeRuntime`, so text measurement, line wrapping, alignment, pointer hit
mapping and painting share the same typeface metrics. A custom renderer can
inject its own `TextMeasurer`:

```python
from novaui.native import NativeRuntime, TextMeasurer

runtime = NativeRuntime(
    build, renderer, 900, 640,
    text_measurer=TextMeasurer(),
)
```

## Cluster-aware text layout

`TextMeasurer` exposes `TextLayout`, `TextLine` and `TextCluster` geometry.
Lines retain absolute source offsets. Layout helpers provide:

- `caret_position(offset)` — local x/y and line index.
- `offset_at(x, y)` — nearest insertion boundary for a pointer position.
- `selection_rects(start, end)` — line-specific native selection rectangles.

Grapheme segmentation uses the optional `regex` package's Unicode `\X`
extended-grapheme implementation when installed. Add it with
`python -m pip install 'yuktara-ui[unicode]'`. The base installation retains a
dependency-free fallback for combining marks, emoji variation/modifier
sequences, ZWJ emoji, regional-indicator flags and common Indic virama
conjuncts. For production multilingual editing, install the `unicode` or
`shaping` extra so keyboard movement, deletion and selection use a maintained
Unicode grapheme segmenter.

Word wrapping preserves source offsets and trailing empty lines. It currently
uses simple whitespace and hyphen break opportunities; full Unicode line
breaking, soft hyphen handling, ellipsis, rich inline spans and paragraph style
runs are not included.

## Syntax highlighting

Install the optional Pygments adapter:

```bash
python -m pip install 'yuktara-ui[syntax]'
```

Pygments tokenizes source code; Yuktara maps tokens to grapheme-safe
`TextStyleSpan` ranges and keeps all painting in Skia:

```python
from novaui.native import RichText, highlight_code

source = "def greet(name):\\n    return 'hello'\\n"
editor_preview = RichText(source, spans=highlight_code(source, "python"))
```

The lexer alias is supplied by Pygments (for example, `python`, `json`,
`javascript` or `bash`). The package is loaded lazily, so applications that
do not use syntax highlighting do not need it installed. The default palette
can be replaced with `SyntaxPalette`.

## Markdown import

Install the optional Mistune adapter:

```bash
python -m pip install 'yuktara-ui[markdown]'
```

Parse Markdown into plain source text, source-indexed native style spans,
paragraph layout styles and link ranges:

```python
from novaui.native import parse_markdown

document = parse_markdown("# Notes\\n\\nA **native** paragraph with [a link](https://example.com).")
widget = document.to_rich_text(size=16)
# document.links retains URL targets and source offsets for app-owned actions.
```

The adapter supports headings, paragraphs, ordered/unordered lists, block
quotes, code blocks, code spans, strong text, emphasis, links and image alt
text. Emphasis is currently represented as underline because the native text
style model does not yet expose italic. Links are metadata, not automatic
navigation: the application decides whether and how to open them. Parsing does
not add HTML, CSS or a browser renderer.

## Text input, selection and clipboard

`TextField` and `TextArea` now paint the caret and selection separately from the
text string. This avoids inserting a synthetic cursor glyph into document
content. When a `TextMeasurer` is present, pointer placement and selection use
measured cluster advances. Text inputs clip to their content area and keep the
caret visible while horizontally or vertically scrolling.

Keyboard editing includes grapheme-safe Backspace/Delete, Left/Right movement,
Shift selection, Home/End, multiline Up/Down, Ctrl+A and Ctrl+Left/Right word
navigation. Cut/copy/paste use an optional clipboard service implementing
`get_text()` and `set_text()`:

```python
from novaui.native import TextField
from novaui.native.platform import SDL3Window

window = SDL3Window("Editor", 900, 640).open()
field = TextField("Select and edit this text", clipboard=window, text_input=window)
# Ctrl+C / Ctrl+X / Ctrl+V now use the operating-system clipboard.
```

`SDL3Window.get_text()` and `SDL3Window.set_text(text)` are aliases suitable
for the text-field service contract. They require an open SDL3 window and must
be called on the thread that opened it. Clipboard text is UTF-8. The SDL3
adapter rejects non-string values and embedded NUL characters.

## Host and platform responsibilities

When the supplied clipboard service is an `SDL3Window`, focusing a text
control calls `SDL_StartTextInput` and blurring it calls `SDL_StopTextInput`.
SDL3 delivers committed text input and provides clipboard access. The host
still owns input-method composition/pre-edit, candidate-window placement and
focus policy. The current control does not render IME pre-edit text or expose
platform-specific text-input rectangles.

The text pipeline uses Skia font advances and fallback font runs; it is not a
full HarfBuzz or SkParagraph shaping implementation. Bidirectional reordering,
Arabic joining, complete Indic shaping, ligature-aware caret geometry and
complex-script line breaking require a shaping backend. OS accessibility
providers also remain separate adapters. Validate fonts, clipboard permissions,
IME composition and assistive technology on each supported operating system.

## Example

Run the native text editor gallery:

```bash
python examples/native/text_editor_gallery.py
```

Run tests and compilation:

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```
