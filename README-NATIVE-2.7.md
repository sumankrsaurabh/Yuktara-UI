# Yuktara UI Native 2.7.0.dev0

Yuktara UI 2.7 adds an optional HarfBuzz shaping path while keeping the base
framework dependency-free and retaining the SDL3 + Skia architecture.

## Included

- Optional `HarfBuzzShaper` backed by `uharfbuzz`.
- Explicit font-file mapping in `FontConfig.font_path` and
  `FontConfig.font_files`, matching HarfBuzz glyph IDs to the exact typeface.
- Glyph ID, offset and advance extraction from HarfBuzz shaping results.
- Ligature-aware cluster geometry, per-run direction metadata and shaped
  visual positions retained in `TextLayout`.
- HarfBuzz-shaped advances used during wrapping and intrinsic measurement.
- Skia `TextBlobBuilder.allocRunPos` + `Canvas.drawTextBlob` rendering for
  pre-shaped glyph runs. No browser or HTML text engine is introduced.
- Mixed strong-direction run grouping with automatic or explicit paragraph
  base direction (`auto`, `ltr`, `rtl`).
- Regression tests for ligatures, RTL cluster mapping, rendering dispatch,
  font-path validation and optional dependency guidance.

## Install the optional shaping extra

```bash
python -m pip install -e '.[native,shaping]'
```

HarfBuzz requires actual font files. The same files must be resolved by Skia
for glyph rendering. Configure the preferred font and any fallback families:

```python
from novaui.native import FontConfig, HarfBuzzShaper, TextMeasurer

config = FontConfig(
    family="Noto Sans Devanagari",
    size=22,
    fallback_families=(),
    font_path="/path/to/NotoSansDevanagari-Regular.ttf",
)
measurer = TextMeasurer(shaper=HarfBuzzShaper(), base_direction="auto")
layout = measurer.measure("नमस्ते भारत", config, wrap=False)
```

For multiple fallback typefaces, map every family the resolver may select:

```python
config = FontConfig(
    family="Inter",
    font_path="/fonts/Inter-Regular.ttf",
    font_files=(
        ("Noto Sans Devanagari", "/fonts/NotoSansDevanagari-Regular.ttf"),
        ("Noto Sans Arabic", "/fonts/NotoSansArabic-Regular.ttf"),
    ),
)
```

`font_path` and `font_files` are explicit resources. Skia loads the exact same
font file that HarfBuzz used to shape the glyph IDs; Yuktara UI does not
silently substitute a similarly named system face. A missing file or invalid
font raises a clear error. The file is used as-is, so point each family registration at the actual regular, medium, bold or italic font resource required by the UI. For component-tree text, register `FontConfig`
objects on `TextMeasurer(font_configs={...})` and pass that measurer into
`NativeRuntime(..., text_measurer=...)` so layout and painting share the
configured font resources.

## Scope and limitations

The backend supports HarfBuzz shaping and glyph-level drawing for configured
font files. It groups runs by strong Unicode direction and can choose an
`auto`, `ltr` or `rtl` base direction. This run grouping is not a full Unicode
Bidirectional Algorithm implementation: embeddings, isolates, neutrals and
complex mixed-script paragraph ordering still need a dedicated UAX #9 engine.

Caret and selection geometry is cluster-based. It correctly keeps a ligature
as one HarfBuzz cluster but does not yet calculate OpenType GDEF ligature
caret positions inside that ligature. Unicode line breaking, rich inline style
runs, full IME pre-edit composition and cross-platform desktop validation also
remain future work. The base Skia-only text path remains available when no
shaper is supplied.

Run the shaping inspection example with a local font:

```bash
python examples/native/harfbuzz_shaping.py ./font.ttf --family "Inter"
```

Run the native tests:

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```


## Validation for this development build

- 176 native tests pass with injected HarfBuzz/Skia test doubles.
- Python compile checks, wheel build, clean-target installation and package import checks pass.
- The build environment could not reach the package index, so `skia-python` and
  `uharfbuzz` could not be installed for a real-font raster integration run.
  Validate the optional shaping path on a machine with the native dependencies
  installed before using it for production text rendering.
