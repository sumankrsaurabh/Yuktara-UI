import pytest

from novaui.native import (
    Badge, Button, Card, Checkbox, Divider, Label, NativeTheme, ProgressBar,
    RadioGroup, Switch, build_accessibility_tree, column, row,
)
from novaui.native.layout import LayoutEngine, Rect
from novaui.native.platform.dispatcher import InputDispatcher
from novaui.native.platform.events import EventType, InputEvent, PointerEvent
from novaui.native.rendering import LayoutTreePainter


class RecordingRenderer:
    def __init__(self):
        self.calls = []

    def clear(self, color):
        self.calls.append(("clear", color))

    def draw_rect(self, x, y, width, height, color, *, radius=0):
        self.calls.append(("rect", x, y, width, height, color, radius))

    def draw_stroke_rect(self, x, y, width, height, color, *, stroke_width=1, radius=0):
        self.calls.append(("stroke", x, y, width, height, color, stroke_width, radius))

    def draw_text(self, text, x, y, *, color, font):
        self.calls.append(("text", text, x, y, color, font.size))


def click(node, x=5, y=5):
    engine = LayoutEngine()
    engine.layout(node, Rect(0, 0, 400, 200))
    dispatcher = InputDispatcher(node)
    event = InputEvent(EventType.POINTER_DOWN, pointer=PointerEvent(x=x, y=y, button=1))
    dispatcher.dispatch(event)
    dispatcher.dispatch(InputEvent(EventType.POINTER_UP, pointer=PointerEvent(x=x, y=y, button=1)))


def test_button_variants_and_disabled_semantics():
    for variant in Button.VARIANTS:
        node = Button("Apply", variant=variant).build()
        assert node.accessibility_role == "button"
        assert node.accessibility_label == "Apply"
    disabled = Button("Unavailable", disabled=True).build()
    assert disabled.on_click is None
    assert disabled.accessibility_disabled is True
    with pytest.raises(ValueError):
        Button("Bad", variant="neon")


def test_button_click_dispatches_once():
    calls = []
    node = Button("Save", on_click=lambda event: calls.append("saved")).build()
    click(node)
    assert calls == ["saved"]


def test_label_validation_and_text_properties():
    node = Label("Heading", size=22, weight="bold", max_lines=2).build()
    assert node.text == "Heading"
    assert node.font_size == 22
    assert node.font_weight == "bold"
    assert node.text_max_lines == 2
    with pytest.raises(ValueError):
        Label("Bad", align="middle")


def test_card_composes_widgets_and_paints_border():
    root = Card((Label("Title"), Badge("Ready", "success"))).build()
    assert root.kind == "column"
    assert root.border_width == 1
    assert [child.text for child in root.children] == ["Title", "Ready"]
    LayoutEngine().layout(root, Rect(0, 0, 300, 120))
    renderer = RecordingRenderer()
    LayoutTreePainter(renderer).paint(root)
    assert any(call[0] == "stroke" for call in renderer.calls)


def test_badge_semantic_status_and_variants():
    for variant in Badge.VARIANTS:
        node = Badge("Status", variant=variant).build()
        assert node.accessibility_role == "status"
    with pytest.raises(ValueError):
        Badge("Status", variant="purple").build()


def test_checkbox_toggles_model_and_live_semantics():
    changes = []
    widget = Checkbox("Remember me", on_change=changes.append)
    node = widget.build()
    node.on_click(None)
    assert widget.checked is True
    assert "☑" in node.text
    assert node.accessibility_checked is True
    assert changes == [True]


def test_disabled_checkbox_does_not_toggle():
    widget = Checkbox("Locked", disabled=True)
    node = widget.build()
    assert node.on_click is None
    widget._toggle()
    assert widget.checked is False


def test_switch_updates_track_and_semantics():
    changes = []
    widget = Switch("Notifications", on_change=changes.append)
    root = widget.build()
    track = root.children[0]
    old_color = track.background
    track.on_click(None)
    assert widget.checked is True
    assert track.background != old_color
    assert track.accessibility_checked is True
    assert changes == [True]


def test_radio_group_updates_selection_and_tree():
    changes = []
    widget = RadioGroup(("Day", "Week", "Month"), value="Day", on_change=changes.append)
    root = widget.build()
    root.children[1].on_click(None)
    assert widget.value == "Week"
    assert root.children[0].accessibility_selected is False
    assert root.children[1].accessibility_selected is True
    assert changes == ["Week"]


def test_radio_group_rejects_unknown_value_and_duplicate_options():
    with pytest.raises(ValueError):
        RadioGroup(("A", "B"), value="C")
    with pytest.raises(ValueError):
        RadioGroup(("A", "A"))


def test_progress_bar_bounds_and_semantic_value():
    bar = ProgressBar(68).build()
    assert bar.accessibility_role == "progressbar"
    assert bar.accessibility_value == "68%"
    with pytest.raises(ValueError):
        ProgressBar(101)
    with pytest.raises(ValueError):
        ProgressBar(-1)


def test_progress_bar_layout_allocates_fill_ratio():
    bar = ProgressBar(25).build()
    LayoutEngine().layout(bar, Rect(0, 0, 400, 8))
    assert bar.children[0].bounds.width == pytest.approx(100)
    assert bar.children[1].bounds.width == pytest.approx(300)


def test_divider_dimension_and_validation():
    horizontal = Divider().build()
    vertical = Divider(vertical=True, thickness=2).build()
    assert horizontal.height == 1
    assert vertical.width == 2
    with pytest.raises(ValueError):
        Divider(thickness=0).build()


def test_row_column_helpers_accept_widgets_and_nodes():
    root = column(Label("A"), row(Label("B"), Badge("C")))
    assert root.kind == "column"
    assert root.children[1].kind == "row"


def test_accessibility_tree_preserves_control_state():
    root = column(Checkbox("Accept", checked=True), Badge("Ready"))
    LayoutEngine().layout(root, Rect(0, 0, 300, 100))
    tree = build_accessibility_tree(root)
    assert tree.role == "group"
    assert tree.children[0].role == "checkbox"
    assert tree.children[0].checked is True
    assert tree.children[1].role == "status"


def test_dark_theme_exposes_complete_semantic_palette():
    theme = NativeTheme.dark()
    assert theme.name == "yuktara-dark"
    assert theme.primary != NativeTheme().primary
    assert theme.on_primary != 0
    assert theme.danger_soft != theme.warning_soft


def test_spacer_expands_in_linear_layout_and_rejects_negative_flex():
    from novaui.native import Spacer
    left = Label("Left").build()
    spacer = Spacer().build()
    right = Label("Right").build()
    root = row(left, spacer, right, spacing=0)
    LayoutEngine().layout(root, Rect(0, 0, 300, 40))
    assert spacer.bounds.width > 0
    with pytest.raises(ValueError):
        Spacer(flex=-1).build()
