import pytest

from novaui.native import (
    Dropdown, SegmentedControl, Slider, TabItem, Tabs, TextArea, TextField,
    build_accessibility_tree, column,
)
from novaui.native.layout import LayoutEngine, Rect
from novaui.native.platform.dispatcher import InputDispatcher
from novaui.native.platform.events import EventType, InputEvent, KeyEvent, PointerEvent


KEY_BACKSPACE = 8
KEY_RETURN = 13
KEY_LEFT = (1 << 30) | 80
KEY_RIGHT = (1 << 30) | 79
KEY_HOME = (1 << 30) | 74
KEY_END = (1 << 30) | 77
KEY_DOWN = (1 << 30) | 81
KEY_UP = (1 << 30) | 82
KEY_ESCAPE = 27
MOD_SHIFT = 0x0001
MOD_CTRL = 0x0040


def pointer(event_type, x, y, *, source="mouse"):
    return InputEvent(event_type, pointer=PointerEvent(x=x, y=y, button=1, source=source))


def key(code, modifiers=0):
    return InputEvent(EventType.KEY_DOWN, key=KeyEvent(code, 0, modifiers))


def text(value):
    return InputEvent(EventType.TEXT_INPUT, text=value)


def layout(node, width=480, height=360):
    LayoutEngine().layout(node, Rect(0, 0, width, height))
    return node


def click(dispatcher, node, x, y):
    layout(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, x, y))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, x, y))


def test_text_field_receives_committed_text_and_calls_change():
    changes = []
    field = TextField(placeholder="Name", on_change=changes.append)
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 30, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 30, 20))
    assert dispatcher.focused is node
    dispatcher.dispatch(text("Suman"))
    assert field.value == "Suman"
    assert changes == ["Suman"]
    assert node.accessibility_value == "Suman"
    assert node.text == "Suman"
    assert node.text_cursor == len("Suman")


def test_text_field_backspace_delete_home_end_and_arrow_keys():
    field = TextField("abcd")
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 20, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 20, 20))
    dispatcher.dispatch(key(KEY_HOME))
    dispatcher.dispatch(key(KEY_RIGHT))
    dispatcher.dispatch(key(KEY_BACKSPACE))
    assert field.value == "bcd"
    dispatcher.dispatch(key(KEY_END))
    dispatcher.dispatch(key(127))
    assert field.value == "bcd"
    dispatcher.dispatch(key(KEY_LEFT))
    dispatcher.dispatch(key(KEY_BACKSPACE))
    assert field.value == "bd"


def test_text_field_ctrl_a_replaces_selection_and_respects_max_length():
    field = TextField("hello", max_length=8)
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 30, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 30, 20))
    dispatcher.dispatch(key(ord("a"), MOD_CTRL))
    dispatcher.dispatch(text("Yuktara UI"))
    assert field.value == "Yuktara "


def test_text_field_shift_navigation_creates_selection():
    field = TextField("abcdef")
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 10, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 10, 20))
    dispatcher.dispatch(key(KEY_END))
    dispatcher.dispatch(key(KEY_LEFT, MOD_SHIFT))
    dispatcher.dispatch(key(KEY_LEFT, MOD_SHIFT))
    assert field.selection == (4, 6)
    dispatcher.dispatch(text("XY"))
    assert field.value == "abcdXY"


def test_text_field_single_line_removes_newlines_and_submit_callback():
    submitted = []
    field = TextField(on_submit=submitted.append)
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 8, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 8, 20))
    dispatcher.dispatch(text("one\ntwo"))
    assert field.value == "onetwo"
    dispatcher.dispatch(key(KEY_RETURN))
    assert submitted == ["onetwo"]


def test_text_field_disabled_and_readonly_are_not_editable():
    disabled = TextField("locked", disabled=True).build()
    readonly = TextField("read only", read_only=True).build()
    assert disabled.on_text_input is None
    assert disabled.on_key_down is None
    readonly.on_text_input(text("x"))
    assert readonly.accessibility_disabled is False
    assert readonly.text == "read only"
    readonly.on_key_down(key(KEY_LEFT))
    readonly.on_text_input(text("x"))
    assert readonly.text == "read only"


def test_text_area_supports_newlines_and_vertical_navigation():
    area = TextArea("first\nlast")
    node = layout(area.build(), 360, 180)
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 120, 44))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 120, 44))
    dispatcher.dispatch(key(KEY_END))
    dispatcher.dispatch(text("!"))
    assert area.value.endswith("last!")
    assert "\n" in area.value
    dispatcher.dispatch(key(KEY_UP))
    assert area.cursor < len(area.value)


