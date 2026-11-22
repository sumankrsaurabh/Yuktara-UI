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


class StrictRectangleRenderer:
    """Mirror Skia's required rectangle signature instead of accepting bad calls."""

    def __init__(self):
        self.rectangles = []

    def draw_rect(self, x, y, width, height, color, *, radius=0.0):
        assert width >= 0
        assert height >= 0
        self.rectangles.append((x, y, width, height, color, radius))

    def draw_text(self, *_args, **_kwargs):
        pass

    def save(self):
        pass

    def clip_rect(self, *_args):
        pass

    def restore(self):
        pass


@pytest.mark.parametrize("axis", ["vertical", "horizontal"])
def test_scrollbar_uses_complete_rectangle_geometry(axis):
    if axis == "vertical":
        content = LayoutNode("box", height=300, intrinsic_size=Size(100, 300))
        viewport = LayoutNode.scroll(content, width=100, height=100, scroll_axis=axis)
    else:
        content = LayoutNode.row(
            LayoutNode("box", width=100, height=20, intrinsic_size=Size(100, 20)),
            LayoutNode("box", width=100, height=20, intrinsic_size=Size(100, 20)),
            spacing=0,
        )
        viewport = LayoutNode.scroll(content, width=100, height=40, scroll_axis=axis)

    LayoutEngine().layout(viewport, Rect(0, 0, 100, 100 if axis == "vertical" else 40))
    assert (viewport.max_scroll_y if axis == "vertical" else viewport.max_scroll_x) > 0

    renderer = StrictRectangleRenderer()
    LayoutTreePainter(renderer).paint(viewport)

    assert len(renderer.rectangles) == 1
    _x, _y, width, height, _color, radius = renderer.rectangles[0]
    assert radius == 2
    if axis == "vertical":
        assert width == 4
        assert height >= 18
    else:
        assert width >= 18
        assert height == 4
