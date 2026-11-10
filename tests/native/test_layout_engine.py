import pytest
from novaui.native.layout import (Alignment, Constraints, Insets, LayoutEngine,
    LayoutNode, MainAxisAlignment, Rect, Size, hit_test)

def test_constraints_clamp_size():
    c=Constraints(10,100,20,80)
    assert c.constrain(Size(5,90))==Size(10,80)

def test_column_padding_and_spacing():
    a=LayoutNode("box",intrinsic_size=Size(40,10))
    b=LayoutNode("box",intrinsic_size=Size(30,20))
    root=LayoutNode.column(a,b,spacing=5,padding=Insets.all(10))
    engine=LayoutEngine()
    engine.layout(root,Rect(0,0,100,100))
    assert root.content_bounds==Rect(10,10,80,80)
    assert a.bounds==Rect(10,10,80,10)
    assert b.bounds==Rect(10,25,80,20)

def test_row_weighted_child_gets_remaining_width():
    fixed=LayoutNode.box(intrinsic_size=Size(30,20))
    flexible=LayoutNode.box(weight=1,intrinsic_size=Size(10,10))
    root=LayoutNode.row(fixed,flexible,spacing=10)
    LayoutEngine().layout(root,Rect(0,0,200,50))
    assert fixed.bounds.width==30
    assert flexible.bounds.width==160
    assert flexible.bounds.x==40

def test_stack_overlays_children_and_center_aligns():
    a=LayoutNode.box(intrinsic_size=Size(20,10))
    root=LayoutNode.stack(a,align=Alignment.CENTER)
    LayoutEngine().layout(root,Rect(0,0,100,80))
    assert a.bounds==Rect(40,35,20,10)

def test_main_axis_space_between():
    a=LayoutNode.box(intrinsic_size=Size(10,10))
    b=LayoutNode.box(intrinsic_size=Size(10,10))
    root=LayoutNode.row(a,b,main_align=MainAxisAlignment.SPACE_BETWEEN)
    LayoutEngine().layout(root,Rect(0,0,100,30))
    assert a.bounds.x==0
    assert b.bounds.x==90

def test_hit_test_returns_deepest_child():
    child=LayoutNode.box(intrinsic_size=Size(20,20))
    root=LayoutNode.box(child)
    LayoutEngine().layout(root,Rect(0,0,100,100))
    assert hit_test(root,10,10) is child
    assert hit_test(root,90,90) is root

def test_invalid_constraints_rejected():
    with pytest.raises(ValueError): Constraints(20,10,0,10)
