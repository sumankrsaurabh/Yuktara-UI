from novaui.native.layout import LayoutEngine, LayoutNode, Rect, Size
from novaui.native.rendering import parse_color
from novaui.native.platform.dispatcher import InputDispatcher
from novaui.native.platform.events import EventType, InputEvent, PointerEvent

def test_parse_color_variants():
    assert parse_color("#fff")==0xFFFFFFFF
    assert parse_color("#123456")==0xFF123456
    assert parse_color("#80123456")==0x80123456
    assert parse_color(0x123456)==0xFF123456

def test_parse_color_rejects_bad_input():
    import pytest
    with pytest.raises(ValueError): parse_color("#12")

def make_event(kind,x,y):
    return InputEvent(kind,pointer=PointerEvent(x=x,y=y,button=1,source="mouse"))

def test_click_only_when_release_matches_pressed_target():
    calls=[]
    child=LayoutNode.box(intrinsic_size=Size(40,40),on_click=lambda e:calls.append("click"))
    root=LayoutNode.box(child)
    LayoutEngine().layout(root,Rect(0,0,100,100))
    dispatcher=InputDispatcher(root)
    dispatcher.dispatch(make_event(EventType.POINTER_DOWN,10,10))
    dispatcher.dispatch(make_event(EventType.POINTER_UP,10,10))
    assert calls==["click"]
    dispatcher.dispatch(make_event(EventType.POINTER_DOWN,10,10))
    dispatcher.dispatch(make_event(EventType.POINTER_UP,90,90))
    assert calls==["click"]

def test_hover_enter_leave_and_move():
    calls=[]
    child=LayoutNode.box(intrinsic_size=Size(30,30),
        on_pointer_enter=lambda e:calls.append("enter"),
        on_pointer_move=lambda e:calls.append("move"),
        on_pointer_leave=lambda e:calls.append("leave"))
    root=LayoutNode.box(child)
    LayoutEngine().layout(root,Rect(0,0,100,100))
    d=InputDispatcher(root)
    d.dispatch(make_event(EventType.POINTER_MOTION,10,10))
    d.dispatch(make_event(EventType.POINTER_MOTION,11,11))
    d.dispatch(make_event(EventType.POINTER_MOTION,90,90))
    assert calls==["enter","move","move","leave"]

def test_pointer_callback_receives_normalized_event():
    seen=[]
    node=LayoutNode.box(on_pointer_down=lambda event:seen.append(event.type))
    LayoutEngine().layout(node,Rect(0,0,50,50))
    InputDispatcher(node).dispatch(make_event(EventType.POINTER_DOWN,5,5))
    assert seen==[EventType.POINTER_DOWN]