def test_text_area_enter_inserts_newline():
    area = TextArea("abc")
    node = layout(area.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 10, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 10, 20))
    dispatcher.dispatch(key(KEY_END))
    dispatcher.dispatch(key(KEY_RETURN))
    assert area.value == "abc\n"


def test_text_inputs_validate_dimensions_and_length():
    with pytest.raises(ValueError):
        TextField(width=0)
    with pytest.raises(ValueError):
        TextField(max_length=-1)
    with pytest.raises(ValueError):
        TextArea(height=0)


def test_tab_key_moves_focus_and_shift_tab_reverses():
    first = TextField("one").build()
    second = TextField("two").build()
    root = layout(column(first, second))
    dispatcher = InputDispatcher(root)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, first.bounds.x + 2, first.bounds.y + 2))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, first.bounds.x + 2, first.bounds.y + 2))
    assert dispatcher.focused is first
    dispatcher.dispatch(key(9))
    assert dispatcher.focused is second
    dispatcher.dispatch(key(9, MOD_SHIFT))
    assert dispatcher.focused is first


def test_dropdown_opens_selects_closes_and_updates_semantics():
    changes = []
    dropdown = Dropdown(("Daily", "Weekly", "Monthly"), on_change=changes.append)
    root = dropdown.build()
    dispatcher = InputDispatcher(root)
    layout(root, 300, 180)
    header = root.children[0]
    click(dispatcher, root, header.bounds.x + 10, header.bounds.y + 10)
    assert dropdown.is_open is True
    assert header.accessibility_expanded is True
    layout(root, 300, 180)
    option = root.children[2]
    click(dispatcher, root, option.bounds.x + 10, option.bounds.y + 8)
    assert dropdown.value == "Weekly"
    assert dropdown.is_open is False
    assert changes == ["Weekly"]
    assert header.accessibility_value == "Weekly"


def test_dropdown_keyboard_open_navigate_select_and_escape():
    dropdown = Dropdown(("A", "B", "C"))
    root = layout(dropdown.build(), 300, 180)
    dispatcher = InputDispatcher(root)
    header = root.children[0]
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, header.bounds.x + 4, header.bounds.y + 4))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, header.bounds.x + 4, header.bounds.y + 4))
    assert dropdown.is_open is True
    dispatcher.dispatch(key(KEY_DOWN))
    dispatcher.dispatch(key(KEY_RETURN))
    assert dropdown.value == "B"
    dispatcher.dispatch(key(KEY_DOWN))
    dispatcher.dispatch(key(KEY_ESCAPE))
    assert dropdown.is_open is False


def test_dropdown_rejects_invalid_options_and_value():
    with pytest.raises(ValueError):
        Dropdown(())
    with pytest.raises(ValueError):
        Dropdown(("A", "A"))
    with pytest.raises(ValueError):
        Dropdown(("A", "B"), value="C")


def test_slider_pointer_drag_snaps_to_step_and_reports_value():
    changes = []
    slider = Slider(value=20, minimum=0, maximum=100, step=5, on_change=changes.append)
    node = layout(slider.build(), 300, 60)
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, node.bounds.right - 10, 14))
    dispatcher.dispatch(pointer(EventType.POINTER_MOTION, node.bounds.right + 40, 14))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, node.bounds.right + 40, 14))
    assert slider.value == 100
    assert changes[-1] == 100
    assert node.accessibility_value == "100"


def test_slider_keyboard_arrows_home_end_and_disabled():
    slider = Slider(value=50, step=10)
    node = layout(slider.build(), 240, 28)
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 120, 14))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 120, 14))
    dispatcher.dispatch(key(KEY_RIGHT))
    assert slider.value == 60
    dispatcher.dispatch(key(KEY_HOME))
    assert slider.value == 0
    dispatcher.dispatch(key(KEY_END))
    assert slider.value == 100
    locked = Slider(20, disabled=True).build()
    assert locked.on_pointer_down is None
    assert locked.on_key_down is None


def test_slider_paints_track_fill_and_thumb():
    from test_ui_components import RecordingRenderer
    slider = Slider(value=50)
    node = layout(slider.build())
    renderer = RecordingRenderer()
    node.paint_callback(renderer, node)
    assert len([call for call in renderer.calls if call[0] == "rect"]) == 3
    assert any(call[0] == "stroke" for call in renderer.calls)


def test_slider_validates_range_step_and_width():
    with pytest.raises(ValueError):
        Slider(minimum=5, maximum=5)
    with pytest.raises(ValueError):
        Slider(step=0)
    with pytest.raises(ValueError):
        Slider(width=20)
    with pytest.raises(ValueError):
        Slider(value=101)


