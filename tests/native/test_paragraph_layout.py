from types import SimpleNamespace

import pytest

from novaui.native.layout import Constraints, LayoutEngine, LayoutNode, Rect
from novaui.native.rendering import LayoutTreePainter
from novaui.native.text import (ParagraphStyle, TextCluster, TextLayout, TextLine, TextMeasurer,
                                TextParagraph, TextStyleSpan, line_break_offsets,
                                grapheme_spans)
from novaui.native.text.linebreak import can_break_between
from novaui.native.typography import FontConfig


class FakeFont:
    def __init__(self, typeface, size):
        self.size = size

    def measureText(self, text):
        return len(text) * self.size * 0.5

    def getMetrics(self):
        return SimpleNamespace(fAscent=-self.size * 0.8,
                               fDescent=self.size * 0.2, fLeading=0)


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
        def MakeFromName(name, style):
            return object()

        @staticmethod
        def MakeDefault():
            return object()

    Font = FakeFont


class RecordingRenderer:
    def __init__(self):
        self.text = []
        self.rects = []
        self.strokes = []

    def draw_text(self, text, x, y, *, color, font):
        self.text.append((text, x, y, color, font))

    def draw_rect(self, x, y, width, height, color, *, radius=0):
        self.rects.append((x, y, width, height, color))

    def draw_stroke_rect(self, x, y, width, height, color, *, stroke_width=1, radius=0):
        self.strokes.append((x, y, width, height, color, stroke_width))


def test_line_break_rules_keep_nonbreaking_and_punctuation_pairs_together():
    assert not can_break_between("a", "\u00a0")
    assert not can_break_between("\u00a0", "b")
    assert not can_break_between("a", "\u2060")
    assert not can_break_between("\u2060", "b")
    assert not can_break_between("(", "word")
    assert not can_break_between("word", ")")
    assert not can_break_between(" ", "(")
    assert can_break_between("漢", "字")
    assert not can_break_between("漢", "，")
    assert can_break_between(" ", "n")


def test_cjk_paragraph_wraps_at_ideographic_boundaries():
    layout = TextMeasurer(FakeSkia).measure(
        "漢字かな", FontConfig(size=10), max_width=10
    )
    assert [line.text for line in layout.lines] == ["漢字", "かな"]
    assert all(line.width <= 10 for line in layout.lines)


def test_nonbreaking_space_sequence_overflows_instead_of_splitting():
    layout = TextMeasurer(FakeSkia).measure(
        "a\u00a0b", FontConfig(size=10), max_width=10
    )
    assert [line.text for line in layout.lines] == ["a\u00a0b"]
    assert layout.lines[0].width == 15


def test_word_joiner_keeps_adjacent_text_together():
    layout = TextMeasurer(FakeSkia).measure(
        "ab\u2060cd", FontConfig(size=10), max_width=5
    )
    assert [line.text for line in layout.lines] == ["a", "b\u2060c", "d"]


def test_paragraph_metadata_tracks_source_offsets_and_line_ranges():
    layout = TextMeasurer(FakeSkia).measure(
        "first\nsecond\n", FontConfig(size=10), wrap=False
    )
    assert layout.paragraphs == (
        TextParagraph("first", 0, 5, 0, 1, top=0, height=10),
        TextParagraph("second", 6, 12, 1, 1, top=10, height=10),
        TextParagraph("", 13, 13, 2, 1, top=20, height=10),
    )


def test_inline_style_spans_change_font_metrics_and_preserve_source_ranges():
    style = TextStyleSpan(1, 3, font_size=20, color=0xFFCC0000)
    layout = TextMeasurer(FakeSkia).measure(
        "ABCD", FontConfig(size=10), wrap=False, style_spans=(style,)
    )
    line = layout.lines[0]
    assert line.width == 30
    assert [(run.text, run.start, run.end) for run in line.paint_runs] == [
        ("A", 0, 1), ("BC", 1, 3), ("D", 3, 4)
    ]
    assert line.paint_runs[1].font_config.size == 20
    assert line.paint_runs[1].color == 0xFFCC0000
    assert layout.line_height == 20


def test_layout_node_renders_inline_color_background_and_underline():
    node = LayoutNode(
        kind="text", text="abcd", font_size=10,
        text_style_spans=(TextStyleSpan(
            1, 3, font_size=16, color=0xFF123456,
            underline=True, background=0x22334455,
        ),),
    )
    engine = LayoutEngine(TextMeasurer(FakeSkia))
    engine.measure(node, Constraints(0, 100, 0, 50))
    engine.arrange(node, Rect(0, 0, 100, 30))
    renderer = RecordingRenderer()
    LayoutTreePainter(renderer).paint(node)

    assert [call[0] for call in renderer.text] == ["a", "bc", "d"]
    assert renderer.text[1][3] == 0xFF123456
    assert renderer.rects[0][0] == 5
    assert renderer.rects[0][2] == 16
    assert len(renderer.rects) >= 2


def test_style_spans_reject_overlap_and_out_of_bounds():
    measurer = TextMeasurer(FakeSkia)
    with pytest.raises(ValueError, match="sorted and non-overlapping"):
        measurer.measure("abcd", style_spans=(TextStyleSpan(0, 3), TextStyleSpan(2, 4)))
    with pytest.raises(ValueError, match="exceeds"):
        measurer.measure("abc", style_spans=(TextStyleSpan(1, 4),))


def test_custom_line_break_provider_can_override_default_rules():
    measurer = TextMeasurer(FakeSkia, line_break_provider=lambda left, right: True)
    layout = measurer.measure("abcd", FontConfig(size=10), max_width=10)
    assert [line.text for line in layout.lines] == ["ab", "cd"]


