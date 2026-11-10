"""Paint arranged Yuktara UI layout trees through the SkiaRenderer interface."""
from __future__ import annotations
from ..typography import FontConfig

def parse_color(value):
    """Accept ARGB integers or #RGB/#RRGGBB/#AARRGGBB strings."""
    if value is None: return None
    if isinstance(value,int): return value if value > 0xFFFFFF else (0xFF000000 | value)
    if not isinstance(value,str): raise TypeError("Color must be an ARGB integer or hex string")
    raw=value.strip().lstrip("#")
    if len(raw)==3: raw="".join(ch*2 for ch in raw)
    if len(raw)==6: raw="FF"+raw
    if len(raw)!=8: raise ValueError("Hex colors must be #RGB, #RRGGBB or #AARRGGBB")
    return int(raw,16)

class LayoutTreePainter:
    """Paint backgrounds and text in tree order; children appear above parents."""
    def __init__(self, renderer, *, default_text_color=0xFF202735):
        self.renderer=renderer
        self.default_text_color=default_text_color

    def paint(self, root, *, clear_color=None):
        if clear_color is not None: self.renderer.clear(parse_color(clear_color))
        self._paint_node(root)

    def _paint_node(self,node):
        r=node.bounds
        if node.background is not None and r.width>0 and r.height>0:
            self.renderer.draw_rect(r.x,r.y,r.width,r.height,
                                    parse_color(node.background),radius=node.radius)
        if (node.border_color is not None and node.border_width > 0 and
                r.width > 0 and r.height > 0):
            draw_stroke = getattr(self.renderer, "draw_stroke_rect", None)
            if callable(draw_stroke):
                inset = node.border_width / 2
                draw_stroke(r.x + inset, r.y + inset,
                            max(0.0, r.width - node.border_width),
                            max(0.0, r.height - node.border_width),
                            parse_color(node.border_color),
                            stroke_width=node.border_width, radius=node.radius)
        if node.text:
            font=FontConfig(size=node.font_size,weight=node.font_weight)
            layout=node.text_layout
            if layout is not None:
                for line in layout.lines:
                    if node.text_align == "center":
                        x=r.x+(r.width-line.width)/2
                    elif node.text_align == "end":
                        x=r.right-line.width
                    else:
                        x=r.x
                    self.renderer.draw_text(line.text,x,r.y+line.baseline,
                        color=parse_color(node.text_color or self.default_text_color),font=font)
            else:
                baseline=r.y+(r.height+node.font_size*0.72)/2
                self.renderer.draw_text(node.text,r.x,baseline,
                    color=parse_color(node.text_color or self.default_text_color),font=font)
        if node.kind == "scroll" and hasattr(self.renderer, "save"):
            viewport=node.content_bounds
            self.renderer.save()
            self.renderer.clip_rect(viewport.x,viewport.y,viewport.width,viewport.height)
            for child in node.children:
                self._paint_node(child)
            self.renderer.restore()
            self._paint_scrollbar(node)
        else:
            for child in node.children:
                self._paint_node(child)

    def _paint_scrollbar(self,node):
        """Paint a subtle vertical/horizontal thumb when content overflows."""
        if not hasattr(self.renderer,"draw_rect"):
            return
        track=0x1F64748B
        thumb=0x9964748B
        v=node.content_bounds
        if node.max_scroll_y>0 and v.height>0:
            thickness=4.0
            thumb_h=max(18.0,v.height*v.height/node.content_size.height)
            travel=max(0.0,v.height-thumb_h)
            y=v.y+(node.scroll_y/node.max_scroll_y)*travel
            self.renderer.draw_rect(v.right-thickness,y,thickness,thumb_h,thumb,radius=2)
        if node.max_scroll_x>0 and v.width>0:
            thickness=4.0
            thumb_w=max(18.0,v.width*v.width/node.content_size.width)
            travel=max(0.0,v.width-thumb_w)
            x=v.x+(node.scroll_x/node.max_scroll_x)*travel
            self.renderer.draw_rect(x,v.bottom-thickness,thumb_w,thickness,thumb,radius=2)
