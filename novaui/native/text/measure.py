"""Skia-backed text measurement and deterministic line breaking."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Any
from ..typography import FontConfig, FontResolver

@dataclass(frozen=True, slots=True)
class TextLine:
    text: str
    width: float
    baseline: float

@dataclass(frozen=True, slots=True)
class TextLayout:
    lines: tuple[TextLine, ...]
    width: float
    height: float
    ascent: float
    descent: float
    leading: float
    line_height: float

class TextMeasurer:
    """Measure text using Skia's real typeface metrics.

    The Skia module can be injected for testing. Importing this module does not
    require Skia; the dependency is loaded only when measure() is called.
    """
    def __init__(self, skia_module: Any = None, font_resolver: FontResolver | None = None):
        self._skia=skia_module
        self._resolver=font_resolver or FontResolver(skia_module)

    def _module(self):
        if self._skia is None:
            try:
                from ..dependencies import ensure_skia_python
                ensure_skia_python()
                import skia
            except Exception as exc:
                raise RuntimeError(
                    "Yuktara UI could not prepare Skia Python (skia-python 144.1) "
                    "for text measurement. Check the network connection or disable "
                    "automatic setup with YUKTARA_UI_NO_AUTO_INSTALL=1."
                ) from exc
            self._skia=skia
            if self._resolver._skia is None:
                self._resolver=FontResolver(skia)
        return self._skia

    def _font(self, config: FontConfig):
        skia=self._module()
        typeface=self._resolver.resolve(config)
        return skia.Font(typeface,config.size)

    @staticmethod
    def _font_metrics(font):
        metrics=font.getMetrics()
        ascent=abs(float(getattr(metrics,"fAscent",0.0)))
        descent=max(0.0,float(getattr(metrics,"fDescent",0.0)))
        leading=max(0.0,float(getattr(metrics,"fLeading",0.0)))
        if ascent+descent == 0:
            ascent=font.getSize()*0.8
            descent=font.getSize()*0.2
        return ascent,descent,leading

    @staticmethod
    def _split_long_word(word, max_width, measure):
        parts=[]
        current=""
        for char in word:
            candidate=current+char
            if current and measure(candidate)>max_width:
                parts.append(current)
                current=char
            else:
                current=candidate
        if current: parts.append(current)
        return parts or [""]

    def _wrap(self,text,max_width,measure):
        if max_width is None or not isfinite(max_width):
            return text.splitlines() or [""]
        if max_width <= 0:
            return [char for char in text] if text else [""]
        lines=[]
        paragraphs=text.splitlines() or [""]
        for paragraph in paragraphs:
            if paragraph=="":
                lines.append("")
                continue
            words=paragraph.split()
            current=""
            for word in words:
                candidate=word if not current else current+" "+word
                if measure(candidate)<=max_width:
                    current=candidate
                    continue
                if current:
                    lines.append(current)
                    current=""
                if measure(word)>max_width:
                    chunks=self._split_long_word(word,max_width,measure)
                    lines.extend(chunks[:-1])
                    current=chunks[-1]
                else:
                    current=word
            lines.append(current)
        return lines or [""]

    def measure(self,text: str,config: FontConfig | None = None, *,
                max_width: float | None = None, wrap: bool = True,
                line_height: float | None = None, max_lines: int | None = None) -> TextLayout:
        if not isinstance(text,str): raise TypeError("text must be a string")
        config=config or FontConfig()
        if max_width is not None and (not isfinite(max_width) or max_width<0):
            raise ValueError("max_width must be finite and non-negative")
        if line_height is not None and line_height<=0:
            raise ValueError("line_height must be positive")
        if max_lines is not None and max_lines<1:
            raise ValueError("max_lines must be at least 1")
        font=self._font(config)
        measure=lambda value: float(font.measureText(value))
        ascent,descent,leading=self._font_metrics(font)
        natural=ascent+descent+leading
        actual_line_height=float(line_height or natural)
        if wrap:
            strings=self._wrap(text,max_width,measure)
        else:
            strings=text.splitlines() or [""]
        if max_lines is not None:
            strings=strings[:max_lines]
        widths=[measure(line) for line in strings]
        lines=tuple(TextLine(line,width,i*actual_line_height+ascent)
                    for i,(line,width) in enumerate(zip(strings,widths)))
        return TextLayout(lines,max(widths,default=0.0),
                          max(1,len(lines))*actual_line_height,
                          ascent,descent,leading,actual_line_height)
