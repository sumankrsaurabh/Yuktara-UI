import pytest

from novaui.native import (
    Button, ContextMenu, Dialog, MenuItem, NativeRuntime, Popover, TextField,
    Toast, Tooltip, column,
)
from novaui.native.layout import LayoutNode, Point, Rect, Size
from novaui.native.platform.events import EventType, InputEvent, KeyEvent, PointerEvent
from novaui.native.platform.dispatcher import SDLK_ESCAPE, SDLK_TAB


class FakeRenderer:
    def __init__(self):
        self.ops = []

    def clear(self, color):
        self.ops.append(("clear", color))

    def draw_rect(self, *args, **kwargs):
        self.ops.append(("rect", args, kwargs))

    def draw_text(self, *args, **kwargs):
        self.ops.append(("text", args, kwargs))


def pointer(kind, x, y):
    return InputEvent(kind, pointer=PointerEvent(x=x, y=y, button=1, source="mouse"))


def key(code):
    return InputEvent(EventType.KEY_DOWN, key=KeyEvent(code, 0, 0))


def click(runtime, x, y):
    runtime.dispatch(pointer(EventType.POINTER_DOWN, x, y))
    runtime.dispatch(pointer(EventType.POINTER_UP, x, y))


def test_dialog_is_centered_painted_above_content_and_dismisses_on_escape():
    renderer = FakeRenderer()
    runtime = NativeRuntime(lambda: LayoutNode("text", text="underlay"), renderer, 640, 400)
    runtime.start()
    handle = runtime.overlays.show_dialog(Dialog("Confirm", "Delete this file?"))
    entry = runtime.overlays.top
    assert entry.handle == handle
    assert entry.modal is True
    assert entry.root.bounds == Rect(0, 0, 640, 400)
    assert entry.node.bounds.x > 0 and entry.node.bounds.y > 0
    assert renderer.ops[-1][0] == "text"
    runtime.dispatch(key(SDLK_ESCAPE))
    assert runtime.overlays.entries == ()
    runtime.stop()


def test_dialog_outside_click_dismisses_and_reports_reason():
    reasons = []
    runtime = NativeRuntime(lambda: LayoutNode.box(intrinsic_size=Size(500, 300)), FakeRenderer(), 500, 300)
    runtime.start()
    runtime.overlays.show_dialog(Dialog("Notice", "Body"), on_dismiss=reasons.append)
    panel = runtime.overlays.top.node.bounds
    assert not panel.contains(Point(4, 4))
    click(runtime, 4, 4)
    assert runtime.overlays.entries == ()
    assert reasons == ["outside"]
    runtime.stop()


def test_modal_traps_keyboard_focus_inside_dialog():
    base_field = TextField("base").build()
    first = Button("First action").build()
    second = Button("Second action").build()
    runtime = NativeRuntime(lambda: column(base_field), FakeRenderer(), 500, 320)
    runtime.start()
    runtime.overlays.show_dialog(Dialog("Actions", [first, second]))
    runtime.dispatch(key(SDLK_TAB))
    assert runtime.dispatcher.focused is first or runtime.dispatcher.focused is second
    runtime.stop()


def test_popover_anchors_below_control_and_dismisses_on_outside_pointer_down():
    anchor = Button("Options").build()
    runtime = NativeRuntime(lambda: column(anchor), FakeRenderer(), 400, 260)
    runtime.start()
    runtime.overlays.show_popover(Popover("Popover body"), anchor=anchor)
    entry = runtime.overlays.top
    assert entry.root.bounds.y >= anchor.bounds.bottom
    click(runtime, 380, 240)
    assert runtime.overlays.entries == ()
    runtime.stop()


def test_popover_collision_flips_above_anchor_and_clamps_to_viewport():
    anchor = LayoutNode.box(width=100, height=30)
    base = column(LayoutNode.box(height=80), anchor)
    runtime = NativeRuntime(lambda: base, FakeRenderer(), 180, 120)
    runtime.start()
    runtime.overlays.show_popover(Popover("More", width=250), anchor=anchor, placement="bottom")
    bounds = runtime.overlays.top.root.bounds
    assert bounds.width <= 180
    assert bounds.x == 0
    assert bounds.y < anchor.bounds.y
    runtime.stop()


def test_tooltip_is_painted_but_does_not_capture_pointer_events():
    clicked = []
    anchor = Button("Target", on_click=lambda _event: clicked.append(True)).build()
    runtime = NativeRuntime(lambda: anchor, FakeRenderer(), 300, 180)
    runtime.start()
    runtime.overlays.show_tooltip(Tooltip("Helpful detail"), anchor=anchor)
    tip = runtime.overlays.top.root.bounds
    target, entry = runtime.overlays.hit_test(tip.x + 1, tip.y + 1)
    assert entry is None
    click(runtime, anchor.bounds.x + 2, anchor.bounds.y + 2)
    assert clicked == [True]
    runtime.stop()


