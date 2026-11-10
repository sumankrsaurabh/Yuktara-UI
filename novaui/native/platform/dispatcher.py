"""Pointer event dispatch for backend-neutral Yuktara UI layout trees."""
from __future__ import annotations
from dataclasses import dataclass
from ..layout.engine import hit_test
from ..layout.node import LayoutNode
from .events import EventType, InputEvent

@dataclass(frozen=True, slots=True)
class DispatchResult:
    target: LayoutNode | None = None
    previous_hover: LayoutNode | None = None
    current_hover: LayoutNode | None = None
    handled: bool = False

class InputDispatcher:
    """Dispatch pointer events to the deepest arranged node.

    Callbacks receive the normalized InputEvent. A click fires on pointer-up
    only when the pointer was pressed and released over the same node.
    """
    def __init__(self, root: LayoutNode):
        self.root=root
        self._pressed: dict[tuple[str,int],LayoutNode]={}
        self._hover: dict[tuple[str,int],LayoutNode]={}
        self._touch_scroll: dict[tuple[str,int],LayoutNode]={}
        self._touch_positions: dict[tuple[str,int],tuple[float,float]]={}

    @staticmethod
    def _key(event):
        p=event.pointer
        return (p.source,p.pointer_id)

    @staticmethod
    def _invoke(node, name, event):
        callback=getattr(node,name,None)
        if callback is not None:
            callback(event)
            return True
        return False

    def _scroll_ancestor(self,target):
        if target is None:return None
        if target.kind == "scroll":
            return target
        found=None
        def walk(node):
            nonlocal found
            if node is target:
                return True
            for child in node.children:
                if walk(child):
                    if node.kind=="scroll" and found is None: found=node
                    return True
            return False
        walk(self.root)
        return found

    @staticmethod
    def _scroll_by(node,dx,dy):
        if node is None:return False
        old=(node.scroll_x,node.scroll_y)
        node.scroll_x=min(node.max_scroll_x,max(0.0,node.scroll_x+dx))
        node.scroll_y=min(node.max_scroll_y,max(0.0,node.scroll_y+dy))
        return old!=(node.scroll_x,node.scroll_y)

    def dispatch(self,event:InputEvent)->DispatchResult:
        if event.pointer is None:return DispatchResult()
        p=event.pointer
        key=self._key(event)
        target=hit_test(self.root,p.x,p.y)
        previous=self._hover.get(key)
        if event.type==EventType.POINTER_MOTION:
            if p.source == "touch" and key in self._touch_scroll:
                previous_pos=self._touch_positions.get(key,(p.x,p.y))
                dx=previous_pos[0]-p.x; dy=previous_pos[1]-p.y
                self._scroll_by(self._touch_scroll[key],dx,dy)
                self._touch_positions[key]=(p.x,p.y)
            if target is not previous:
                if previous:self._invoke(previous,"on_pointer_leave",event)
                if target:self._invoke(target,"on_pointer_enter",event)
                if target:self._hover[key]=target
                else:self._hover.pop(key,None)
            handled=self._invoke(target,"on_pointer_move",event) if target else False
            return DispatchResult(target,previous,target,handled or target is not None)
        if event.type==EventType.POINTER_DOWN:
            if target:self._pressed[key]=target
            if p.source == "touch":
                scroll=self._scroll_ancestor(target)
                if scroll is not None:
                    self._touch_scroll[key]=scroll
                    self._touch_positions[key]=(p.x,p.y)
            handled=self._invoke(target,"on_pointer_down",event) if target else False
            return DispatchResult(target,previous,previous,handled or target is not None)
        if event.type==EventType.POINTER_UP:
            pressed=self._pressed.pop(key,None)
            self._touch_scroll.pop(key,None)
            self._touch_positions.pop(key,None)
            handled=self._invoke(target,"on_pointer_up",event) if target else False
            if target is not None and target is pressed:
                handled=self._invoke(target,"on_click",event) or handled
            return DispatchResult(target,previous,previous,handled or target is not None)
        if event.type==EventType.POINTER_WHEEL:
            scroll=self._scroll_ancestor(target)
            changed=self._scroll_by(scroll,-p.wheel_x*40.0,-p.wheel_y*40.0)
            handled=self._invoke(target,"on_wheel",event) if target else False
            return DispatchResult(target,previous,previous,handled or changed)
        return DispatchResult(target,previous,previous,False)

    def reset(self):
        self._pressed.clear()
        self._hover.clear()
        self._touch_scroll.clear()
        self._touch_positions.clear()
