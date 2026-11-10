import pytest

from novaui.native.layout import LayoutNode, Size
from novaui.native.reactivity import Component, Scheduler, State
from novaui.native.runtime import NativeRuntime
from novaui.native.platform.events import EventType, InputEvent, PointerEvent

class FakeRenderer:
    def __init__(self): self.ops=[]
    def clear(self,color): self.ops.append(("clear",color))
    def draw_rect(self,*args,**kwargs): self.ops.append(("rect",args,kwargs))
    def draw_text(self,*args,**kwargs): self.ops.append(("text",args,kwargs))

def test_state_only_notifies_when_value_changes():
    state=State(1); seen=[]
    sub=state.subscribe(lambda new,old:seen.append((old,new)))
    state.value=1
    state.update(lambda x:x+1)
    assert seen==[(1,2)]
    sub.cancel(); state.value=3
    assert seen==[(1,2)]

def test_scheduler_batches_and_deduplicates_by_key():
    scheduler=Scheduler(); seen=[]; key=object()
    with scheduler.batch():
        scheduler.schedule(key,lambda:seen.append("first"))
        scheduler.schedule(key,lambda:seen.append("latest"))
        scheduler.schedule("other",lambda:seen.append("other"))
        assert seen==[]
    assert seen==["latest","other"]

def test_component_rebuilds_on_bound_state_and_unsubscribes_on_unmount():
    value=State("before"); builds=[]
    c=Component(lambda: builds.append(value.value) or LayoutNode("text",text=value.value))
    c.mount(); c.bind_state(value)
    value.value="after"
    assert builds==["before","after"]
    c.unmount(); value.value="ignored"
    assert builds==["before","after"]

def test_runtime_renders_and_reacts_to_state():
    state=State("Initial")
    renderer=FakeRenderer()
    runtime=NativeRuntime(lambda: LayoutNode("text",text=state.value,background="#eeeeee"),
                          renderer,320,200)
    runtime.component.bind_state(state)
    runtime.start()
    assert runtime.frame_count==1
    assert any(op[0]=="text" and op[1][0]=="Initial" for op in renderer.ops)
    state.value="Updated"
    assert runtime.frame_count==2
    assert any(op[0]=="text" and op[1][0]=="Updated" for op in renderer.ops)
    runtime.resize(640,400)
    assert runtime.root.bounds.width==640
    runtime.stop()


def test_pointer_up_repaints_after_native_widget_mutates_node():
    from novaui.native import Checkbox
    checkbox = Checkbox("Keep signed in")
    renderer = FakeRenderer()
    runtime = NativeRuntime(checkbox.build, renderer, 200, 80)
    runtime.start()
    initial_frames = runtime.frame_count
    down = InputEvent(EventType.POINTER_DOWN, pointer=PointerEvent(x=5, y=5, button=1))
    up = InputEvent(EventType.POINTER_UP, pointer=PointerEvent(x=5, y=5, button=1))
    runtime.dispatch(down)
    runtime.dispatch(up)
    assert checkbox.checked is True
    assert runtime.frame_count == initial_frames + 1
    assert any(op[0] == "text" and "☑" in op[1][0] for op in renderer.ops)
    runtime.stop()


def test_runtime_keeps_dispatcher_and_focus_across_component_rebuild():
    state = State("before")
    renderer = FakeRenderer()

    def build():
        return LayoutNode.column(
            LayoutNode("box", key="action", accessibility_role="button",
                       accessibility_label=state.value,
                       on_click=lambda _event: None),
            LayoutNode("text", text=state.value, key="label"),
            key="root",
        )

    runtime = NativeRuntime(build, renderer, 240, 100)
    runtime.component.bind_state(state)
    runtime.start()
    dispatcher = runtime.dispatcher
    focused = runtime.root.children[0]
    runtime.dispatcher._set_focus(focused)
    state.value = "after"

    assert runtime.dispatcher is dispatcher
    assert runtime.dispatcher.focused is focused
    assert focused.accessibility_focused is True
    assert focused.accessibility_label == "after"
    runtime.stop()


