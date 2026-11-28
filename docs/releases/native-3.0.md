# Yuktara UI Native 3.0.0.dev0

Yuktara UI 3.0 introduces a native document page composition subsystem on top of
the existing SDL3 + Skia retained UI and paragraph-aware text engine.

## Included

- A4 portrait defaults and configurable `PageSize` / `PageMargins`.
- `DocumentParagraph` blocks that retain existing font configuration, inline
  rich-text spans and paragraph styles.
- Explicit `PageBreak()` blocks.
- Fixed-page pagination with source-preserving paragraph fragments.
- `keep_together`, `keep_with_next`, `widow_lines` and `orphan_lines` controls.
- Left, center and right page headers and footers.
- `{page}` and `{pages}` placeholders resolved after total page count is known.
- `DocumentLayout.paint_page()` for native Skia or compatible recording renderers.
- A raster A4 sample in `examples/native/document_pagination.py`.

## Quick start

```python
from novaui.native import (
    DocumentParagraph, DocumentPaginator, PageMargins, PageSize,
    PageTemplate, ParagraphStyle, TextMeasurer,
)

layout = DocumentPaginator(TextMeasurer()).paginate(
    [
        DocumentParagraph(
            "Report title",
            style=ParagraphStyle(alignment="center", space_after=18),
            keep_with_next=True,
        ),
        DocumentParagraph("First paragraph of the report."),
    ],
    page_size=PageSize(),
    margins=PageMargins(72, 72, 72, 72),
    template=PageTemplate(
        header_left="Yuktara UI",
        footer_right="Page {page} of {pages}",
    ),
)
print(f"Pages: {layout.page_count}")
```

To paint a page through Skia:

```python
layout.paint_page(renderer, 0)
```

## Verification

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```

The page and paragraph algorithms have backend-injected tests. Real-font
rendering, OS printing and PDF export are not included in this milestone.

## Known limits

Full justification, tab-stop leaders, tables, floating images, footnotes,
section breaks, multi-column flow, complete Unicode bidi and advanced print
composition remain future work. `paint_page()` is a raster preview API, not a
PDF exporter.
