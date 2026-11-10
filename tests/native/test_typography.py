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


def test_font_resolver_uses_fallback_face_for_missing_glyphs():
    from novaui.native.typography import FontResolver

    class Typeface:
        def __init__(self, family):
            self.family = family

        def unicharToGlyph(self, codepoint):
            if self.family == "Primary" and codepoint < 128:
                return codepoint or 1
            if self.family == "Indic" and 0x0900 <= codepoint <= 0x097F:
                return codepoint
            return 0

    class FakeSkia:
        class FontStyle:
            kNormal_Weight = 0
            kMedium_Weight = 1
            kSemiBold_Weight = 2
            kBold_Weight = 3
            kNormal_Width = 0
            kUpright_Slant = 0
            kItalic_Slant = 1

            def __init__(self, *args):
                pass

        class Typeface:
            @staticmethod
            def MakeFromName(family, style):
                return Typeface(family) if family in {"Primary", "Indic"} else None

            @staticmethod
            def MakeDefault():
                return Typeface("Primary")

    resolver = FontResolver(FakeSkia)
    config = FontConfig(family="Primary", fallback_families=("Indic",), size=12)
    runs = resolver.resolve_runs(config, "AकB")
    assert [(run.text, run.family) for run in runs] == [
        ("A", "Primary"), ("क", "Indic"), ("B", "Primary")
    ]


def test_font_resolver_loads_exact_configured_font_file(tmp_path):
    from novaui.native.typography import FontResolver

    font_file = tmp_path / "Primary-Regular.ttf"
    font_file.write_bytes(b"test-font-data")
    loaded = []

    class Typeface:
        def __init__(self, source):
            self.source = source

        def unicharToGlyph(self, codepoint):
            return codepoint or 1

    class FontManager:
        def makeFromFile(self, path, index):
            loaded.append((path, index))
            return Typeface(path)

    class FakeSkia:
        class FontStyle:
            kNormal_Weight = 0
            kMedium_Weight = 1
            kSemiBold_Weight = 2
            kBold_Weight = 3
            kNormal_Width = 0
            kUpright_Slant = 0
            kItalic_Slant = 1

            def __init__(self, *args):
                pass

        class FontMgr:
            @staticmethod
            def RefDefault():
                return FontManager()

        class Typeface:
            @staticmethod
            def MakeFromName(family, style):
                raise AssertionError("configured font path must take precedence")

            @staticmethod
            def MakeDefault():
                return Typeface("default")

    resolver = FontResolver(FakeSkia)
    config = FontConfig(
        family="Primary", fallback_families=(), font_path=str(font_file)
    )
    face = resolver.resolve(config)
    assert face.source == str(font_file.resolve())
    assert loaded == [(str(font_file.resolve()), 0)]


def test_font_resolver_loads_configured_fallback_font_file(tmp_path):
    from novaui.native.typography import FontResolver

    primary_file = tmp_path / "primary.ttf"
    fallback_file = tmp_path / "indic.ttf"
    primary_file.write_bytes(b"primary")
    fallback_file.write_bytes(b"fallback")
    loaded = []

    class Typeface:
        def __init__(self, family, path=None):
            self.family = family
            self.path = path

        def unicharToGlyph(self, codepoint):
            if self.family == "Primary" and codepoint < 128:
                return codepoint or 1
            if self.family == "Indic" and 0x0900 <= codepoint <= 0x097F:
                return codepoint
            return 0

    class FontManager:
        def makeFromFile(self, path, index):
            loaded.append(path)
            family = "Primary" if path == str(primary_file.resolve()) else "Indic"
            return Typeface(family, path)

    class FakeSkia:
        class FontStyle:
            kNormal_Weight = 0
            kMedium_Weight = 1
            kSemiBold_Weight = 2
            kBold_Weight = 3
            kNormal_Width = 0
            kUpright_Slant = 0
            kItalic_Slant = 1

            def __init__(self, *args):
                pass

        class FontMgr:
            @staticmethod
            def RefDefault():
                return FontManager()

        class Typeface:
            @staticmethod
            def MakeFromName(family, style):
                raise AssertionError("explicit configured faces should load from files")

            @staticmethod
            def MakeDefault():
                return Typeface("Primary")

    config = FontConfig(
        family="Primary",
        fallback_families=("Indic",),
        font_path=str(primary_file),
        font_files=(("Indic", str(fallback_file)),),
    )
    runs = FontResolver(FakeSkia).resolve_runs(config, "Aक")
    assert [(run.family, run.typeface.path) for run in runs] == [
        ("Primary", str(primary_file.resolve())),
        ("Indic", str(fallback_file.resolve())),
    ]
    assert loaded == [str(primary_file.resolve()), str(fallback_file.resolve())]


def test_font_resolver_rejects_missing_configured_font_file(tmp_path):
    from novaui.native.typography import FontResolver

    class FakeSkia:
        class Typeface:
            @staticmethod
            def MakeFromName(family, style):
                raise AssertionError("missing explicit files must not use a system substitute")

    config = FontConfig(family="Primary", font_path=str(tmp_path / "missing.ttf"))
    with pytest.raises(FileNotFoundError, match="Configured font file"):
        FontResolver(FakeSkia).resolve(config)


def test_font_size_must_be_finite():
    import math

    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError, match="finite"):
            FontConfig(size=value)
