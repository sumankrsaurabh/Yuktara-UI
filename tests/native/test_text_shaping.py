from types import SimpleNamespace

import pytest

from novaui.native.text import HarfBuzzShaper, TextMeasurer
from novaui.native.typography import FontConfig, FontRun


class FakeSkiaFont:
    def __init__(self, typeface, size):
        self.typeface = typeface
        self.size = size

    def getMetrics(self):
        return SimpleNamespace(fAscent=-self.size * 0.8,
                               fDescent=self.size * 0.2, fLeading=0)

    def measureText(self, text):
        return len(text) * self.size * 0.5


class FakeSkia:
    Font = FakeSkiaFont


class FakeResolver:
    def __init__(self):
        self.face = object()
        self._skia = FakeSkia

    def resolve(self, config):
        return self.face

    def resolve_runs(self, config, text):
        return (FontRun(text, 0, len(text), config.family, self.face),) if text else ()

    def measure_text(self, config, text):
        return len(text) * config.size * 0.5


class FakeBlob:
    @classmethod
    def from_file_path(cls, path):
        return path


class FakeFace:
    def __init__(self, blob):
        self.blob = blob
        self.upem = 1000


class FakePosition:
    def __init__(self, x_advance, x_offset=0, y_offset=0):
        self.x_advance = x_advance
        self.x_offset = x_offset
        self.y_offset = y_offset


class FakeBuffer:
    def __init__(self):
        self.text = ""
        self.direction = None
        self.glyph_infos = ()
        self.glyph_positions = ()

    def add_str(self, text):
        self.text = text

    def guess_segment_properties(self):
        if self.direction is None:
            self.direction = "ltr"


class FakeHarfBuzz:
    Blob = FakeBlob
    Face = FakeFace
    Buffer = FakeBuffer

    class BufferClusterLevel:
        MONOTONE_GRAPHEMES = 0

    @staticmethod
    def ot_font_set_funcs(font):
        pass

    @staticmethod
    def Font(face):
        return SimpleNamespace(face=face, scale=None)

    @staticmethod
    def shape(font, buffer, features):
        text = buffer.text
        if text == "fi":
            # One glyph for the two-character ligature.
            buffer.glyph_infos = (SimpleNamespace(codepoint=900, cluster=0),)
            buffer.glyph_positions = (FakePosition(600),)
            return
        entries = [(ord(char), index) for index, char in enumerate(text)]
        if buffer.direction == "rtl":
            entries.reverse()
        buffer.glyph_infos = tuple(
            SimpleNamespace(codepoint=glyph, cluster=cluster)
            for glyph, cluster in entries
        )
        buffer.glyph_positions = tuple(FakePosition(500) for _ in entries)


def test_font_config_exposes_explicit_shaping_font_paths():
    config = FontConfig(
        family="Example",
        fallback_families=(),
        font_path="/fonts/example.ttf",
        font_files=(("Arabic", "/fonts/arabic.ttf"),),
    )
    assert config.path_for_family("Example") == "/fonts/example.ttf"
    assert config.path_for_family("Arabic") == "/fonts/arabic.ttf"
    assert config.path_for_family("Missing") is None


def test_font_config_rejects_ambiguous_font_file_mappings():
    with pytest.raises(ValueError, match="configured more than once"):
        FontConfig(font_files=(("Example", "a.ttf"), ("Example", "b.ttf")))


def test_harfbuzz_shapes_ligatures_and_retains_source_cluster_offsets(tmp_path):
    font_file = tmp_path / "example.ttf"
    font_file.write_bytes(b"test-font-placeholder")
    config = FontConfig(family="Example", fallback_families=(), size=20,
                        font_path=str(font_file))
    measurer = TextMeasurer(
        FakeSkia, FakeResolver(), shaper=HarfBuzzShaper(FakeHarfBuzz)
    )
    layout = measurer.measure("fi", config, wrap=False)
    line = layout.lines[0]

    assert line.width == pytest.approx(12.0)
    assert len(line.glyph_runs) == 1
    assert line.glyph_runs[0].glyph_ids == (900,)
    assert line.glyph_runs[0].start == 0
    assert line.glyph_runs[0].end == 2
    assert [(item.start, item.end) for item in line.clusters] == [(0, 2)]
    assert layout.caret_position(0)[0] == pytest.approx(0.0)
    assert layout.caret_position(2)[0] == pytest.approx(12.0)


def test_harfbuzz_rtl_clusters_map_visual_coordinates_to_logical_offsets(tmp_path):
    font_file = tmp_path / "arabic.ttf"
    font_file.write_bytes(b"test-font-placeholder")
    config = FontConfig(family="Arabic", fallback_families=(), size=20,
                        font_path=str(font_file))
    measurer = TextMeasurer(
        FakeSkia, FakeResolver(), shaper=HarfBuzzShaper(FakeHarfBuzz)
    )
    layout = measurer.measure("سلام", config, wrap=False)
    line = layout.lines[0]

    assert line.rtl is True
    assert line.width == pytest.approx(40.0)
    assert line.glyph_runs[0].direction == "rtl"
    assert layout.caret_position(0)[0] == pytest.approx(40.0)
    assert layout.caret_position(4)[0] == pytest.approx(0.0)
    # Leftmost visual edge belongs to the logical end of the RTL run.
    assert layout.offset_at(0.1, 0) == 4
    assert layout.offset_at(39.9, 0) == 0


