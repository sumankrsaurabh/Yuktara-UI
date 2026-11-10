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