def test_context_menu_items_invoke_callback_and_menu_clamps_to_viewport():
    selected = []
    menu = ContextMenu([MenuItem("Open", lambda _event: selected.append("open")),
                        MenuItem("Disabled", disabled=True)])
    runtime = NativeRuntime(lambda: LayoutNode.box(intrinsic_size=Size(400, 300)), FakeRenderer(), 240, 160)
    runtime.start()
    runtime.overlays.show_context_menu(menu, position=(230, 150))
    root = runtime.overlays.top.root
    assert root.bounds.right <= 240 and root.bounds.bottom <= 160
    item = root.children[0]
    click(runtime, item.bounds.x + 2, item.bounds.y + 2)
    assert selected == ["open"]
    assert runtime.overlays.entries == ()
    assert runtime.dispatcher.focused is None
    runtime.stop()


def test_disabled_context_menu_item_has_no_click_handler():
    node = ContextMenu([MenuItem("Unavailable", disabled=True)]).build()
    assert node.children[0].on_click is None
    assert node.children[0].accessibility_disabled is True


def test_toast_expiry_uses_explicit_runtime_clock():
    runtime = NativeRuntime(lambda: LayoutNode.box(), FakeRenderer(), 320, 180)
    runtime.start()
    runtime.overlays.show_toast(Toast("Saved", duration_ms=1000))
    assert len(runtime.overlays.entries) == 1
    assert runtime.advance_time(999) == 0
    assert len(runtime.overlays.entries) == 1
    assert runtime.advance_time(1) == 1
    assert runtime.overlays.entries == ()
    runtime.stop()


def test_persistent_toast_does_not_expire():
    runtime = NativeRuntime(lambda: LayoutNode.box(), FakeRenderer(), 320, 180)
    runtime.start()
    runtime.overlays.show_toast(Toast("Persistent", duration_ms=None))
    assert runtime.advance_time(100000) == 0
    assert len(runtime.overlays.entries) == 1
    runtime.overlays.dismiss_all()
    runtime.stop()


def test_overlays_stack_and_dismiss_by_handle():
    runtime = NativeRuntime(lambda: LayoutNode.box(), FakeRenderer(), 320, 180)
    runtime.start()
    first = runtime.overlays.show_popover(Popover("First"), anchor=Rect(10, 10, 20, 20))
    second = runtime.overlays.show_context_menu(ContextMenu([MenuItem("One")]), position=(30, 30))
    assert [entry.handle for entry in runtime.overlays.entries] == [first, second]
    assert runtime.overlays.dismiss(first) is True
    assert runtime.overlays.top.handle == second
    assert runtime.overlays.dismiss(first) is False
    runtime.stop()


def test_invalid_overlay_options_are_rejected():
    runtime = NativeRuntime(lambda: LayoutNode.box(), FakeRenderer(), 320, 180)
    with pytest.raises(ValueError):
        runtime.overlays.show(LayoutNode.box(), placement="diagonal")
    with pytest.raises(ValueError):
        runtime.overlays.show(Toast("Bad", duration_ms=10), duration_ms=0)
    with pytest.raises(TypeError):
        runtime.overlays.show_popover(Popover("x"), anchor=(2, 3))


def test_non_dismissible_dialog_blocks_outside_click_and_escape():
    runtime = NativeRuntime(lambda: LayoutNode.box(intrinsic_size=Size(300, 200)), FakeRenderer(), 300, 200)
    runtime.start()
    runtime.overlays.show_dialog(
        Dialog("Locked", "Complete the required step"),
        dismiss_on_escape=False, dismiss_on_outside=False,
    )
    click(runtime, 2, 2)
    assert len(runtime.overlays.entries) == 1
    runtime.dispatch(key(SDLK_ESCAPE))
    assert len(runtime.overlays.entries) == 1
    runtime.stop()


def test_escape_skips_passive_toast_and_dismisses_modal_underneath():
    runtime = NativeRuntime(lambda: LayoutNode.box(), FakeRenderer(), 320, 180)
    runtime.start()
    runtime.overlays.show_dialog(Dialog("Modal", "Body"))
    runtime.overlays.show_toast(Toast("Saved", duration_ms=None))
    runtime.dispatch(key(SDLK_ESCAPE))
    assert [entry.kind for entry in runtime.overlays.entries] == ["toast"]
    runtime.stop()


