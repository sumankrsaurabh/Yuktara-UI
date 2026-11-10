import pytest

from novaui.native import AnimationManager, NativeRuntime
from novaui.native.layout import LayoutNode, Size
from novaui.native.platform.dispatcher import InputDispatcher
from novaui.native.rendering import LayoutTreePainter


class FakeRenderer:
    def __init__(self):
        self.ops = []

    def clear(self, color):
        self.ops.append(("clear", color))

    def draw_rect(self, *args, **kwargs):
        self.ops.append(("rect", args, kwargs))

    def draw_stroke_rect(self, *args, **kwargs):
        self.ops.append(("stroke", args, kwargs))

    def draw_text(self, *args, **kwargs):
        self.ops.append(("text", args, kwargs))


def test_runtime_animates_opacity_with_host_clock_and_repaints():
    renderer = FakeRenderer()
    node = LayoutNode.box(width=100, height=40, background="#336699")
    runtime = NativeRuntime(lambda: node, renderer, 160, 100)
    runtime.start()
    before = runtime.frame_count
    completed = []
    handle = runtime.animate(node, "opacity", 0.0, duration_ms=100,
                             easing="linear", on_complete=lambda: completed.append(True))
    assert handle in runtime.animations.handles
    assert runtime.frame_count == before

    runtime.advance_time(25)
    assert node.opacity == pytest.approx(0.75)
    assert runtime.frame_count > before
    assert completed == []

    runtime.advance_time(75)
    assert node.opacity == 0.0
    assert runtime.animations.active_count == 0
    assert completed == [True]
    runtime.stop()


def test_animation_easing_replacement_and_cancel():
    class Target:
        value = 0.0

    target = Target()
    manager = AnimationManager()
    first = manager.animate(target, "value", 100, duration_ms=100, easing="linear")
    manager.advance_time(25)
    assert target.value == pytest.approx(25)

    second = manager.animate(target, "value", 50, duration_ms=100, easing="ease_out")
    assert manager.cancel(first) is False
    assert manager.cancel(second) is True
    assert manager.active_count == 0
    assert target.value == pytest.approx(25)


def test_reduced_motion_finishes_current_and_future_animations_immediately():
    class Target:
        value = 0.0

    target = Target()
    completed = []
    manager = AnimationManager()
    manager.animate(target, "value", 1, duration_ms=500,
                    on_complete=lambda: completed.append("first"))
    manager.set_reduced_motion(True)
    assert target.value == 1
    assert manager.active_count == 0
    assert completed == ["first"]

    manager.animate(target, "value", 0, duration_ms=500,
                    on_complete=lambda: completed.append("second"))
    assert target.value == 0
    assert completed == ["first", "second"]


def test_animation_validates_time_values_easing_and_opacity_range():
    node = LayoutNode.box()
    manager = AnimationManager()
    with pytest.raises(ValueError):
        manager.animate(node, "opacity", 2, duration_ms=10)
    with pytest.raises(ValueError):
        manager.animate(node, "opacity", 0, duration_ms=-1)
    with pytest.raises(ValueError):
        manager.animate(node, "opacity", 0, duration_ms=10, easing="spring")
    with pytest.raises(ValueError):
        manager.advance_time(float("nan"))
    with pytest.raises(AttributeError):
        manager.animate(node, "missing", 1)


def test_inherited_opacity_multiplies_fill_and_text_alpha():
    renderer = FakeRenderer()
    child = LayoutNode("text", text="child", width=60, height=20,
                       background="#FF0000", opacity=0.5)
    root = LayoutNode.box(child, width=100, height=50,
                          background="#0000FF", opacity=0.5)
    runtime = NativeRuntime(lambda: root, renderer, 120, 80)
    runtime.start()
    rect_colors = [op[1][4] for op in renderer.ops if op[0] == "rect"]
    assert (rect_colors[0] >> 24) & 0xFF == 128
    assert (rect_colors[1] >> 24) & 0xFF == 64
    text_colors = [op[2]["color"] for op in renderer.ops if op[0] == "text"]
    assert text_colors and ((text_colors[-1] >> 24) & 0xFF) == 64
    runtime.stop()


def test_keyboard_focused_node_gets_visible_focus_ring():
    renderer = FakeRenderer()
    node = LayoutNode("box", width=80, height=30, accessibility_role="button",
                      accessibility_focused=True, background="#FFFFFF")
    runtime = NativeRuntime(lambda: node, renderer, 120, 80)
    runtime.start()
    strokes = [op for op in renderer.ops if op[0] == "stroke"]
    assert strokes
    assert strokes[-1][2]["stroke_width"] == 2.0
    runtime.stop()


def test_opacity_uses_group_layer_when_renderer_supports_compositing():
    class LayerRenderer(FakeRenderer):
        def save_layer(self, opacity):
            self.ops.append(("save_layer", opacity))

        def restore(self):
            self.ops.append(("restore",))

    renderer = LayerRenderer()
    child = LayoutNode("text", text="child", background="#FF0000", width=60, height=20)
    root = LayoutNode.box(child, width=100, height=50,
                          background="#0000FF", opacity=0.5)
    runtime = NativeRuntime(lambda: root, renderer, 120, 80)
    runtime.start()
    assert ("save_layer", 0.5) in renderer.ops
    # Colors remain fully opaque inside the group; the compositor applies alpha once.
    colors = [op[1][4] for op in renderer.ops if op[0] == "rect"]
    assert all(((color >> 24) & 0xFF) == 255 for color in colors)
    assert renderer.ops[-1] == ("restore",)
    runtime.stop()


def test_skia_renderer_uses_save_layer_with_paint_alpha():
    from novaui.native.renderer import SkiaRenderer

    calls = []

    class Paint:
        def setAlphaf(self, value):
            self.alpha = value

    class Canvas:
        def saveLayer(self, bounds, paint):
            calls.append((bounds, paint.alpha))
            return 7

    class FakeSkia:
        @staticmethod
        def Paint():
            return Paint()

    renderer = object.__new__(SkiaRenderer)
    renderer._skia = FakeSkia
    renderer._canvas = Canvas()
    assert renderer.save_layer(0.35) == 7
    assert calls == [(None, 0.35)]
    with pytest.raises(ValueError):
        renderer.save_layer(1.5)


def test_runtime_stop_discards_active_animations_without_completion():
    node = LayoutNode.box(opacity=1.0)
    runtime = NativeRuntime(lambda: node, FakeRenderer(), 120, 80)
    runtime.start()
    completed = []
    runtime.animate(node, "opacity", 0.0, duration_ms=100,
                    on_complete=lambda: completed.append(True))
    assert runtime.animations.active_count == 1
    runtime.stop()
    assert runtime.animations.active_count == 0
    assert completed == []
    assert node.opacity == 1.0


def test_layout_node_rejects_opacity_outside_zero_to_one():
    with pytest.raises(ValueError):
        LayoutNode.box(opacity=-0.1)
    with pytest.raises(ValueError):
        LayoutNode.box(opacity=1.1)
