"""Small orchestration layer joining component, layout, paint and input."""
from __future__ import annotations
from .layout import LayoutEngine, Rect
from .rendering import LayoutTreePainter
from .platform.dispatcher import InputDispatcher
from .reactivity import Component, Scheduler
from .text import TextMeasurer

class NativeRuntime:
    """Run one native component tree against an injected renderer.

    SDL3 window creation/presentation remains owned by the platform host.
    This class owns the Python-side lifecycle: build -> layout -> paint and
    normalized input dispatch. It is intentionally easy to test without SDL3
    or Skia by injecting a renderer-compatible object.
    """
    def __init__(self, build, renderer, width: float, height: float, *,
                 scheduler: Scheduler | None = None, clear_color="#FFFFFF",
                 text_measurer: TextMeasurer | None = None):
        if width <= 0 or height <= 0:
            raise ValueError("runtime dimensions must be positive")
        self.width=float(width)
        self.height=float(height)
        self.renderer=renderer
        self.clear_color=clear_color
        self.layout_engine=LayoutEngine(text_measurer=text_measurer)
        self.painter=LayoutTreePainter(renderer)
        self.scheduler=scheduler or Scheduler()
        self.component=Component(build,scheduler=self.scheduler,on_invalidate=self._component_changed)
        self.dispatcher=None
        self.frame_count=0
        self.reconcile_count=0
        self._rendering=False

    @property
    def root(self):
        return self.component.node

    def start(self):
        self.component.mount()
        return self

    def _component_changed(self, component):
        if component.node is not None:
            self.dispatcher=InputDispatcher(component.node)
        if not self._rendering:
            self.render()

    def render(self):
        if self.root is None:
            return
        if self._rendering:
            return
        self._rendering=True
        try:
            self.layout_engine.layout(self.root,Rect(0,0,self.width,self.height))
            self.painter.paint(self.root,clear_color=self.clear_color)
            self.frame_count += 1
        finally:
            self._rendering=False

    def dispatch(self,event):
        if self.dispatcher is None:
            return None
        result=self.dispatcher.dispatch(event)
        pointer=event.pointer
        if pointer is not None:
            from .platform.events import EventType
            # Pointer-up may run a widget callback that mutates the retained
            # node in place (checkbox, switch, radio group). Repaint after the
            # callback so simple controls remain immediately responsive even
            # when the host does not use a continuously-rendered frame loop.
            if (event.type in {EventType.POINTER_UP, EventType.POINTER_WHEEL} or
                (event.type == EventType.POINTER_MOTION and pointer.source == "touch")):
                self.render()
        return result

    def resize(self,width:float,height:float):
        if width<=0 or height<=0:
            raise ValueError("runtime dimensions must be positive")
        self.width=float(width)
        self.height=float(height)
        self.render()

    def stop(self):
        if self.dispatcher is not None:
            self.dispatcher.reset()
        self.dispatcher=None
        self.component.unmount()
