"""Optional Pygments adapter for native Skia-rendered code text."""

from __future__ import annotations

from dataclasses import dataclass

from .measure import TextStyleSpan, grapheme_spans


@dataclass(frozen=True, slots=True)
class SyntaxPalette:
    """ARGB syntax colors; painting remains owned by Yuktara and Skia."""

    keyword: int = 0xFFC586C0
    function: int = 0xFF82AAFF
    class_name: int = 0xFF4EC9B0
    builtin: int = 0xFF4FC1FF
    string: int = 0xFFCE9178
    number: int = 0xFFB5CEA8
    comment: int = 0xFF7F848E
    operator: int = 0xFFD4D4D4
    error: int = 0xFFF44747


DEFAULT_SYNTAX_PALETTE = SyntaxPalette()


def _token_color(token, palette: SyntaxPalette):
    from pygments.token import Token

    if token in Token.Comment:
        return palette.comment
    if token in Token.Keyword:
        return palette.keyword
    if token in Token.Name.Function:
        return palette.function
    if token in Token.Name.Class:
        return palette.class_name
    if token in Token.Name.Builtin:
        return palette.builtin
    if token in Token.String:
        return palette.string
    if token in Token.Number:
        return palette.number
    if token in Token.Operator:
        return palette.operator
    if token in Token.Error:
        return palette.error
    return None


def highlight_code(
    source: str,
    language: str = "python",
    *,
    palette: SyntaxPalette = DEFAULT_SYNTAX_PALETTE,
) -> tuple[TextStyleSpan, ...]:
    """Return source-indexed syntax spans suitable for Yuktara RichText.

    Pygments performs lexical analysis only. Yuktara retains the source string,
    grapheme-safe offsets, component model and Skia painting. The optional
    dependency is loaded only when this function is called.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(language, str) or not language.strip():
        raise ValueError("language must be a non-empty lexer alias")
    if not isinstance(palette, SyntaxPalette):
        raise TypeError("palette must be a SyntaxPalette")
    if not source:
        return ()

    try:
        from pygments.lexers import get_lexer_by_name
        from pygments.util import ClassNotFound
    except ImportError as exc:
        raise RuntimeError(
            "Syntax highlighting requires Pygments. "
            "Install it with: pip install 'yuktara-ui[syntax]'"
        ) from exc

    try:
        lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
    except ClassNotFound as exc:
        raise ValueError(f"Unknown syntax highlighting language: {language}") from exc

    token_ranges = []
    cursor = 0
    for offset, token_type, value in lexer.get_tokens_unprocessed(source):
        if not value:
            continue
        if offset != cursor:
            raise RuntimeError(
                "The selected Pygments lexer returned non-contiguous source offsets"
            )
        end = offset + len(value)
        token_ranges.append((offset, end, _token_color(token_type, palette)))
        cursor = end
    if cursor != len(source):
        raise RuntimeError(
            "The selected Pygments lexer did not preserve the complete source text"
        )

    # Tokenizers may split a combining sequence across token types. Assign one
    # color per extended grapheme so TextStyleSpan never splits an edit cluster.
    result: list[TextStyleSpan] = []
    token_index = 0
    for start, end in grapheme_spans(source):
        while token_index < len(token_ranges) and token_ranges[token_index][1] <= start:
            token_index += 1
        color = None
        if token_index < len(token_ranges):
            token_start, token_end, token_color = token_ranges[token_index]
            if token_start <= start < token_end:
                color = token_color
        if color is None:
            continue
        if result and result[-1].end == start and result[-1].color == color:
            previous = result[-1]
            result[-1] = TextStyleSpan(previous.start, end, color=color)
        else:
            result.append(TextStyleSpan(start, end, color=color))
    return tuple(result)


__all__ = ["DEFAULT_SYNTAX_PALETTE", "SyntaxPalette", "highlight_code"]
