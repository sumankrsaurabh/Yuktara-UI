from types import SimpleNamespace
import pytest
from novaui.native.text import TextMeasurer
from novaui.native.typography import FontConfig
from novaui.native.layout import LayoutEngine, LayoutNode, Rect, Size

class FakeFont:
    def __init__(self, typeface, size): self.size=size
    def measureText(self,text): return len(text)*self.size*0.5
    def getMetrics(self):
        return SimpleNamespace(fAscent=-self.size*0.8,fDescent=self.size*0.2,fLeading=0)

class FakeSkia:
    class FontStyle:
        kNormal_Weight=0; kMedium_Weight=1; kSemiBold_Weight=2; kBold_Weight=3
        kNormal_Width=0; kUpright_Slant=0; kItalic_Slant=1
        def __init__(self,*args): pass
    class Typeface:
        @staticmethod
        def MakeFromName(name,style): return object()
        @staticmethod
        def MakeDefault(): return object()
    Font=FakeFont

def test_skia_text_measurement_wraps_words_and_tracks_metrics():
    m=TextMeasurer(FakeSkia)
    layout=m.measure("hello world",FontConfig(size=10),max_width=30)
    assert [line.text for line in layout.lines]==["hello","world"]
    assert layout.width==25
    assert layout.height==20
    assert layout.lines[0].baseline==8

def test_long_words_are_split_to_fit_width():
    layout=TextMeasurer(FakeSkia).measure("abcdefgh",FontConfig(size=10),max_width=15)
    assert [line.text for line in layout.lines]==["abc","def","gh"]
    assert all(line.width<=15 for line in layout.lines)

def test_newlines_preserved_and_max_lines_applied():
    layout=TextMeasurer(FakeSkia).measure("one\ntwo\nthree",FontConfig(size=10),wrap=False,max_lines=2)
    assert [line.text for line in layout.lines]==["one","two"]

def test_engine_uses_text_measurer_for_intrinsic_size_and_wrap():
    node=LayoutNode("text",text="hello world",font_size=10)
    engine=LayoutEngine(TextMeasurer(FakeSkia))
    size=engine.measure(node, __import__("novaui.native.layout",fromlist=["Constraints"]).Constraints(0,30,0,100))
    assert size==Size(25,20)
    assert node.text_layout is not None

def test_node_rejects_invalid_text_alignment():
    with pytest.raises(ValueError): LayoutNode("text",text="x",text_align="justify")


def test_text_layout_preserves_trailing_newline_and_empty_paragraphs():
    layout = TextMeasurer(FakeSkia).measure("first\n\nlast\n", FontConfig(size=10), wrap=False)
    assert [line.text for line in layout.lines] == ["first", "", "last", ""]
    assert [line.start for line in layout.lines] == [0, 6, 7, 12]


def test_text_layout_exposes_cluster_caret_and_selection_geometry():
    layout = TextMeasurer(FakeSkia).measure("A😀B", FontConfig(size=10), wrap=False)
    assert layout.caret_position(1) == (5.0, 0.0, 0)
    assert layout.caret_position(2) == (10.0, 0.0, 0)
    assert layout.offset_at(8.0, 0.0) == 2
    assert layout.selection_rects(1, 3) == ((5.0, 0.0, 10.0, 10.0),)


def test_wrapped_lines_keep_original_source_offsets():
    layout = TextMeasurer(FakeSkia).measure("hello world", FontConfig(size=10), max_width=30)
    assert [(line.text, line.start, line.end) for line in layout.lines] == [
        ("hello", 0, 5), ("world", 6, 11)
    ]


def test_text_measurer_does_not_split_combining_marks_emoji_or_indic_conjuncts():
    from novaui.native.text import grapheme_spans

    samples = ["e\u0301", "👍🏽", "👨‍👩‍👧‍👦", "🇮🇳", "क्ष"]
    for sample in samples:
        spans = grapheme_spans(sample)
        assert len(spans) == 1
        assert sample[spans[0][0]:spans[0][1]] == sample


def test_grapheme_spans_uses_unicode_regex_when_available(monkeypatch):
    import sys
    from types import SimpleNamespace
    from novaui.native.text import grapheme_spans

    class Match:
        def __init__(self, start, end):
            self._start, self._end = start, end
        def start(self):
            return self._start
        def end(self):
            return self._end

    calls = []
    def finditer(pattern, text):
        calls.append((pattern, text))
        return iter((Match(0, 2), Match(2, 5)))

    monkeypatch.setitem(sys.modules, "regex", SimpleNamespace(finditer=finditer))
    assert grapheme_spans("a👨‍👩") == ((0, 2), (2, 5))
    assert calls == [(r"\X", "a👨‍👩")]


def test_grapheme_spans_falls_back_when_regex_is_unavailable(monkeypatch):
    import sys
    from novaui.native.text import grapheme_spans

    monkeypatch.setitem(sys.modules, "regex", None)
    sample = "e\u0301"
    assert grapheme_spans(sample) == ((0, 2),)


def test_grapheme_spans_properties_cover_source_text():
    from hypothesis import given, strategies as st
    from novaui.native.text import grapheme_spans

    @given(st.text())
    def check(source):
        spans = grapheme_spans(source)
        if not source:
            assert spans == ()
            return
        assert spans[0][0] == 0
        assert spans[-1][1] == len(source)
        assert all(start < end for start, end in spans)
        assert all(left[1] == right[0] for left, right in zip(spans, spans[1:]))
        assert "".join(source[start:end] for start, end in spans) == source

    check()
