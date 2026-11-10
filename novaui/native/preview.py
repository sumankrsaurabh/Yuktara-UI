"""Deterministic, backend-free viewport previews for native layout trees.

The preview harness runs the real layout engine against a sequence of logical
viewport profiles and records the selected adaptive variants and node bounds.
It does not create a window, renderer, or framebuffer.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .layout import LayoutEngine, LayoutNode, Rect


@dataclass(frozen=True)
class ViewportProfile:
    """A logical viewport and display scale used by a preview pass."""

    name: str
    width: float
    height: float
    scale: float = 1.0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("viewport profile name must not be empty")
        for value, label in ((self.width, "width"), (self.height, "height"),
                             (self.scale, "scale")):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not isfinite(float(value)) or value <= 0):
                raise ValueError(f"viewport profile {label} must be a finite positive number")


@dataclass(frozen=True)
class NodeLayoutSnapshot:
    """Measured and arranged bounds for one node in the active layout tree."""

    path: tuple[int, ...]
    kind: str
    key: str | None
    bounds: tuple[float, float, float, float]
    accessibility_label: str | None
    active_variant_index: int | None = None
    grid_columns: int | None = None


@dataclass(frozen=True)
class ViewportPreview:
    """Result of laying out a tree at one viewport profile."""

    profile: ViewportProfile
    backing_pixel_size: tuple[int, int]
    active_variant_index: int | None
    nodes: tuple[NodeLayoutSnapshot, ...]


class AdaptivePreviewHarness:
    """Run the production layout engine against named viewport profiles.

    The same retained root is laid out repeatedly, just as it is during native
    window resizing. The harness records the active tree after each pass.
    """

    def __init__(
        self,
        root: LayoutNode,
        profiles: Sequence[ViewportProfile],
        engine: LayoutEngine | None = None,
    ):
        if not isinstance(root, LayoutNode):
            raise TypeError("root must be a LayoutNode")
        if not profiles:
            raise ValueError("at least one viewport profile is required")
        if any(not isinstance(profile, ViewportProfile) for profile in profiles):
            raise TypeError("profiles must contain ViewportProfile instances")
        names = [profile.name for profile in profiles]
        if len(names) != len(set(names)):
            raise ValueError("viewport profile names must be unique")
        self.root = root
        self.profiles = tuple(profiles)
        self.engine = engine or LayoutEngine()

    @staticmethod
    def _snapshot_tree(root: LayoutNode) -> tuple[NodeLayoutSnapshot, ...]:
        snapshots = []

        def visit(node: LayoutNode, path: tuple[int, ...]):
            bounds = node.bounds
            active_index = (
                node.responsive_active_index
                if node.kind in {"responsive", "adaptive"} else None
            )
            snapshots.append(NodeLayoutSnapshot(
                path=path,
                kind=node.kind,
                key=node.key,
                bounds=(bounds.x, bounds.y, bounds.width, bounds.height),
                accessibility_label=node.accessibility_label,
                active_variant_index=active_index,
                grid_columns=node.grid_actual_columns if node.kind == "grid" else None,
            ))
            for index, child in enumerate(node.children):
                visit(child, path + (index,))

        visit(root, ())
        return tuple(snapshots)

    def run(self) -> tuple[ViewportPreview, ...]:
        """Return one immutable layout snapshot per configured viewport."""
        previews = []
        for profile in self.profiles:
            self.engine.layout(
                self.root,
                Rect(0.0, 0.0, float(profile.width), float(profile.height)),
            )
            previews.append(ViewportPreview(
                profile=profile,
                backing_pixel_size=(
                    round(profile.width * profile.scale),
                    round(profile.height * profile.scale),
                ),
                active_variant_index=(
                    self.root.responsive_active_index
                    if self.root.kind in {"responsive", "adaptive"} else None
                ),
                nodes=self._snapshot_tree(self.root),
            ))
        return tuple(previews)


__all__ = [
    "AdaptivePreviewHarness",
    "NodeLayoutSnapshot",
    "ViewportPreview",
    "ViewportProfile",
]
