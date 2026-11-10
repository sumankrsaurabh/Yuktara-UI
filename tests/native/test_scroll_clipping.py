import pytest
from novaui.native.layout import LayoutEngine, LayoutNode, Rect, Size
from novaui.native.layout.engine import hit_test
from novaui.native.platform.dispatcher import InputDispatcher
from novaui.native.platform.events import EventType, InputEvent, PointerEvent
from novaui.native.rendering.tree_painter import LayoutTreePainter


def test_vertical_scroll_measures_content_and_clamps_offset():
    content=LayoutNode.column(
        LayoutNode("box",height=80,intrinsic_size=Size(100,80)),
        LayoutNode("box",height=90,intrinsic_size=Size(100,90)),
        spacing=4,
    )
    viewport=LayoutNode.scroll(content,width=120,height=100,scroll_axis="vertical")
    LayoutEngine().layout(viewport,Rect(0,0,120,100))
    assert viewport.content_size.height == 174
    assert viewport.max_scroll_y == 74
    viewport.scroll_y=1000
    LayoutEngine().layout(viewport,Rect(0,0,120,100))
    assert viewport.scroll_y == 74
    assert content.bounds.y == -74


def test_hit_testing_respects_scroll_viewport():
    inside=LayoutNode("box",height=100,intrinsic_size=Size(100,100))
    scroll=LayoutNode.scroll(inside,width=100,height=40)
    LayoutEngine().layout(scroll,Rect(0,0,100,40))
    assert hit_test(scroll,10,20) is inside
    assert hit_test(scroll,10,60) is None


def test_wheel_scrolls_nearest_scroll_ancestor():
    child=LayoutNode("box",height=300,intrinsic_size=Size(100,300))
    scroll=LayoutNode.scroll(child,width=100,height=100)
    LayoutEngine().layout(scroll,Rect(0,0,100,100))
    dispatcher=InputDispatcher(scroll)
    event=InputEvent(EventType.POINTER_WHEEL,pointer=PointerEvent(10,10,wheel_y=-1))
    result=dispatcher.dispatch(event)
    assert result.handled
    assert scroll.scroll_y == 40


def test_touch_drag_scrolls_and_stops_on_release():
    child=LayoutNode("box",height=300,intrinsic_size=Size(100,300))
    scroll=LayoutNode.scroll(child,width=100,height=100)
    LayoutEngine().layout(scroll,Rect(0,0,100,100))
    dispatcher=InputDispatcher(scroll)
    dispatcher.dispatch(InputEvent(EventType.POINTER_DOWN,pointer=PointerEvent(10,70,source="touch",pointer_id=2)))
    dispatcher.dispatch(InputEvent(EventType.POINTER_MOTION,pointer=PointerEvent(10,30,source="touch",pointer_id=2)))
    assert scroll.scroll_y == 40
    dispatcher.dispatch(InputEvent(EventType.POINTER_UP,pointer=PointerEvent(10,30,source="touch",pointer_id=2)))
    dispatcher.dispatch(InputEvent(EventType.POINTER_MOTION,pointer=PointerEvent(10,10,source="touch",pointer_id=2)))
    assert scroll.scroll_y == 40


class FakeRenderer:
    def __init__(self): self.ops=[]
    def clear(self,c): self.ops.append(("clear",c))
    def draw_rect(self,*args,**kwargs): self.ops.append(("rect",args,kwargs))
    def draw_text(self,*args,**kwargs): pass
    def save(self): self.ops.append(("save",))
    def clip_rect(self,*args): self.ops.append(("clip",args))
    def restore(self): self.ops.append(("restore",))


def test_painter_clips_scroll_children_and_paints_thumb():
    child=LayoutNode("box",height=300,intrinsic_size=Size(100,300),background="#ff0000")
    scroll=LayoutNode.scroll(child,width=100,height=100)
    LayoutEngine().layout(scroll,Rect(0,0,100,100))
    renderer=FakeRenderer()
    LayoutTreePainter(renderer).paint(scroll)
    names=[op[0] for op in renderer.ops]
    assert names.index("save") < names.index("clip") < names.index("restore")
    assert names[-1] == "rect"  # scrollbar thumb is painted above clipped content