def test_runtime_defers_background_state_updates_until_ui_thread_flush():
    from threading import Thread, get_ident

    state = State("before")
    renderer = FakeRenderer()
    runtime = NativeRuntime(lambda: LayoutNode("text", text=state.value),
                            renderer, 200, 80)
    runtime.component.bind_state(state)
    runtime.start()
    initial_frames = runtime.frame_count
    errors = []

    def update_from_worker():
        try:
            state.value = "after"
        except Exception as exc:  # pragma: no cover - failure is asserted below
            errors.append(exc)

    worker = Thread(target=update_from_worker)
    worker.start()
    worker.join()

    assert errors == []
    assert runtime.root.text == "before"
    assert runtime.frame_count == initial_frames
    assert runtime.scheduler.pending_count == 1

    runtime.process_pending()
    assert runtime.root.text == "after"
    assert runtime.frame_count == initial_frames + 1
    runtime.stop()


def test_runtime_scales_normalized_touch_coordinates_to_logical_pixels():
    received = []
    node = LayoutNode("box", on_pointer_down=lambda event: received.append(
        (event.pointer.x, event.pointer.y,
         event.pointer.delta_x, event.pointer.delta_y)
    ))
    runtime = NativeRuntime(lambda: node, FakeRenderer(), 300, 200)
    runtime.start()
    event = InputEvent(
        EventType.POINTER_DOWN,
        pointer=PointerEvent(
            x=0.25, y=0.5, delta_x=0.1, delta_y=0.2,
            source="touch", pointer_id=8, button=1,
        ),
    )
    runtime.dispatch(event)
    assert received == [(75.0, 100.0, 30.0, 40.0)]
    runtime.stop()


def test_runtime_handles_logical_and_pixel_resize_events_separately():
    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 320, 200)
    runtime.start()
    runtime.handle_event(InputEvent(
        EventType.WINDOW_RESIZED,
        window=__import__("novaui.native.platform.events", fromlist=["WindowEvent"]).WindowEvent(800, 600),
    ))
    assert (runtime.width, runtime.height) == (800.0, 600.0)
    assert (runtime.pixel_width, runtime.pixel_height) == (800, 600)
    runtime.handle_event(InputEvent(
        EventType.WINDOW_PIXEL_SIZE_CHANGED,
        window=__import__("novaui.native.platform.events", fromlist=["WindowEvent"]).WindowEvent(1600, 1200),
    ))
    assert (runtime.pixel_width, runtime.pixel_height) == (1600, 1200)
    assert runtime.scale_x == 2.0
    assert runtime.scale_y == 2.0
    runtime.stop()


def test_runtime_resets_pointer_capture_and_focus_when_window_loses_focus():
    from novaui.native.platform.events import WindowEvent

    node = LayoutNode("box", accessibility_role="button", on_click=lambda _event: None)
    runtime = NativeRuntime(lambda: node, FakeRenderer(), 100, 80)
    runtime.start()
    runtime.dispatcher._set_focus(node)
    runtime.dispatcher._pressed[("mouse", 0)] = node
    runtime.handle_event(InputEvent(EventType.WINDOW_FOCUS_LOST,
                                    window=WindowEvent(window_id=1)))
    assert runtime.window_focused is False
    assert runtime.dispatcher.focused is None
    assert runtime.dispatcher.has_capture is False
    runtime.stop()


