# Native document layout (3.0)

Yuktara UI 3.0 adds a page composition layer above the paragraph-aware text
engine. It is backend-neutral: pagination produces immutable page/fragment
models, and `DocumentLayout.paint_page()` paints a page using the native
renderer protocol. It does not depend on a browser, HTML, CSS or a web view.

## Basic document

```python
from novaui.native import (
    DocumentParagraph, DocumentPaginator, PageMargins, PageSize,
    PageTemplate, ParagraphStyle, TextMeasurer,
)

paginator = DocumentPaginator(TextMeasurer())
document = paginator.paginate(
    [
        DocumentParagraph(
            "A centered title",
            style=ParagraphStyle(alignment="center", space_after=18),
            keep_with_next=True,
        ),
        DocumentParagraph("A body paragraph with native line wrapping."),
    ],
    page_size=PageSize(),                 # A4 portrait, logical points
    margins=PageMargins(72, 72, 72, 72),
    template=PageTemplate(
        header_left="Yuktara UI",
        footer_right="Page {page} of {pages}",
    ),
)
print(document.page_count)
```

## Blocks and pagination rules

- `DocumentParagraph` represents one hard paragraph. Use a separate block for
each paragraph; embedded `\n` and `\r` are rejected so paragraph rules are
  explicit.
- `PageBreak()` inserts a hard page break. A leading break is ignored rather
  than creating a blank first page.
- `keep_together=True` moves a paragraph to the next page when the complete
  paragraph fits on a fresh page but not in the current remainder.
- `keep_with_next=True` groups the paragraph with subsequent blocks until the
  first block without that flag. The group moves together when it fits on a
  fresh page but not in the current remainder.
- `orphan_lines` sets the preferred minimum lines at the bottom of a paragraph's
  first fragment; `widow_lines` sets the preferred minimum lines at the top of
  its continuation. If the page is too small to satisfy the preference, the
  paginator makes progress and allows the paragraph to split.
- Existing `ParagraphStyle`, `TextStyleSpan` and `FontConfig` values are passed
  through to `TextMeasurer`, so indentation, list markers and rich text metrics
  participate in page composition.

## Headers and footers

`PageTemplate` provides left, center and right strings for both header and
footer. `{page}` and `{pages}` are substituted after pagination so the total
page count is known. Unknown placeholders are preserved literally. Header and
footer heights reserve vertical space above and below the body. Their font and
color can be configured independently of paragraph fonts.

## Painting

`DocumentLayout.paint_page(renderer, page_index, x=0, y=0)` paints a white page,
optional outline, header/footer text, paragraph lines, styled runs and list
markers. The renderer must provide `draw_rect()` and `draw_text()`; shaped runs
also require `draw_glyph_run()`. It can be used with `SkiaRenderer` or a
backend-injected recording renderer.

A raster A4 example is available:

```bash
python examples/native/document_pagination.py preview.png
```

## Current limits

This is a page-layout foundation, not a complete word processor or print/PDF
exporter. Full justification, tab-stop leaders, tables, floating images,
footnotes, section breaks, multi-column flow, automatic hyphenation, complete
Unicode bidi processing, and cross-platform desktop print validation remain
future work. Widow/orphan handling is a best-effort line-count constraint, not
a full publishing composition algorithm. The native Skia painter is a raster
page preview; a PDF backend can consume the page models later.

## Verification

```bash
python -m pytest -q tests/native
python -m compileall -q novaui examples/native
```

The test suite uses backend-injected measurement and rendering doubles. It does
not certify installed-font rendering, SDL3 desktop integration or OS print
subsystems.