def test_tabs_select_panel_and_keyboard_navigation():
    changes = []
    tabs = Tabs((TabItem("General", "general panel"), TabItem("Advanced", "advanced panel")),
                on_change=changes.append)
    root = tabs.build()
    assert root.children[1].text == "general panel"
    tablist = root.children[0]
    node = tablist.children[1]
    layout(root, 400, 160)
    dispatcher = InputDispatcher(root)
    click(dispatcher, root, node.bounds.x + 4, node.bounds.y + 4)
    assert tabs.value == "Advanced"
    assert root.children[1].text == "advanced panel"
    assert node.accessibility_selected is True
    assert changes == ["Advanced"]
    dispatcher.dispatch(key(KEY_LEFT))
    assert tabs.value == "General"


def test_tabs_support_widget_content_and_disabled_tabs():
    tabs = Tabs((TabItem("One", TextField("text")), TabItem("Two", "two", disabled=True)))
    root = tabs.build()
    assert root.children[1].accessibility_role == "textbox"
    assert root.children[0].children[1].on_click is None
    with pytest.raises(ValueError):
        Tabs(("A", "A"))
    with pytest.raises(ValueError):
        Tabs(("A",), value="B")


def test_segmented_control_selects_mutually_exclusive_option():
    changes = []
    control = SegmentedControl(("Day", "Week", "Month"), value="Day", on_change=changes.append)
    root = layout(control.build(), 360, 60)
    dispatcher = InputDispatcher(root)
    target = root.children[1]
    click(dispatcher, root, target.bounds.x + 5, target.bounds.y + 5)
    assert control.value == "Week"
    assert target.accessibility_selected is True
    assert changes == ["Week"]
    dispatcher.dispatch(key(KEY_RIGHT))
    assert control.value == "Month"


def test_segmented_control_validation_and_disabled_state():
    with pytest.raises(ValueError):
        SegmentedControl(())
    with pytest.raises(ValueError):
        SegmentedControl(("A", "A"))
    with pytest.raises(ValueError):
        SegmentedControl(("A", "B"), value="C")
    locked = SegmentedControl(("A", "B"), disabled=True).build()
    assert all(node.on_click is None for node in locked.children)


def test_accessibility_tree_includes_new_control_semantics():
    root = layout(column(
        TextField(placeholder="Email"),
        Slider(value=25, label="Zoom"),
        Dropdown(("A", "B")),
        SegmentedControl(("A", "B")),
    ))
    semantics = build_accessibility_tree(root)
    roles = [node.role for node in semantics.children]
    assert roles == ["textbox", "slider", "group", "radiogroup"]
    assert semantics.children[0].label == "Email"
    assert semantics.children[1].value == "25"


def test_native_runtime_repaints_while_dragging_slider():
    from novaui.native.runtime import NativeRuntime

    class Renderer:
        def __init__(self):
            self.frames = 0

        def clear(self, _color):
            self.frames += 1

        def draw_rect(self, *_args, **_kwargs):
            pass

        def draw_stroke_rect(self, *_args, **_kwargs):
            pass

        def draw_text(self, *_args, **_kwargs):
            pass

    slider = Slider(value=10, step=5, width=240)
    root = slider.build()
    renderer = Renderer()
    runtime = NativeRuntime(lambda: root, renderer, 240, 28)
    runtime.start()
    initial_frames = runtime.frame_count
    runtime.dispatch(pointer(EventType.POINTER_DOWN, 40, 14))
    runtime.dispatch(pointer(EventType.POINTER_MOTION, 190, 14))
    assert slider.value > 10
    assert runtime.frame_count > initial_frames
    runtime.dispatch(pointer(EventType.POINTER_UP, 190, 14))
    runtime.stop()


def test_dropdown_active_option_highlight_and_focus_returns_to_trigger():
    dropdown = Dropdown(("First", "Second", "Third"))
    root = layout(dropdown.build(), 280, 180)
    dispatcher = InputDispatcher(root)
    header = root.children[0]
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 8, 8))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 8, 8))
    dispatcher.dispatch(key(KEY_DOWN))
    active = root.children[2]
    assert active.accessibility_focused is True
    assert active.accessibility_selected is False
    dispatcher.dispatch(key(KEY_RETURN))
    assert dropdown.value == "Second"
    assert dropdown.is_open is False
    dispatcher.dispatch(key(KEY_DOWN))
    assert dispatcher.focused is header
    assert dropdown.is_open is True


def test_focused_state_is_exposed_in_accessibility_snapshot():
    field = TextField(placeholder="Account email")
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 20, 18))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 20, 18))
    semantic = build_accessibility_tree(node)
    assert semantic.focused is True
    dispatcher.reset()
    assert build_accessibility_tree(node).focused is False


