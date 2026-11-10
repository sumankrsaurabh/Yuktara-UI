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

def apply_opacity(color, opacity):
    """Multiply an ARGB color's alpha channel by an inherited opacity."""
    if color is None:
        return None
    value = parse_color(color)
    alpha = (value >> 24) & 0xFF
    alpha = max(0, min(255, round(alpha * max(0.0, min(1.0, opacity)))))
    return (value & 0x00FFFFFF) | (alpha << 24)


class LayoutTreePainter:
    """Paint backgrounds and text in tree order; children appear above parents."""
    def __init__(self, renderer, *, default_text_color=0xFF202735):
        self.renderer=renderer
        self.default_text_color=default_text_color

    def paint(self, root, *, clear_color=None):
        if clear_color is not None: self.renderer.clear(parse_color(clear_color))
        self._paint_node(root)

    def _paint_node(self,node,parent_opacity=1.0):
        r=node.bounds
        save_layer = getattr(self.renderer, "save_layer", None)
        layered = callable(save_layer) and node.opacity < 1.0
        if layered:
            save_layer(node.opacity)
        opacity = parent_opacity if layered or callable(save_layer) else parent_opacity * node.opacity
        if node.background is not None and r.width>0 and r.height>0:
            self.renderer.draw_rect(r.x,r.y,r.width,r.height,
                                    apply_opacity(node.background,opacity),radius=node.radius)
        if (node.border_color is not None and node.border_width > 0 and
                r.width > 0 and r.height > 0):
            draw_stroke = getattr(self.renderer, "draw_stroke_rect", None)
            if callable(draw_stroke):
                inset = node.border_width / 2
                draw_stroke(r.x + inset, r.y + inset,
                            max(0.0, r.width - node.border_width),
                            max(0.0, r.height - node.border_width),
                            apply_opacity(node.border_color,opacity),
                            stroke_width=node.border_width, radius=node.radius)
        if node.paint_callback is not None:
            node.paint_callback(self.renderer, node)
        if node.text is not None:
            font = FontConfig(family=node.font_family, size=node.font_size, weight=node.font_weight)
            layout = node.text_layout
            area = node.content_bounds
            clip = bool(node.text_clip and callable(getattr(self.renderer, "save", None))
                        and callable(getattr(self.renderer, "clip_rect", None)))
            if clip:
                self.renderer.save()
                self.renderer.clip_rect(area.x, area.y, area.width, area.height)
            origin_x = area.x - node.text_scroll_x
            origin_y = area.y - node.text_scroll_y
            self._paint_text_selection(node, opacity, layout, origin_x, origin_y)
            if layout is not None:
                for line_index, line in enumerate(layout.lines):
                    if line.alignment == "inherit":
                        if node.text_align == "center":
                            base_x = area.x + (area.width - line.width) / 2
                        elif node.text_align == "end":
                            base_x = area.right - line.width
                        else:
                            base_x = area.x
                    else:
                        base_x = area.x
                    x = base_x + line.x_offset - node.text_scroll_x
                    default_color = apply_opacity(node.text_color or self.default_text_color, opacity)
                    if line.paint_runs:
                        self._paint_text_runs(line, x, origin_y, default_color, opacity)
                    else:
                        color = default_color
                        draw_glyph_run = getattr(self.renderer, "draw_glyph_run", None)
                        if line.glyph_runs and callable(draw_glyph_run):
                            for glyph_run in line.glyph_runs:
                                draw_glyph_run(
                                    glyph_run.glyph_ids, glyph_run.positions,
                                    x, origin_y + line.baseline,
                                    color=color, typeface=glyph_run.typeface,
                                    size=glyph_run.font_size,
                                )
                        elif line.glyph_runs:
                            raise RuntimeError(
                                "The active renderer cannot draw shaped glyph runs. "
                                "Use SkiaRenderer or a renderer implementing draw_glyph_run()."
                            )
                        else:
                            self.renderer.draw_text(
                                line.text, x, origin_y + line.baseline,
                                color=color, font=font,
                            )
                    if line_index == next((p.first_line for p in layout.paragraphs
                                           if p.first_line == line_index and p.style.marker), -1):
                        paragraph = next(p for p in layout.paragraphs
                                         if p.first_line == line_index and p.style.marker)
                        marker_x = area.x + max(0.0, paragraph.style.effective_left_indent - paragraph.style.marker_indent) - node.text_scroll_x
                        marker_color = apply_opacity(
                            paragraph.style.marker_color if paragraph.style.marker_color is not None
                            else node.text_color or self.default_text_color, opacity
                        )
                        self.renderer.draw_text(
                            paragraph.style.marker, marker_x, origin_y + line.baseline,
                            color=marker_color, font=font,
                        )
            elif node.text:
                baseline = area.y + (area.height + node.font_size * 0.72) / 2 - node.text_scroll_y
                self.renderer.draw_text(
                    node.text, origin_x, baseline,
                    color=apply_opacity(node.text_color or self.default_text_color, opacity),
                    font=font,
                )
            self._paint_text_composition(node, opacity, layout, origin_x, origin_y)
            self._paint_text_caret(node, opacity, layout, origin_x, origin_y)
            if clip:
                self.renderer.restore()
        if node.kind == "scroll" and hasattr(self.renderer, "save"):
            viewport=node.content_bounds
            self.renderer.save()
            self.renderer.clip_rect(viewport.x,viewport.y,viewport.width,viewport.height)
            for child in node.children:
                self._paint_node(child,opacity if not callable(save_layer) else 1.0)
            self.renderer.restore()
            self._paint_scrollbar(node,opacity)
        else:
            for child in node.children:
                self._paint_node(child,opacity if not callable(save_layer) else 1.0)
        self._paint_focus_ring(node,opacity)
        if layered:
            self.renderer.restore()


    def _paint_text_runs(self, line, line_x, origin_y, default_color, opacity):
        """Render per-span typography while retaining shared line geometry."""
        draw_glyph_run = getattr(self.renderer, "draw_glyph_run", None)
        draw_rect = getattr(self.renderer, "draw_rect", None)
        draw_stroke = getattr(self.renderer, "draw_stroke_rect", None)
        baseline = origin_y + line.baseline
        for run in line.paint_runs:
            run_x = line_x + run.x
            color = apply_opacity(run.color, opacity) if run.color is not None else default_color
            if run.background is not None and callable(draw_rect):
                draw_rect(run_x, origin_y + line.top,
                          run.width, line.height or 1.0,
                          apply_opacity(run.background, opacity))
            if run.glyph_runs:
                if not callable(draw_glyph_run):
                    raise RuntimeError(
                        "The active renderer cannot draw shaped glyph runs. "
                        "Use SkiaRenderer or a renderer implementing draw_glyph_run()."
                    )
                for glyph_run in run.glyph_runs:
                    draw_glyph_run(
                        glyph_run.glyph_ids, glyph_run.positions,
                        line_x, baseline, color=color,
                        typeface=glyph_run.typeface, size=glyph_run.font_size,
                    )
            else:
                self.renderer.draw_text(
                    run.text, run_x, baseline, color=color, font=run.font_config,
                )
            if run.underline and callable(draw_rect):
                underline_y = baseline + max(1.0, run.font_config.size * 0.08)
                draw_rect(run_x, underline_y, run.width,
                          max(1.0, run.font_config.size / 16.0), color)

    def _paint_text_selection(self, node, opacity, layout, origin_x, origin_y):
        """Paint measured selection backgrounds below the glyphs."""
        draw_rect = getattr(self.renderer, "draw_rect", None)
        selection = node.text_selection
        if not callable(draw_rect) or opacity <= 0 or selection is None or selection[0] == selection[1]:
            return
        if layout is not None and callable(getattr(layout, "selection_rects", None)):
            rects = layout.selection_rects(*selection)
            for x, y, width, height in rects:
                if width > 0 and height > 0:
                    draw_rect(origin_x + x, origin_y + y, width, height,
                              apply_opacity(node.text_selection_color, opacity))
        else:
            start, end = sorted(selection)
            char_width = node.font_size * 0.55
            draw_rect(origin_x + start * char_width, origin_y,
                      max(0.0, (end - start) * char_width),
                      max(node.font_size * 1.35, 1.0),
                      apply_opacity(node.text_selection_color, opacity))

    def _paint_text_composition(self, node, opacity, layout, origin_x, origin_y):
        """Underline the active IME pre-edit range without changing committed text."""
        draw_rect = getattr(self.renderer, "draw_rect", None)
        composition = node.text_composition
        if (not callable(draw_rect) or opacity <= 0 or composition is None
                or composition[0] == composition[1]):
            return
        color = apply_opacity(node.text_composition_color, opacity)
        if layout is not None and callable(getattr(layout, "selection_rects", None)):
            for x, y, width, height in layout.selection_rects(*composition):
                if width > 0 and height > 0:
                    underline_y = origin_y + y + max(0.0, height - 1.5)
                    draw_rect(origin_x + x, underline_y, width, 1.5, color)
            return
        start, end = composition
        char_width = node.font_size * 0.55
        line_height = max(node.font_size * 1.35, 1.0)
        draw_rect(
            origin_x + start * char_width,
            origin_y + line_height - 1.5,
            max(0.0, (end - start) * char_width),
            1.5,
            color,
        )

    def _paint_text_caret(self, node, opacity, layout, origin_x, origin_y):
        """Paint the insertion caret after glyphs so it remains visible."""
        draw_rect = getattr(self.renderer, "draw_rect", None)
        if (not callable(draw_rect) or opacity <= 0 or not node.accessibility_focused
                or node.text_cursor is None):
            return
        if layout is not None and callable(getattr(layout, "caret_position", None)):
            x, y, line_index = layout.caret_position(node.text_cursor)
            height = (layout.lines[line_index].height or layout.line_height)
            height = min(height, max(1.0, node.bounds.height - (y - node.text_scroll_y)))
        else:
            text = node.text or ""
            cursor = min(len(text), node.text_cursor)
            before = text[:cursor]
            line_index = before.count("\n")
            line_text = before.rsplit("\n", 1)[-1]
            x = len(line_text) * node.font_size * 0.55
            y = line_index * node.font_size * 1.35
            height = node.font_size * 1.35
        draw_rect(origin_x + x, origin_y + y, node.text_caret_width,
                  max(1.0, height), apply_opacity(node.text_caret_color, opacity))

    def _paint_focus_ring(self,node,opacity):
        draw_stroke = getattr(self.renderer,"draw_stroke_rect",None)
        if not node.accessibility_focused or node.focus_ring_width <= 0 or not callable(draw_stroke):
            return
        r=node.bounds
        if r.width <= 0 or r.height <= 0 or opacity <= 0:
            return
        inset=node.focus_ring_width/2
        draw_stroke(r.x+inset,r.y+inset,max(0.0,r.width-node.focus_ring_width),
                    max(0.0,r.height-node.focus_ring_width),
                    apply_opacity(node.focus_ring_color,opacity),
                    stroke_width=node.focus_ring_width,radius=node.radius+inset)

    def _paint_scrollbar(self,node,opacity=1.0):
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
            self.renderer.draw_rect(v.right-thickness,y,thickness,apply_opacity(thumb,opacity),radius=2)
        if node.max_scroll_x>0 and v.width>0:
            thickness=4.0
            thumb_w=max(18.0,v.width*v.width/node.content_size.width)
            travel=max(0.0,v.width-thumb_w)
            x=v.x+(node.scroll_x/node.max_scroll_x)*travel
            self.renderer.draw_rect(x,v.bottom-thickness,thumb_w,thickness,apply_opacity(thumb,opacity),radius=2)