def test_accessibility_tree_can_include_active_overlay_semantics():
    from novaui.native import build_accessibility_tree
    runtime = NativeRuntime(lambda: LayoutNode("text", text="Home"), FakeRenderer(), 320, 180)
    runtime.start()
    runtime.overlays.show_dialog(Dialog("Confirm", "Continue?"))
    tree = build_accessibility_tree(runtime.root, overlays=runtime.overlays.roots)
    assert tree.role == "application"
    assert tree.children[-1].role == "dialog-overlay"
    assert tree.children[-1].children[0].role == "dialog"
    runtime.stop()


def test_interactive_overlay_above_modal_joins_focus_scope():
    runtime = NativeRuntime(lambda: TextField("background").build(), FakeRenderer(), 360, 240)
    runtime.start()
    runtime.overlays.show_dialog(Dialog("Modal", "Choose an item"))
    menu_item = MenuItem("Select", lambda _event: None)
    runtime.overlays.show_context_menu(ContextMenu([menu_item]), position=(30, 30))
    runtime.dispatch(key(SDLK_TAB))
    focused = runtime.dispatcher.focused
    assert focused is not runtime.root
    assert focused.accessibility_role == "menuitem"
    runtime.stop()


def test_dismissing_modal_restores_focus_to_previously_focused_control():
    base_button = Button("Open dialog").build()
    confirm = Button("Confirm").build()
    runtime = NativeRuntime(lambda: column(base_button), FakeRenderer(), 420, 240)
    runtime.start()
    runtime.dispatch(pointer(EventType.POINTER_DOWN, base_button.bounds.x + 2, base_button.bounds.y + 2))
    runtime.dispatch(pointer(EventType.POINTER_UP, base_button.bounds.x + 2, base_button.bounds.y + 2))
    assert runtime.dispatcher.focused is base_button

    runtime.overlays.show_dialog(Dialog("Confirm", [confirm]))
    assert runtime.dispatcher.focused is confirm
    runtime.dispatch(key(SDLK_ESCAPE))
    assert runtime.dispatcher.focused is base_button
    assert base_button.accessibility_focused is True
    runtime.stop()


def test_context_menu_starts_keyboard_focus_and_supports_arrow_navigation():
    from novaui.native.platform.dispatcher import SDLK_DOWN
    selected = []
    runtime = NativeRuntime(lambda: Button("Background").build(), FakeRenderer(), 420, 260)
    runtime.start()
    runtime.overlays.show_context_menu(
        ContextMenu([
            MenuItem("First", lambda _event: selected.append("first")),
            MenuItem("Second", lambda _event: selected.append("second")),
        ]),
        position=(30, 30),
    )
    first, second = runtime.overlays.top.root.children
    assert runtime.dispatcher.focused is first
    runtime.dispatch(key(SDLK_DOWN))
    assert runtime.dispatcher.focused is second
    runtime.dispatch(key(13))
    assert selected == ["second"]
    assert runtime.overlays.entries == ()
    runtime.stop()


def test_modal_accessibility_tree_excludes_obscured_application_controls():
    from novaui.native import build_accessibility_tree
    background = Button("Background action").build()
    runtime = NativeRuntime(lambda: background, FakeRenderer(), 360, 240)
    runtime.start()
    runtime.overlays.show_dialog(Dialog("Accessible dialog", "Body"))
    tree = build_accessibility_tree(runtime.root, overlays=runtime.overlays.roots)
    assert tree.role == "application"
    assert len(tree.children) == 1
    assert tree.children[0].role == "dialog-overlay"
    runtime.stop()


def test_dismissing_context_menu_restores_previous_focus():
    from novaui.native.platform.dispatcher import SDLK_ESCAPE
    base = Button("Open menu").build()
    runtime = NativeRuntime(lambda: column(base), FakeRenderer(), 360, 220)
    runtime.start()
    runtime.dispatch(pointer(EventType.POINTER_DOWN, base.bounds.x + 1, base.bounds.y + 1))
    runtime.dispatch(pointer(EventType.POINTER_UP, base.bounds.x + 1, base.bounds.y + 1))
    assert runtime.dispatcher.focused is base
    runtime.overlays.show_context_menu(ContextMenu([MenuItem("First", lambda _event: None),
                                                   MenuItem("Second", lambda _event: None)]),
                                       position=(40, 40))
    assert runtime.dispatcher.focused is runtime.overlays.top.root.children[0]
    runtime.dispatch(key(SDLK_ESCAPE))
    assert runtime.dispatcher.focused is base
    runtime.stop()