def test_style_span_cannot_split_a_combining_grapheme():
    text = "e\u0301x"
    with pytest.raises(ValueError, match="must not split a grapheme cluster"):
        TextMeasurer._normalize_style_spans(text, (TextStyleSpan(0, 1),))


def test_line_break_offsets_include_cjk_and_whitespace_boundaries():
    offsets = line_break_offsets("漢字 next", grapheme_spans)
    assert 1 in offsets
    assert 3 in offsets
    assert offsets[-1] == len("漢字 next")


def test_selection_geometry_can_return_disjoint_visual_rectangles():
    layout = TextLayout(
        lines=(TextLine("אבג", 25, 8, 0, 3, (
            TextCluster(0, 1, 0, 5, False),
            TextCluster(1, 2, 5, 5, False),
            TextCluster(2, 3, 20, 5, True),
        )),),
        width=25, height=10, ascent=8, descent=2, leading=0, line_height=10,
    )
    assert layout.selection_rects(0, 3) == (
        (0, 0, 10, 10), (20, 0, 5, 10),
    )


def test_rich_text_widget_builds_a_text_node_with_inline_spans():
    from novaui.native import RichText

    widget = RichText(
        "Native rich text",
        spans=(TextStyleSpan(7, 11, font_weight="bold", color=0xFF123456),),
    )
    node = widget.build()
    assert node.kind == "text"
    assert node.text == "Native rich text"
    assert node.text_style_spans == widget.spans


def test_paragraph_alignment_indents_and_selection_geometry():
    style = ParagraphStyle(
        alignment="center", left_indent=5, right_indent=5,
        first_line_indent=4,
    )
    layout = TextMeasurer(FakeSkia).measure(
        "abc", FontConfig(size=10), max_width=60,
        paragraph_styles=(style,),
    )
    line = layout.lines[0]
    assert line.width == 15
    assert line.x_offset == pytest.approx(24.5)
    assert layout.caret_position(0) == (24.5, 0, 0)
    assert layout.selection_rects(0, 1) == ((24.5, 0, 5, 10),)
    assert layout.offset_at(26, 4) == 0
    assert layout.offset_at(28, 4) == 1


def test_paragraph_spacing_and_custom_line_height_affect_vertical_geometry():
    layout = TextMeasurer(FakeSkia).measure(
        "a\nb", FontConfig(size=10), wrap=False,
        paragraph_styles=(
            ParagraphStyle(space_before=3, space_after=4,
                           line_height=12, line_spacing=2),
            ParagraphStyle(line_height=15),
        ),
    )
    assert [(line.top, line.height) for line in layout.lines] == [(3, 14), (21, 15)]
    assert layout.paragraphs[0].top == 3
    assert layout.paragraphs[0].height == 14
    assert layout.paragraphs[1].top == 21
    assert layout.height == 36
    assert layout.caret_position(2)[1] == 21
    assert layout.selection_rects(2, 3)[0][1:] == (21, 5, 15)


def test_first_line_indent_reduces_first_line_wrap_width_only():
    layout = TextMeasurer(FakeSkia).measure(
        "one two", FontConfig(size=10), max_width=40,
        paragraph_styles=(ParagraphStyle(first_line_indent=10),),
    )
    assert [line.text for line in layout.lines] == ["one", "two"]
    assert [line.x_offset for line in layout.lines] == [10, 0]


def test_paragraph_marker_reserves_space_and_paints_once():
    node = LayoutNode(
        kind="text", text="Item\ncontinuation", font_size=10,
        text_paragraph_styles=(ParagraphStyle(marker="•", marker_indent=18),),
    )
    engine = LayoutEngine(TextMeasurer(FakeSkia))
    engine.measure(node, Constraints(0, 100, 0, 50))
    engine.arrange(node, Rect(0, 0, 100, 40))
    renderer = RecordingRenderer()
    LayoutTreePainter(renderer).paint(node)
    assert node.text_layout.lines[0].x_offset == 18
    assert renderer.text[0][0] == "Item"
    assert renderer.text[1][0] == "•"
    assert len([call for call in renderer.text if call[0] == "•"]) == 1


def test_rich_text_accepts_paragraph_styles_and_preserves_positional_size():
    from novaui.native import RichText

    style = ParagraphStyle(alignment="end", space_after=6)
    widget = RichText("first\nsecond", (), 18, paragraph_styles=(style,))
    node = widget.build()
    assert node.font_size == 18
    assert node.text_paragraph_styles == (style,)


def test_paragraph_style_rejects_invalid_metrics_and_alignment():
    with pytest.raises(ValueError, match="alignment"):
        ParagraphStyle(alignment="justify")
    with pytest.raises(ValueError, match="left_indent"):
        ParagraphStyle(left_indent=-1)
    with pytest.raises(ValueError, match="line_height"):
        ParagraphStyle(line_height=0)


def test_fixed_width_text_node_wraps_and_aligns_within_its_own_content_width():
    node = LayoutNode(
        kind="text", text="abc def", width=20, font_size=10,
        text_paragraph_styles=(ParagraphStyle(alignment="end"),),
    )
    engine = LayoutEngine(TextMeasurer(FakeSkia))
    engine.measure(node, Constraints(0, 100, 0, 50))
    assert [line.text for line in node.text_layout.lines] == ["abc", "def"]
    assert [line.x_offset for line in node.text_layout.lines] == [5, 5]
    assert node.measured_size.width == 20
