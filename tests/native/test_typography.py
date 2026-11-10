import pytest

from novaui.native.typography import (
    DEFAULT_FONT_FAMILY,
    FALLBACK_FONT_FAMILIES,
    FontConfig,
)


def test_inter_is_the_primary_font():
    assert DEFAULT_FONT_FAMILY == "Inter"
    assert FontConfig().family == "Inter"


def test_fallbacks_are_available():
    assert "Noto Sans" in FALLBACK_FONT_FAMILIES
    assert "DejaVu Sans" in FALLBACK_FONT_FAMILIES


def test_font_size_must_be_positive():
    with pytest.raises(ValueError):
        FontConfig(size=0)


def test_font_weight_is_validated():
    with pytest.raises(ValueError):
        FontConfig(weight="ultra-heavy")
