"""Optional HarfBuzz shaping for native text rendering.

The base framework remains dependency-free.  Install the ``shaping`` extra
and provide font files in :class:`FontConfig` to enable glyph shaping.  The
adapter deliberately keeps source offsets in Python code-point indices and
returns glyph IDs/positions for direct Skia drawing.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import unicodedata


@dataclass(frozen=True, slots=True)
class ShapedCluster:
    """Visual geometry for one HarfBuzz cluster, with logical source offsets."""

    start: int
    end: int
    x: float
    width: float
    rtl: bool = False


@dataclass(frozen=True, slots=True)
class ShapedGlyphRun:
    """A glyph run ready for direct rendering with its resolved typeface."""

    start: int
    end: int
    font_family: str
    typeface: Any
    font_size: float
    direction: str
    glyph_ids: tuple[int, ...]
    positions: tuple[tuple[float, float], ...]
    clusters: tuple[ShapedCluster, ...]
    width: float


@dataclass(frozen=True, slots=True)
class ShapedText:
    """Shaped paragraph data in visual run order."""

    runs: tuple[ShapedGlyphRun, ...]
    clusters: tuple[ShapedCluster, ...]
    width: float


class HarfBuzzShaper:
    """Shape configured font files through the optional ``uharfbuzz`` module.

    ``FontConfig.font_path`` or ``FontConfig.font_files`` must point at the
    actual font resource used by each fallback family.  HarfBuzz glyph IDs are
    font-specific, so silently substituting a different file is unsafe.

    Mixed-direction handling here groups strong Unicode bidi classes and
    orders directional runs for a simple paragraph base direction.  Full
    UAX #9 embedding/isolate processing remains a separate bidi-engine task.
    """

    def __init__(self, harfbuzz_module=None):
        self._hb = harfbuzz_module
        self._faces: dict[str, tuple[Any, Any, int]] = {}

    def _module(self):
        if self._hb is None:
            try:
                import uharfbuzz as hb
            except ImportError as exc:
                raise RuntimeError(
                    "HarfBuzz shaping requires the optional 'uharfbuzz' package. "
                    "Install it with: pip install 'yuktara-ui[shaping]'"
                ) from exc
            self._hb = hb
        return self._hb

    def _font(self, path: str):
        path = str(Path(path).expanduser().resolve())
        cached = self._faces.get(path)
        if cached is not None:
            return cached
        if not Path(path).is_file():
            raise FileNotFoundError(f"Configured shaping font does not exist: {path}")
        hb = self._module()
        blob = hb.Blob.from_file_path(path)
        face = hb.Face(blob)
        font = hb.Font(face)
        set_funcs = getattr(hb, "ot_font_set_funcs", None)
        if callable(set_funcs):
            set_funcs(font)
        upem = int(getattr(face, "upem", 0) or 1000)
        font.scale = (upem, upem)
        result = (face, font, upem)
        self._faces[path] = result
        return result

    @staticmethod
    def _strong_direction(cluster: str) -> str | None:
        for char in cluster:
            bidi = unicodedata.bidirectional(char)
            if bidi in {"R", "AL", "AN"}:
                return "rtl"
            if bidi == "L":
                return "ltr"
        return None

    @classmethod
    def _directional_spans(cls, text: str, base_direction: str):
        # Import locally to avoid a dependency cycle with grapheme segmentation.
        from .measure import grapheme_spans

        spans = grapheme_spans(text)
        directions: list[str | None] = [
            cls._strong_direction(text[start:end]) for start, end in spans
        ]
        previous = base_direction
        for index, direction in enumerate(directions):
            if direction is None:
                directions[index] = previous
            else:
                previous = direction
        result = []
        for (start, end), direction in zip(spans, directions):
            direction = direction or base_direction
            if result and result[-1][2] == direction and result[-1][1] == start:
                result[-1] = (result[-1][0], end, direction)
            else:
                result.append((start, end, direction))
        return result

    @classmethod
    def _base_direction(cls, text: str, requested: str = "auto") -> str:
        if requested in {"ltr", "rtl"}:
            return requested
        for char in text:
            bidi = unicodedata.bidirectional(char)
            if bidi == "L":
                return "ltr"
            if bidi in {"R", "AL"}:
                return "rtl"
        return "ltr"

    def _shape_segment(self, text: str, *, path: str, size: float,
                       direction: str, font_family: str, typeface: Any,
                       source_start: int) -> ShapedGlyphRun:
        hb = self._module()
        face, font, upem = self._font(path)
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.direction = direction
        cluster_level = getattr(hb, "BufferClusterLevel", None)
        if cluster_level is not None:
            value = getattr(cluster_level, "MONOTONE_GRAPHEMES", None)
            if value is not None:
                buffer.cluster_level = value
        buffer.guess_segment_properties()
        hb.shape(font, buffer, {"kern": True, "liga": True, "clig": True, "calt": True})
        infos = tuple(buffer.glyph_infos or ())
        positions = tuple(buffer.glyph_positions or ())
        if len(infos) != len(positions):
            raise RuntimeError("HarfBuzz returned mismatched glyph and position arrays")
        scale = float(size) / float(upem)
        cursor_x = 0.0
        glyph_ids: list[int] = []
        glyph_positions: list[tuple[float, float]] = []
        glyph_clusters: list[tuple[int, float, float]] = []
        for info, position in zip(infos, positions):
            advance_x = float(position.x_advance) * scale
            offset_x = float(position.x_offset) * scale
            offset_y = float(position.y_offset) * scale
            glyph_ids.append(int(info.codepoint))
            glyph_positions.append((cursor_x + offset_x, -offset_y))
            glyph_clusters.append((int(info.cluster), cursor_x, cursor_x + advance_x))
            cursor_x += advance_x
        # Normalize runs whose font direction uses negative advances.
        min_x = min((min(a, b) for _, a, b in glyph_clusters), default=0.0)
        max_x = max((max(a, b) for _, a, b in glyph_clusters), default=0.0)
        if min_x < 0:
            glyph_positions = [(x - min_x, y) for x, y in glyph_positions]
            glyph_clusters = [(c, a - min_x, b - min_x) for c, a, b in glyph_clusters]
        width = max(0.0, max_x - min_x)
        logical_starts = sorted({max(0, min(len(text), c)) for c, _, _ in glyph_clusters})
        cluster_ends = {
            start: (logical_starts[index + 1] if index + 1 < len(logical_starts) else len(text))
            for index, start in enumerate(logical_starts)
        }
        cluster_boxes: dict[int, list[float]] = {}
        for cluster, left, right in glyph_clusters:
            cluster = max(0, min(len(text), cluster))
            if cluster not in cluster_boxes:
                cluster_boxes[cluster] = [min(left, right), max(left, right)]
            else:
                cluster_boxes[cluster][0] = min(cluster_boxes[cluster][0], left, right)
                cluster_boxes[cluster][1] = max(cluster_boxes[cluster][1], left, right)
        clusters = []
        for cluster, (left, right) in cluster_boxes.items():
            end = cluster_ends.get(cluster, min(len(text), cluster + 1))
            clusters.append(ShapedCluster(
                source_start + cluster, source_start + end,
                left, max(0.0, right - left), direction == "rtl",
            ))
        clusters.sort(key=lambda item: item.x)
        return ShapedGlyphRun(
            source_start, source_start + len(text), font_family, typeface,
            float(size), direction, tuple(glyph_ids), tuple(glyph_positions),
            tuple(clusters), width,
        )

    def shape(self, text: str, config, resolver, *, base_direction: str = "auto") -> ShapedText:
        """Shape text using per-family files declared in ``FontConfig``."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text:
            return ShapedText((), (), 0.0)
        font_runs = resolver.resolve_runs(config, text)
        base = self._base_direction(text, base_direction)
        pieces = []
        for font_run in font_runs:
            path = config.path_for_family(font_run.family)
            if path is None:
                raise ValueError(
                    f"No font file configured for shaping family {font_run.family!r}. "
                    "Set FontConfig.font_path or FontConfig.font_files."
                )
            for start, end, direction in self._directional_spans(font_run.text, base):
                pieces.append((font_run, start, end, direction, path))
        if base == "rtl":
            pieces.reverse()
        shaped_runs = []
        x_offset = 0.0
        all_clusters = []
        for font_run, local_start, local_end, direction, path in pieces:
            source_start = font_run.start + local_start
            shaped = self._shape_segment(
                font_run.text[local_start:local_end], path=path,
                size=config.size, direction=direction,
                font_family=font_run.family, typeface=font_run.typeface,
                source_start=source_start,
            )
            # Runs are emitted in visual order.  Positions are local to each run;
            # the painter adds x_offset as the run origin.
            shaped_runs.append((x_offset, shaped))
            all_clusters.extend(
                ShapedCluster(c.start, c.end, c.x + x_offset, c.width, c.rtl)
                for c in shaped.clusters
            )
            x_offset += shaped.width
        # Public runs carry positions that include the run's paragraph offset.
        positioned_runs = tuple(
            ShapedGlyphRun(
                run.start, run.end, run.font_family, run.typeface, run.font_size,
                run.direction, run.glyph_ids,
                tuple((x + offset, y) for x, y in run.positions),
                tuple(ShapedCluster(c.start, c.end, c.x + offset, c.width, c.rtl)
                      for c in run.clusters),
                run.width,
            )
            for offset, run in shaped_runs
        )
        all_clusters.sort(key=lambda item: item.x)
        return ShapedText(positioned_runs, tuple(all_clusters), x_offset)
