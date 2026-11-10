"""Two-phase measure/arrange layout engine for Yuktara UI."""
from __future__ import annotations
from .geometry import Alignment, Constraints, Insets, MainAxisAlignment, Rect, Size
from .node import LayoutNode, LayoutResult

class LayoutEngine:
    """Measures intrinsic sizes, then assigns absolute rectangles.

    Row/Column support fixed dimensions, padding, spacing, weighted children and
    cross-axis alignment. Stack overlays children. All calculations are in
    logical pixels; the renderer applies device scale when rasterizing.
    """
    def __init__(self, text_measurer=None):
        self.text_measurer = text_measurer

    def measure(self, node: LayoutNode, constraints: Constraints = Constraints()) -> Size:
        inner=Constraints(0,constraints.max_width,0,constraints.max_height)
        pad=node.padding
        content_c=Constraints(0,max(0,inner.max_width-pad.horizontal),
                              0,max(0,inner.max_height-pad.vertical))
        if node.kind == "text":
            if self.text_measurer is not None:
                from ..typography import FontConfig
                layout=self.text_measurer.measure(
                    node.text or "",
                    FontConfig(size=node.font_size, weight=node.font_weight),
                    max_width=content_c.max_width,
                    wrap=node.text_wrap,
                    line_height=node.text_line_height,
                    max_lines=node.text_max_lines,
                )
                node.text_layout=layout
                content=Size(layout.width, layout.height)
            else:
                content=node.intrinsic_size
        elif node.kind == "box":
            content=self._measure_box(node,content_c)
        elif node.kind in ("row","column"):
            content=self._measure_linear(node,content_c)
        elif node.kind == "scroll":
            content=self._measure_scroll(node,content_c)
        else:
            content=self._measure_stack(node,content_c)
        desired=Size(content.width+pad.horizontal,content.height+pad.vertical)
        if node.width is not None: desired=Size(node.width,desired.height)
        if node.height is not None: desired=Size(desired.width,node.height)
        node.measured_size=constraints.constrain(desired)
        return node.measured_size

    def _measure_child(self, child, c):
        return self.measure(child,c)

    def _measure_box(self,node,c):
        if not node.children: return node.intrinsic_size
        child=node.children[0]
        s=self._measure_child(child,c)
        return Size(max(node.intrinsic_size.width,s.width),max(node.intrinsic_size.height,s.height))

    def _measure_stack(self,node,c):
        sizes=[self._measure_child(ch,c) for ch in node.children]
        return Size(max([node.intrinsic_size.width]+[s.width for s in sizes]),
                    max([node.intrinsic_size.height]+[s.height for s in sizes]))

    def _measure_scroll(self,node,c):
        if not node.children:
            node.content_size=Size()
            return node.intrinsic_size
        child=node.children[0]
        max_w=float("inf") if node.scroll_axis in {"horizontal", "both"} else c.max_width
        max_h=float("inf") if node.scroll_axis in {"vertical", "both"} else c.max_height
        child_size=self.measure(child,Constraints(0,max_w,0,max_h))
        node.content_size=child_size
        return Size(min(child_size.width,c.max_width),min(child_size.height,c.max_height))

    def _measure_linear(self,node,c):
        horizontal=node.kind=="row"
        main_max=c.max_width if horizontal else c.max_height
        cross_max=c.max_height if horizontal else c.max_width
        fixed_main=0.0; cross=0.0; weighted=[]
        for child in node.children:
            if child.weight>0:
                weighted.append(child); continue
            cc=Constraints(0,main_max,0,cross_max) if horizontal else Constraints(0,cross_max,0,main_max)
            s=self.measure(child,cc)
            fixed_main += s.width if horizontal else s.height
            cross=max(cross,s.height if horizontal else s.width)
        gaps=node.spacing*max(0,len(node.children)-1)
        total=fixed_main+gaps
        remaining=max(0,main_max-total) if main_max != float("inf") else 0
        weight_sum=sum(ch.weight for ch in weighted)
        for child in weighted:
            allocation=remaining*child.weight/weight_sum if weight_sum else 0
            cc=Constraints(allocation,allocation,0,cross_max) if horizontal else Constraints(0,cross_max,allocation,allocation)
            s=self.measure(child,cc)
            total += s.width if horizontal else s.height
            cross=max(cross,s.height if horizontal else s.width)
        if horizontal: return Size(total,cross)
        return Size(cross,total)

    def arrange(self,node:LayoutNode,bounds:Rect)->LayoutResult:
        node.bounds=bounds
        pad=node.padding
        content=bounds.inset(pad)
        node.content_bounds=content
        if node.kind=="box":
            for child in node.children[:1]:
                self._arrange_aligned(child,content,node.align)
        elif node.kind=="stack":
            for child in node.children: self._arrange_aligned(child,content,node.align)
        elif node.kind=="scroll":
            node.max_scroll_x=max(0.0,node.content_size.width-content.width) if node.scroll_axis in {"horizontal", "both"} else 0.0
            node.max_scroll_y=max(0.0,node.content_size.height-content.height) if node.scroll_axis in {"vertical", "both"} else 0.0
            node.scroll_x=min(node.scroll_x,node.max_scroll_x)
            node.scroll_y=min(node.scroll_y,node.max_scroll_y)
            if node.children:
                child=node.children[0]
                cw=max(content.width,node.content_size.width)
                ch=max(content.height,node.content_size.height)
                self.arrange(child,Rect(content.x-node.scroll_x,content.y-node.scroll_y,cw,ch))
        elif node.kind in ("row","column"):
            self._arrange_linear(node,content)
        return LayoutResult(node.measured_size,bounds)

    def _arrange_aligned(self,child,area,align):
        s=child.measured_size
        if align==Alignment.STRETCH: w,h=area.width,area.height
        else: w,h=min(s.width,area.width),min(s.height,area.height)
        x=area.x if align in (Alignment.START,Alignment.STRETCH) else area.x+(area.width-w)/2 if align==Alignment.CENTER else area.right-w
        y=area.y if align in (Alignment.START,Alignment.STRETCH) else area.y+(area.height-h)/2 if align==Alignment.CENTER else area.bottom-h
        self.arrange(child,Rect(x,y,w,h))

    def _arrange_linear(self,node,area):
        horizontal=node.kind=="row"
        children=node.children
        if not children:return
        main_extent=area.width if horizontal else area.height
        cross_extent=area.height if horizontal else area.width
        sizes=[ch.measured_size for ch in children]
        used=sum((s.width if horizontal else s.height) for s in sizes)
        base_gap=node.spacing
        extra=max(0,main_extent-used-base_gap*(len(children)-1))
        ma=node.main_align
        if ma==MainAxisAlignment.CENTER: offset=extra/2; gap=base_gap
        elif ma==MainAxisAlignment.END: offset=extra; gap=base_gap
        elif ma==MainAxisAlignment.SPACE_BETWEEN and len(children)>1: offset=0; gap=base_gap+extra/(len(children)-1)
        elif ma==MainAxisAlignment.SPACE_AROUND: gap=base_gap+extra/len(children); offset=(gap-base_gap)/2
        elif ma==MainAxisAlignment.SPACE_EVENLY: gap=base_gap+extra/(len(children)+1); offset=gap-base_gap
        else: offset=0; gap=base_gap
        cursor=(area.x if horizontal else area.y)+offset
        for child,s in zip(children,sizes):
            cm=s.width if horizontal else s.height
            cc=s.height if horizontal else s.width
            ca=node.cross_align
            if ca==Alignment.STRETCH: cc=cross_extent
            else: cc=min(cc,cross_extent)
            if ca in (Alignment.START,Alignment.STRETCH): cross_pos=area.y if horizontal else area.x
            elif ca==Alignment.CENTER: cross_pos=(area.y if horizontal else area.x)+(cross_extent-cc)/2
            else: cross_pos=(area.bottom-cc if horizontal else area.right-cc)
            rect=Rect(cursor,cross_pos,cm,cc) if horizontal else Rect(cross_pos,cursor,cc,cm)
            self.arrange(child,rect)
            cursor += cm+gap

    def layout(self,root:LayoutNode,bounds:Rect)->LayoutResult:
        self.measure(root,Constraints(bounds.width,bounds.width,bounds.height,bounds.height))
        return self.arrange(root,bounds)

def hit_test(root: LayoutNode, x: float, y: float) -> LayoutNode | None:
    """Return deepest topmost visible node, respecting scroll viewport clips."""
    from .geometry import Point
    point=Point(x,y)
    def visit(node, clip=None):
        if clip is not None and not clip.contains(point):
            return None
        if node.kind == "scroll":
            viewport=node.content_bounds
            if not viewport.contains(point):
                return node if node.bounds.contains(point) else None
            child_clip=viewport if clip is None else _intersect(clip,viewport)
        else:
            child_clip=clip
        for child in reversed(node.children):
            hit=visit(child,child_clip)
            if hit is not None:
                return hit
        return node if node.bounds.contains(point) else None
    return visit(root)

def _intersect(a: Rect, b: Rect) -> Rect:
    left=max(a.x,b.x); top=max(a.y,b.y)
    right=min(a.right,b.right); bottom=min(a.bottom,b.bottom)
    return Rect(left,top,max(0.0,right-left),max(0.0,bottom-top))
