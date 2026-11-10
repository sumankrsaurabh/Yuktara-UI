"""Dependency-free Unicode-aware line-break opportunities.

This module implements a conservative subset of UAX #14 suitable for the
base runtime: spaces, tabs, explicit zero-width break characters, hyphens,
slashes, CJK ideographs, and opening/closing punctuation. It deliberately
keeps non-breaking spaces, word joiners and combining grapheme clusters intact.
For complete locale-specific line breaking, applications may inject a richer
line-break provider into :class:`TextMeasurer`.
"""
from __future__ import annotations

import unicodedata
from typing import Callable


_NON_BREAKING = {"\u00a0", "\u202f", "\u2011", "\u2060", "\ufeff"}
_OPENING = set("([{<\u2018\u201c\u3008\u300a\u300c\u300e\u3010\u3014\u3016\u3018\u301a\u301d\uff08\uff3b\uff5b\u3008\u300a\u300c\u300e\u3010")
_CLOSING = set(")]}>,.!?:;\u2019\u201d\u3001\u3002\u3009\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b\uff09\uff3d\uff5d\u3009\u300b\u300d\u300f\u3011\uff0c\uff0e\uff01\uff1f\uff1b\uff1a\uff05")
_HYPHENS = {"-", "\u2010", "\u2012", "\u2013", "\u2014", "/", "\\"}


def _base(cluster: str) -> str:
    for char in cluster:
        category = unicodedata.category(char)
        if not category.startswith("M") and char not in {"\u200c", "\u200d"}:
            return char
    return cluster[:1]


def _is_ideographic(cluster: str) -> bool:
    char = _base(cluster)
    if not char:
        return False
    code = ord(char)
    return (
        unicodedata.east_asian_width(char) in {"W", "F"}
        and unicodedata.category(char) in {"Lo", "Nl"}
    ) or (
        0x1F000 <= code <= 0x1FAFF
        or 0x20000 <= code <= 0x3FFFF
    )


def _is_alphanumeric(cluster: str) -> bool:
    return any(unicodedata.category(ch)[0] in {"L", "N"} for ch in cluster)


def is_nonbreaking_boundary(left: str, right: str) -> bool:
    """Whether emergency wrapping must preserve a glued Unicode pair."""
    glued = {"\u00a0", "\u202f", "\u2011", "\u2060", "\ufeff", "\u200d"}
    return any(char in glued for char in left + right)


def can_break_between(left: str, right: str) -> bool:
    """Return whether a line may break between two grapheme clusters."""
    if not left or not right:
        return False
    if any(ch in _NON_BREAKING for ch in left + right):
        return False
    if "\u2060" in left or "\u2060" in right or "\ufeff" in left or "\ufeff" in right:
        return False
    if "\u200d" in left or "\u200d" in right:
        return False
    left_base = _base(left)
    right_base = _base(right)
    if left_base in _OPENING or right_base in _OPENING or right_base in _CLOSING:
        return False
    if left.endswith(("\u200b", "\u00ad")):
        return True
    if left.isspace():
        return True
    if left_base in _HYPHENS:
        return True
    if _is_ideographic(left) or _is_ideographic(right):
        # Keep punctuation attached to its conventional side while allowing
        # CJK runs and CJK/Latin boundaries to wrap naturally.
        return True
    # Avoid splitting alphabetic and numeric sequences at arbitrary points.
    if _is_alphanumeric(left) and _is_alphanumeric(right):
        return False
    # Break after selected sentence/closing punctuation when followed by text.
    if unicodedata.category(left_base).startswith("P"):
        return True
    return False


def line_break_offsets(text: str, grapheme_spans: Callable[[str], tuple[tuple[int, int], ...]]) -> tuple[int, ...]:
    """Return logical code-point offsets where a line break is permitted."""
    spans = grapheme_spans(text)
    offsets = []
    for index in range(len(spans) - 1):
        left = text[spans[index][0]:spans[index][1]]
        right = text[spans[index + 1][0]:spans[index + 1][1]]
        if can_break_between(left, right):
            offsets.append(spans[index][1])
    if text:
        offsets.append(len(text))
    return tuple(offsets)