def test_bind_state_apply_callback_is_marshaled_to_runtime_ui_thread():
    from threading import Thread, get_ident

    state = State("before")
    renderer = FakeRenderer()
    callback_threads = []
    applied = []
    runtime = NativeRuntime(
        lambda: LayoutNode("text", text=state.value), renderer, 160, 60
    )
    runtime.component.bind_state(
        state,
        apply=lambda new, old: (callback_threads.append(get_ident()), applied.append((old, new))),
    )
    runtime.start()
    owner = get_ident()

    worker = Thread(target=lambda: setattr(state, "value", "after"))
    worker.start()
    worker.join()

    assert applied == []
    runtime.process_pending()
    assert applied == [("before", "after")]
    assert callback_threads == [owner]
    assert runtime.root.text == "after"
    runtime.stop()


def test_runtime_can_restart_on_same_ui_thread_and_restores_managers():
    from novaui.native import Toast

    renderer = FakeRenderer()
    runtime = NativeRuntime(lambda: LayoutNode("box"), renderer, 160, 80)
    runtime.start()
    first_dispatcher = runtime.dispatcher
    runtime.stop()
    runtime.start()

    assert runtime.dispatcher is not None
    assert runtime.dispatcher is not first_dispatcher
    # Both manager callbacks were reattached during restart. A toast update
    # must trigger a new frame rather than silently changing hidden state.
    initial = runtime.frame_count
    runtime.overlays.show_toast(Toast("Restarted"))
    assert runtime.frame_count == initial + 1
    runtime.stop()


def test_scheduler_preserves_later_callbacks_when_one_callback_raises():
    import pytest

    scheduler = Scheduler()
    seen = []

    def fail():
        raise RuntimeError("callback failed")

    with pytest.raises(RuntimeError, match="callback failed"):
        with scheduler.batch():
            scheduler.schedule("fail", fail)
            scheduler.schedule("later", lambda: seen.append("later"))

    assert seen == []
    assert scheduler.pending_count == 1
    assert scheduler.flush() == 1
    assert seen == ["later"]


def test_runtime_start_does_not_claim_thread_when_scheduler_binding_fails():
    import pytest
    from threading import get_ident

    scheduler = Scheduler()
    scheduler.bind_owner_thread(get_ident() + 10_000)
    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 100, 80,
                            scheduler=scheduler)

    with pytest.raises(RuntimeError, match="already bound"):
        runtime.start()

    assert runtime.owner_thread_id is None
    assert runtime.root is None


def test_runtime_restart_clears_quit_state_and_restores_window_focus():
    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 100, 80)
    runtime.start()
    runtime.handle_event(InputEvent(EventType.QUIT))
    runtime.window_focused = False
    runtime.stop()
    runtime.start()

    assert runtime.quit_requested is False
    assert runtime.window_focused is True
    runtime.stop()


@pytest.mark.parametrize(
    "width,height,error",
    [
        (0, 100, ValueError),
        (-1, 100, ValueError),
        (float("nan"), 100, ValueError),
        (float("inf"), 100, ValueError),
        (True, 100, TypeError),
        ("400", 100, TypeError),
    ],
)
def test_runtime_rejects_invalid_resize_dimensions_without_mutating_state(
    width, height, error
):
    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 320, 200)

    with pytest.raises(error):
        runtime.resize(width, height)

    assert (runtime.width, runtime.height) == (320.0, 200.0)
    assert (runtime.pixel_width, runtime.pixel_height) == (320, 200)


@pytest.mark.parametrize(
    "pixel_width,pixel_height,error",
    [
        (0, 800, ValueError),
        (1200, -1, ValueError),
        (1200.5, 800, TypeError),
        (1200, True, TypeError),
    ],
)
def test_runtime_validates_backing_pixel_dimensions_atomically(
    pixel_width, pixel_height, error
):
    runtime = NativeRuntime(lambda: LayoutNode("box"), FakeRenderer(), 320, 200)

    with pytest.raises(error):
        runtime.resize(640, 400, pixel_width=pixel_width, pixel_height=pixel_height)

    assert (runtime.width, runtime.height) == (320.0, 200.0)
    assert (runtime.pixel_width, runtime.pixel_height) == (320, 200)
