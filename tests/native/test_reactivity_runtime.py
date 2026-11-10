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
