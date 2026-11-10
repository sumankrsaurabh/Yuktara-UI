"""Print adaptive layout measurements for phone, tablet and desktop profiles.

This example is backend-free: it does not open SDL or initialize Skia.
Run with: python examples/native/adaptive_preview.py
"""

from novaui.native import (
    AdaptiveLayout,
    AdaptivePreviewHarness,
    AdaptiveVariant,
    LayoutNode,
    ViewportProfile,
)


def main() -> None:
    compact = LayoutNode.column(
        LayoutNode("text", text="Navigation"),
        LayoutNode("text", text="Main content"),
        key="compact-composition",
    )
    expanded = LayoutNode.row(
        LayoutNode("text", text="Navigation"),
        LayoutNode("text", text="Main content"),
        LayoutNode("text", text="Inspector"),
        key="expanded-composition",
    )
    screen = AdaptiveLayout((
        AdaptiveVariant(0, 0, compact),
        AdaptiveVariant(840, 0, expanded),
    )).build()

    profiles = (
        ViewportProfile("phone", 390, 844),
        ViewportProfile("tablet", 900, 1200, scale=2),
        ViewportProfile("desktop", 1440, 900, scale=1.5),
    )
    previews = AdaptivePreviewHarness(screen, profiles).run()

    for preview in previews:
        print(
            f"{preview.profile.name}: "
            f"{preview.profile.width:g}x{preview.profile.height:g} UI units, "
            f"{preview.backing_pixel_size[0]}x{preview.backing_pixel_size[1]} pixels, "
            f"variant={preview.active_variant_index}"
        )
        for node in preview.nodes:
            print(
                f"  path={node.path!s:<8} kind={node.kind:<6} "
                f"key={node.key!s:<24} bounds={node.bounds}"
            )


if __name__ == "__main__":
    main()
