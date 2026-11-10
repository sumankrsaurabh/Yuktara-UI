"""Font configuration, typeface fallback and Unicode glyph-run resolution."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from math import isfinite
from typing import Any

DEFAULT_FONT_FAMILY = "Inter"
FALLBACK_FONT_FAMILIES = (
    "Noto Sans", "Noto Sans Devanagari", "Noto Sans Bengali",
    "Noto Sans Tamil", "Noto Sans Telugu", "Noto Sans Kannada",
    "Noto Sans Malayalam", "Noto Sans Gujarati", "Noto Sans Gurmukhi",
    "Noto Sans Arabic", "Noto Sans CJK SC", "Noto Color Emoji",
    "Arial", "DejaVu Sans", "sans-serif",
)


@dataclass(frozen=True, slots=True)
class FontConfig:
    """Font configuration shared by native text components."""

    family: str = DEFAULT_FONT_FAMILY
    fallback_families: tuple[str, ...] = FALLBACK_FONT_FAMILIES
    size: float = 14.0
    weight: str = "normal"
    italic: bool = False
    font_path: str | None = None
    font_files: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.family or not isinstance(self.family, str):
            raise TypeError("Font family must be a non-empty string.")
        if not isfinite(float(self.size)) or self.size <= 0:
            raise ValueError("Font size must be a finite number greater than zero.")
        if self.weight not in {"normal", "medium", "semibold", "bold"}:
            raise ValueError("Unsupported font weight.")
        if any(not isinstance(family, str) or not family for family in self.fallback_families):
            raise ValueError("Fallback font families must be non-empty strings.")
        if self.font_path is not None and (not isinstance(self.font_path, str) or not self.font_path):
            raise ValueError("font_path must be a non-empty path string or None.")
        normalized_files = []
        seen = set()
        for item in self.font_files:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ValueError("font_files entries must be (family, path) pairs.")
            family, path = item
            if not isinstance(family, str) or not family or not isinstance(path, str) or not path:
                raise ValueError("font_files families and paths must be non-empty strings.")
            if family in seen:
                raise ValueError(f"A font file was configured more than once for {family!r}.")
            seen.add(family)
            normalized_files.append((family, path))
        object.__setattr__(self, "font_files", tuple(normalized_files))

    def path_for_family(self, family: str) -> str | None:
        """Return the explicitly configured font file for a resolved family."""
        if family == self.family and self.font_path:
            return self.font_path
        return dict(self.font_files).get(family)


@dataclass(frozen=True, slots=True)
class FontRun:
    """A contiguous text range rendered with one resolved typeface."""

    text: str
    start: int
    end: int
    family: str
    typeface: Any


class FontResolver:
    """Resolve font families and choose fallbacks for unsupported glyphs.

    The resolver segments text at grapheme boundaries and probes Skia's
    ``Typeface.unicharToGlyph`` when that API is available. If the installed
    Skia binding cannot expose glyph coverage, it safely falls back to the
    configured primary face instead of guessing. This is font fallback, not a
    full shaping engine: bidirectional reordering and script shaping need a
    HarfBuzz/SkParagraph backend.
    """

    def __init__(self, skia_module=None) -> None:
        self._skia = skia_module
        self._cache: dict[tuple[str, str | None, str, bool], Any] = {}
        self._font_manager = None

    def _module(self):
        if self._skia is None:
            try:
                from .dependencies import ensure_skia_python
                ensure_skia_python()
                import skia
            except Exception as exc:
                raise RuntimeError(
                    "Yuktara UI could not prepare Skia Python (skia-python 144.1). "
                    "Check the network connection or disable automatic setup with "
                    "YUKTARA_UI_NO_AUTO_INSTALL=1."
                ) from exc
            self._skia = skia
        return self._skia

    @staticmethod
    def _style(skia, config: FontConfig):
        weights = {
            "normal": skia.FontStyle.kNormal_Weight,
            "medium": skia.FontStyle.kMedium_Weight,
            "semibold": skia.FontStyle.kSemiBold_Weight,
            "bold": skia.FontStyle.kBold_Weight,
        }
        return skia.FontStyle(
            weights[config.weight],
            skia.FontStyle.kNormal_Width,
            skia.FontStyle.kItalic_Slant if config.italic else skia.FontStyle.kUpright_Slant,
        )

    def _load_typeface_file(self, path: str, family: str, skia):
        """Load the exact file used by HarfBuzz so glyph IDs stay compatible."""
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(
                f"Configured font file for {family!r} does not exist: {resolved}"
            )

        # Prefer SkFontMgr::makeFromFile, the current Skia API.  The static
        # Typeface.MakeFromFile spelling remains a compatibility fallback for
        # older skia-python builds that expose only the legacy wrapper.
        if self._font_manager is None:
            manager_type = getattr(skia, "FontMgr", None)
            ref_default = getattr(manager_type, "RefDefault", None)
            if callable(ref_default):
                self._font_manager = ref_default()
        manager_loader = getattr(self._font_manager, "makeFromFile", None)
        if callable(manager_loader):
            face = manager_loader(str(resolved), 0)
        else:
            typeface_loader = getattr(skia.Typeface, "MakeFromFile", None)
            if not callable(typeface_loader):
                raise RuntimeError(
                    "This Skia Python build cannot load explicit font files. "
                    "Expected FontMgr.RefDefault().makeFromFile() or "
                    "Typeface.MakeFromFile()."
                )
            face = typeface_loader(str(resolved), 0)
        if face is None:
            raise ValueError(
                f"Skia could not load configured font file for {family!r}: {resolved}. "
                "Check that the file is a supported font and that its face index is valid."
            )
        return face, str(resolved)

    def _typeface(self, family: str, config: FontConfig):
        configured_path = config.path_for_family(family)
        path_key = str(Path(configured_path).expanduser().resolve()) if configured_path else None
        key = (family, path_key, config.weight, config.italic)
        if key in self._cache:
            return self._cache[key]
        skia = self._module()
        if configured_path:
            face, _ = self._load_typeface_file(configured_path, family, skia)
        else:
            face = skia.Typeface.MakeFromName(family, self._style(skia, config))
        self._cache[key] = face
        return face

    def resolve(self, config: FontConfig):
        """Resolve the preferred face, falling back when that family is absent."""
        for family in (config.family, *config.fallback_families):
            face = self._typeface(family, config)
            if face is not None:
                return face
        skia = self._module()
        return skia.Typeface.MakeDefault()

    @staticmethod
    def _supports_cluster(typeface, cluster: str) -> bool | None:
        probe = getattr(typeface, "unicharToGlyph", None)
        if not callable(probe):
            return None
        for character in cluster:
            codepoint = ord(character)
            # Join controls and variation selectors modify neighbouring glyphs;
            # they do not need standalone cmap entries.
            if codepoint in (0x200C, 0x200D) or 0xFE00 <= codepoint <= 0xFE0F:
                continue
            if 0xE0100 <= codepoint <= 0xE01EF:
                continue
            try:
                glyph = int(probe(codepoint))
            except Exception:
                return None
            if glyph in (0, 0xFFFF):
                return False
        return True

    def resolve_runs(self, config: FontConfig, text: str) -> tuple[FontRun, ...]:
        """Split text into contiguous runs with a typeface that covers each cluster."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text:
            return ()
        # Local import avoids a module cycle: text measurement itself uses this resolver.
        from .text.measure import grapheme_spans

        families = (config.family, *config.fallback_families)
        faces = [(family, self._typeface(family, config)) for family in families]
        faces = [(family, face) for family, face in faces if face is not None]
        if not faces:
            return (FontRun(text, 0, len(text), "default", self._module().Typeface.MakeDefault()),)
        selected = []
        for start, end in grapheme_spans(text):
            cluster = text[start:end]
            choice = faces[0]
            probe_available = False
            for candidate in faces:
                support = self._supports_cluster(candidate[1], cluster)
                if support is not None:
                    probe_available = True
                    if support:
                        choice = candidate
                        break
                elif candidate is faces[0]:
                    # Unsupported Skia introspection: retain deterministic primary face.
                    break
            if not probe_available:
                choice = faces[0]
            selected.append((start, end, choice[0], choice[1]))

        runs = []
        run_start, run_end, family, face = selected[0]
        for start, end, next_family, next_face in selected[1:]:
            if next_family == family and next_face is face and start == run_end:
                run_end = end
                continue
            runs.append(FontRun(text[run_start:run_end], run_start, run_end, family, face))
            run_start, run_end, family, face = start, end, next_family, next_face
        runs.append(FontRun(text[run_start:run_end], run_start, run_end, family, face))
        return tuple(runs)

    def measure_text(self, config: FontConfig, text: str) -> float:
        """Measure a text string as the sum of its fallback-font runs."""
        skia = self._module()
        return sum(float(skia.Font(run.typeface, config.size).measureText(run.text))
                   for run in self.resolve_runs(config, text))
