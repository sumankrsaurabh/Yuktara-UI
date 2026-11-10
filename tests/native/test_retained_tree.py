import pytest
from novaui.native.layout import LayoutNode, Size
from novaui.native.reactivity import Component, Scheduler, reconcile

def test_keyed_children_retain_identity_when_reordered():
    old_a=LayoutNode("text",text="A",key="a")
    old_b=LayoutNode("text",text="B",key="b")
    old_root=LayoutNode.column(old_a,old_b,key="root")
    new_root=LayoutNode.column(
        LayoutNode("text",text="B updated",key="b"),
        LayoutNode("text",text="A updated",key="a"),key="root")
    result=reconcile(old_root,new_root)
    assert result.root is old_root
    assert old_root.children[0] is old_b
    assert old_root.children[1] is old_a
    assert old_b.text=="B updated"
    assert len(result.reused)==3

def test_removed_and_created_nodes_are_reported():
    old=LayoutNode.column(LayoutNode("box",key="gone"),key="root")
    new=LayoutNode.column(LayoutNode("box",key="new"),key="root")
    result=reconcile(old,new)
    assert len(result.created)==1
    assert len(result.removed)==1
    assert result.root.children[0].key=="new"

def test_duplicate_keys_rejected():
    old=LayoutNode.column(key="root")
    new=LayoutNode.column(LayoutNode("box",key="x"),LayoutNode("text",key="x"),key="root")
    with pytest.raises(ValueError,match="duplicate sibling key"):
        reconcile(old,new)

def test_unkeyed_children_reconcile_by_position():
    old_child=LayoutNode("box",intrinsic_size=Size(10,10))
    old=LayoutNode.column(old_child)
    new=LayoutNode.column(LayoutNode("box",intrinsic_size=Size(30,30)))
    result=reconcile(old,new)
    assert result.root.children[0] is old_child
    assert old_child.intrinsic_size==Size(30,30)

def test_component_rebuild_preserves_root_identity():
    values={"text":"first"}
    component=Component(lambda: LayoutNode("text",text=values["text"],key="label"))
    component.mount()
    first=component.node
    values["text"]="second"
    component.invalidate()
    component.scheduler.flush()
    assert component.node is first
    assert component.node.text=="second"

def test_component_rebuild_replaces_incompatible_kind():
    values={"kind":"box"}
    component=Component(lambda: LayoutNode(values["kind"],key="root"))
    component.mount()
    first=component.node
    values["kind"]="text"
    component.invalidate()
    component.scheduler.flush()
    assert component.node is not first
    assert component.last_reconcile.removed==(first,)
