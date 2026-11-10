# Python-first library reuse strategy

Yuktara is a Python framework. Application developers write Python only; no
HTML, CSS, JavaScript, C++ or Rust application code is part of the supported
developer experience. A dependency may contain optimized native code behind a
Python API, but it must have reliable Python packaging for our supported
platforms and must not force Yuktara maintainers to maintain a second UI
runtime.

## Adopted foundations

| Area | Library | Status | Yuktara ownership |
|---|---|---|---|
| Window, input, display | SDL3 through the Python ctypes adapter | Adopted | Python host adapter, events, lifecycle and platform policy |
| 2D rendering | skia-python | Adopted | Python renderer, paint dispatch and retained-tree painter |
| Text shaping | uharfbuzz | Optional shaping extra | Python shaping adapter, source offsets and Skia glyph painting |
| Grapheme segmentation | regex (Unicode \X) | Optional unicode extra; used automatically when installed | Python fallback, source-index mapping and editing behavior |
| Unit/integration tests | pytest | Development dependency | Test architecture and fixtures |

Install the optional text capabilities:

```bash
python -m pip install 'yuktara-ui[unicode]'
python -m pip install 'yuktara-ui[shaping]'
```

The base installation remains usable without these optional packages. When
regex is absent, Yuktara uses its dependency-free grapheme fallback.

## Candidates to integrate when the matching feature is implemented

| Python package | Potential use | Decision |
|---|---|---|
| python-bidi | Unicode Bidirectional Algorithm for mixed RTL/LTR paragraphs | Evaluate for source-index-preserving visual ordering before adopting |
| fonttools | Font metadata, cmap coverage, variable-font inspection and subsetting | Evaluate for typography tooling and font diagnostics |
| mistune | Markdown parsing into a structured Python AST | Adopt for a future Markdown/document import adapter if the AST maps cleanly to Yuktara RichText |
| Pygments | Python-side syntax tokenization and highlighting | Adopt for code-editor/document code blocks; keep painting in Skia |
| platformdirs | Cross-platform cache/config/data directories | Evaluate against the current small, tested cache-path implementation |
| hypothesis | Property-based tests for layout, Unicode editing and geometry | Development-only dependency; use to expand regression coverage |

These are candidates, not runtime dependencies. Each integration needs a
focused adapter, a supported-version range, license review, wheel/platform
checks and tests. Do not add a package merely because it is popular.

## Deliberately not used as the application UI backend

- Qt/PySide, Kivy, Toga and Dear PyGui: each introduces another widget and
  rendering architecture instead of supplying a focused SDL3/Skia building
  block.
- Dear ImGui and RmlUi: useful references or possible isolated developer tools,
  but their primary UI runtimes and renderer integrations do not match
  Yuktara's retained Python/Skia component model.
- Yoga: a possible Flexbox implementation, but it overlaps with the current
  Yuktara layout engine and introduces a native binding boundary. Do not replace
  the current engine until a measured compatibility/performance study proves
  the migration is worthwhile.
- Pillow: Skia already decodes the image formats needed by the current renderer;
  add Pillow only if a concrete image-processing feature requires it.
- CairoSVG: avoid adding a second graphics stack when SVG can be handled by the
  Skia SVG APIs exposed by the installed binding.

## Integration acceptance checklist

A dependency can be adopted only when all applicable checks pass:

1. A maintained Python package/API exists and supports Python 3.10+.
2. Windows, macOS and Linux installation paths are documented and tested.
3. The license is compatible with Yuktara's distribution model.
4. It removes meaningful custom code or closes a known correctness gap.
5. It does not introduce a competing widget tree, event loop or renderer.
6. Yuktara keeps stable Python-facing interfaces and can fall back gracefully
   when the dependency is optional.
7. Tests cover behavior at the adapter boundary, including failures and version
   mismatches.

## Development rule

Before implementing a new subsystem, search for a focused Python library first.
Reuse it behind a Yuktara adapter when it is a good fit. Keep Yuktara's public
component API, themes, layout composition, state model, accessibility semantics
and visual identity under Yuktara's control.
