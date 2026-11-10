# Native HarfBuzz text shaping — 2.7

## Design

Yuktara UI retains its dependency-free Skia measurement path. Applications can
opt into HarfBuzz using `HarfBuzzShaper` and `TextMeasurer(shaper=...)`. The
shaper returns positioned glyph IDs, logical source clusters, visual cluster
geometry and font-run metadata. The retained text layout uses those advances
for line wrapping and caret/selection hit geometry.

The renderer does not pass shaped strings back through `drawString`. It uses
Skia's `TextBlobBuilder.allocRunPos` to construct a glyph-positioned text blob,
then calls `Canvas.drawTextBlob`. Glyph IDs are valid only for the exact font
file used to shape the run; a mismatch between the HarfBuzz file and Skia
resolved typeface can produce incorrect glyphs. Configure matching font files
for both font selection and shaping.

## Dependencies

```bash
python -m pip install -e '.[native,shaping]'
```

`uharfbuzz` is an optional extra. It is not imported until an active
`HarfBuzzShaper` needs it. The default `TextMeasurer()` continues to use Skia
font advances without importing HarfBuzz.

## Font paths

`FontConfig.font_path` configures the primary family. `FontConfig.font_files`
is a tuple of `(family, path)` pairs for fallback faces. Every resolved family
used by a shaped run must have a corresponding explicit file mapping. The
resolver loads that same file into Skia, so glyph IDs are never drawn using a
system face selected only by family-name similarity. Missing files or invalid
font resources fail with an actionable error. The resolver does not guess font
paths using OS-specific search commands. The configured file must itself be the requested weight/slant; the resolver loads the file as-is rather than synthesizing bold or italic styling.

For component-tree text, register the resources by family on the measurer that
is passed into `NativeRuntime`:

```python
from novaui.native import FontConfig, HarfBuzzShaper, NativeRuntime, TextMeasurer

text_measurer = TextMeasurer(
    shaper=HarfBuzzShaper(),
    font_configs={
        "Inter": FontConfig(
            family="Inter",
            font_path="/fonts/Inter-Regular.ttf",
            font_files=(("Noto Sans Devanagari", "/fonts/NotoSansDevanagari-Regular.ttf"),),
        ),
    },
)
runtime = NativeRuntime(build, renderer, 1280, 800, text_measurer=text_measurer)
```

The layout engine derives the node's requested size and weight from its style,
while reusing the registered font paths and fallback map. Register a separate
entry for each primary family that needs an explicit face file.

## Direction behavior

`TextMeasurer(base_direction="auto" | "ltr" | "rtl")` selects the paragraph
base direction. The current adapter groups strong Unicode directional classes
into runs and shapes each run with HarfBuzz in its own direction. This is
sufficient for many single-direction paragraphs and basic mixed-script runs,
but it is not a complete UAX #9 implementation. Applications requiring
complex embeddings or isolate handling should inject a bidi engine before
production use.

## Caret and selection

HarfBuzz cluster indexes are mapped to Python source offsets. Ligatures may
span multiple code points, so current caret mapping treats the ligature as a
single indivisible cluster. GDEF caret tables, Unicode word/line break
algorithms, vertical writing and IME pre-edit composition are not implemented
in this release.