def test_focused_button_can_be_activated_with_enter_and_space():
    from novaui.native import Button

    calls = []
    node = layout(Button("Run", on_click=lambda _event: calls.append("run")).build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 12, 12))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 12, 12))
    dispatcher.dispatch(key(KEY_RETURN))
    dispatcher.dispatch(key(32))
    assert calls == ["run", "run", "run"]


def test_text_field_backspace_and_delete_remove_whole_grapheme_clusters():
    from novaui.native.text import previous_grapheme_boundary

    value = "A e\u0301👍🏽👨‍👩‍👧‍👦"
    field = TextField(value)
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 450, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 450, 20))
    dispatcher.dispatch(key(KEY_BACKSPACE))
    assert field.value == "A e\u0301👍🏽"
    dispatcher.dispatch(key(KEY_BACKSPACE))
    assert field.value == "A e\u0301"

    field = TextField("e\u0301x")
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 8, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 8, 20))
    dispatcher.dispatch(key(KEY_HOME))
    dispatcher.dispatch(key(KEY_RIGHT))
    dispatcher.dispatch(key(127))
    assert field.value == "e\u0301"


def test_text_field_drag_selection_tracks_pointer_capture():
    field = TextField("abcdef")
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 12, 20))
    dispatcher.dispatch(InputEvent(EventType.POINTER_MOTION,
                                   pointer=PointerEvent(x=45, y=20, buttons=1)))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 45, 20))
    assert field.selection[0] == 0
    assert field.selection[1] > 0
    assert node.text_selection == field.selection


class MemoryClipboard:
    def __init__(self, text=""):
        self.text = text

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text


def test_text_field_copy_cut_and_paste_use_injected_clipboard():
    clipboard = MemoryClipboard()
    field = TextField("Yuktara UI", clipboard=clipboard)
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 10, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 10, 20))
    dispatcher.dispatch(key(KEY_HOME))
    dispatcher.dispatch(key(KEY_END, MOD_SHIFT))
    dispatcher.dispatch(key(ord("c"), MOD_CTRL))
    assert clipboard.text == "Yuktara UI"
    dispatcher.dispatch(key(ord("x"), MOD_CTRL))
    assert field.value == ""
    dispatcher.dispatch(key(ord("v"), MOD_CTRL))
    assert field.value == "Yuktara UI"


def test_ctrl_v_without_clipboard_does_not_delete_existing_selection():
    field = TextField("keep me")
    node = layout(field.build())
    dispatcher = InputDispatcher(node)
    dispatcher.dispatch(pointer(EventType.POINTER_DOWN, 10, 20))
    dispatcher.dispatch(pointer(EventType.POINTER_UP, 10, 20))
    dispatcher.dispatch(key(KEY_HOME))
    dispatcher.dispatch(key(KEY_END, MOD_SHIFT))
    dispatcher.dispatch(key(ord("v"), MOD_CTRL))
    assert field.value == "keep me"


def test_text_field_uses_font_family_and_disables_drag_handlers_when_disabled():
    node = TextField("hello", font_family="Noto Sans", disabled=True).build()
    assert node.font_family == "Noto Sans"
    assert node.on_pointer_move is None
    assert node.on_pointer_down is None


def test_text_selection_and_caret_are_painted_from_cluster_geometry():
    from test_ui_components import RecordingRenderer
    from novaui.native.rendering import LayoutTreePainter
    from novaui.native.text import TextMeasurer
    from test_text_measurement import FakeSkia

    field = TextField("A😀B")
    node = field.build()
    LayoutEngine(TextMeasurer(FakeSkia)).layout(node, Rect(0, 0, 240, 40))
    field._focus()
    field.anchor, field.cursor = 1, 2
    field._sync_node()
    renderer = RecordingRenderer()
    LayoutTreePainter(renderer).paint(node)
    rects = [call for call in renderer.calls if call[0] == "rect"]
    text_calls = [i for i, call in enumerate(renderer.calls) if call[0] == "text"]
    assert len(rects) >= 3  # field background, selection fill, insertion caret
    assert text_calls
    assert renderer.calls.index(rects[-1]) > text_calls[-1]


def test_text_field_focus_activates_and_blur_deactivates_platform_text_input():
    class HostServices(MemoryClipboard):
        def __init__(self):
            super().__init__()
            self.calls = []

        def start_text_input(self):
            self.calls.append("start")

        def stop_text_input(self):
            self.calls.append("stop")

    services = HostServices()
    field = TextField(clipboard=services)
    node = field.build()
    field._focus()
    field._blur()
    assert services.calls == ["start", "stop"]
