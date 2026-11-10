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


def test_reconcile_updates_all_declared_visual_accessibility_and_callback_fields():
    old = LayoutNode(
        "box", key="root", opacity=1.0, border_color=0xFF000000,
        accessibility_role="group", accessibility_label="old",
        accessibility_disabled=False, grid_columns=2,
    )
    old.text_layout = object()
    new_key_handler = lambda event: "new"
    new = LayoutNode(
        "box", key="root", opacity=0.35, border_color=0xFFFF0000,
        accessibility_role="toolbar", accessibility_label="updated",
        accessibility_disabled=True, grid_columns=4,
        on_key_down=new_key_handler,
    )

    result = reconcile(old, new)

    assert result.root is old
    assert old.opacity == pytest.approx(0.35)
    assert old.border_color == 0xFFFF0000
    assert old.accessibility_role == "toolbar"
    assert old.accessibility_label == "updated"
    assert old.accessibility_disabled is True
    assert old.grid_columns == 4
    assert old.on_key_down is new_key_handler
    assert old.text_layout is None


def test_reconcile_preserves_live_focus_and_scroll_state():
    old = LayoutNode(
        "scroll", key="scroll-root", scroll_y=42, text_scroll_x=8,
        accessibility_focused=True,
    )
    new = LayoutNode(
        "scroll", key="scroll-root", scroll_y=0, text_scroll_x=0,
        accessibility_focused=False,
    )

    reconcile(old, new)

    assert old.scroll_y == 42
    assert old.text_scroll_x == 8
    assert old.accessibility_focused is True


def test_dispatcher_drops_removed_nodes_from_focus_history_on_root_update():
    from novaui.native.platform.dispatcher import InputDispatcher

    old_focus = LayoutNode("box", accessibility_role="button", on_click=lambda _event: None)
    current_focus = LayoutNode("box", accessibility_role="button", on_click=lambda _event: None)
    old_root = LayoutNode.column(old_focus, current_focus, key="root")
    dispatcher = InputDispatcher(old_root)
    dispatcher._set_focus(old_focus)
    dispatcher._set_focus(current_focus)

    new_root = LayoutNode.column(
        LayoutNode("box", accessibility_role="button", on_click=lambda _event: None),
        key="root",
    )
    # The first old node is still present only as historical focus; the new
    # tree has no compatible retained child, so history must not hold it alive.
    dispatcher.update_root(new_root)

    assert old_focus not in dispatcher._focus_history
    assert current_focus not in dispatcher._focus_history


def test_reconcile_updates_advanced_layout_properties():
    old_child = LayoutNode("box", key="child", width=30, position="flow")
    old = LayoutNode.row(old_child, key="root", flex_wrap=False)
    new_child = LayoutNode(
        "box", key="child", width="50%", min_width=80,
        position="absolute", left="10%", top=6,
        grid_row=1, grid_column=2, grid_column_span=2,
    )
    new = LayoutNode.row(new_child, key="root", flex_wrap=True, wrap_spacing=12)

    reconcile(old, new)

    assert old.flex_wrap is True
    assert old.wrap_spacing == 12
    assert old.children[0] is old_child
    assert old_child.width == "50%"
    assert old_child.min_width == 80
    assert old_child.position == "absolute"
    assert old_child.left == "10%"
    assert old_child.top == 6
    assert old_child.grid_row == 1
    assert old_child.grid_column == 2
    assert old_child.grid_column_span == 2