def test_harfbuzz_requires_a_font_file_for_every_selected_fallback_family(tmp_path):
    font_file = tmp_path / "primary.ttf"
    font_file.write_bytes(b"test-font-placeholder")
    resolver = FakeResolver()

    class FallbackResolver(FakeResolver):
        def resolve_runs(self, config, text):
            return (FontRun(text, 0, len(text), "Fallback", self.face),)

    measurer = TextMeasurer(
        FakeSkia, FallbackResolver(), shaper=HarfBuzzShaper(FakeHarfBuzz)
    )
    config = FontConfig(family="Primary", fallback_families=(), size=12,
                        font_path=str(font_file))
    with pytest.raises(ValueError, match="No font file configured for shaping family"):
        measurer.measure("text", config, wrap=False)


def test_shaper_gives_install_guidance_when_optional_package_is_missing(tmp_path):
    font_file = tmp_path / "example.ttf"
    font_file.write_bytes(b"test-font-placeholder")
    shaper = HarfBuzzShaper()
    with pytest.raises(RuntimeError, match=r"yuktara-ui\[shaping\]"):
        shaper._font(str(font_file))


def test_skia_renderer_draws_shaped_glyph_ids_without_reshaping_text():
    from novaui.native.renderer import SkiaRenderer

    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y

    class Builder:
        def __init__(self):
            self.run = None

        def allocRunPos(self, font, glyphs, positions):
            self.run = (font, glyphs, positions)

        def make(self):
            return self.run

    class Canvas:
        def __init__(self):
            self.call = None

        def drawTextBlob(self, blob, x, y, paint):
            self.call = (blob, x, y, paint)

    class SkiaModule:
        class Paint:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        @staticmethod
        def Font(typeface, size):
            return (typeface, size)

    SkiaModule.Point = Point
    SkiaModule.TextBlobBuilder = Builder
    renderer = SkiaRenderer.__new__(SkiaRenderer)
    renderer._skia = SkiaModule
    renderer._canvas = Canvas()
    face = object()
    renderer.draw_glyph_run((101, 102), ((0.0, 0.0), (8.0, -2.0)),
                            10.0, 24.0, color=0xFF123456,
                            typeface=face, size=16.0)
    (font, glyphs, positions), x, y, _paint = renderer._canvas.call
    assert glyphs == [101, 102]
    assert [(point.x, point.y) for point in positions] == [(0.0, 0.0), (8.0, -2.0)]
    assert (x, y) == (10.0, 24.0)
    assert font == (face, 16.0)


def test_layout_tree_painter_prefers_shaped_glyph_runs():
    from novaui.native.layout import LayoutNode, Rect
    from novaui.native.rendering import LayoutTreePainter

    font_file = __import__("pathlib").Path(__file__).with_name("test_text_shaping.py")
    config = FontConfig(family="Example", fallback_families=(), size=20,
                        font_path=str(font_file))
    layout = TextMeasurer(
        FakeSkia, FakeResolver(), shaper=HarfBuzzShaper(FakeHarfBuzz)
    ).measure("fi", config, wrap=False)

    class RecordingRenderer:
        def __init__(self):
            self.glyph_calls = []
            self.text_calls = []

        def draw_glyph_run(self, glyph_ids, positions, x, baseline_y, **kwargs):
            self.glyph_calls.append((glyph_ids, positions, x, baseline_y, kwargs))

        def draw_text(self, *args, **kwargs):
            self.text_calls.append((args, kwargs))

    node = LayoutNode(kind="text", text="fi", font_family="Example", font_size=20)
    node.bounds = Rect(0, 0, 100, 30)
    node.content_bounds = Rect(0, 0, 100, 30)
    node.text_layout = layout
    renderer = RecordingRenderer()
    LayoutTreePainter(renderer).paint(node)

    assert len(renderer.glyph_calls) == 1
    assert renderer.glyph_calls[0][0] == (900,)
    assert renderer.text_calls == []


def test_layout_engine_uses_registered_font_config_for_native_nodes(tmp_path):
    from novaui.native.layout import Constraints, LayoutEngine, LayoutNode

    font_file = tmp_path / "registered.ttf"
    font_file.write_bytes(b"test-font-placeholder")
    registered = FontConfig(
        family="Example", fallback_families=(), size=18,
        font_path=str(font_file),
    )
    measurer = TextMeasurer(
        FakeSkia, FakeResolver(), shaper=HarfBuzzShaper(FakeHarfBuzz),
        font_configs={"Example": registered},
    )
    node = LayoutNode(kind="text", text="fi", font_family="Example", font_size=18)
    LayoutEngine(text_measurer=measurer).measure(
        node, Constraints(0, 240, 0, 80)
    )
    assert node.text_layout is not None
    assert node.text_layout.lines[0].glyph_runs[0].glyph_ids == (900,)
    assert node.text_layout.lines[0].glyph_runs[0].typeface is not None


def test_text_measurer_validates_registered_font_configs():
    with pytest.raises(TypeError, match="FontConfig"):
        TextMeasurer(font_configs={"Example": object()})
