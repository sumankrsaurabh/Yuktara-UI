"""First native window smoke test: Skia raster -> SDL3 streaming texture.

Python package and SDL3 runtime dependencies are prepared automatically on
first use. Run: python examples/native/sdl3_skia_window.py
"""

from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native.renderer import RenderSize, SkiaRenderer
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame


def main():
    renderer = SkiaRenderer(RenderSize(1100, 720))
    window = SDL3Window("Yuktara UI — SDL3 + Skia", 1100, 720)

    def draw():
        renderer.clear(0xFFF7F8FA)
        renderer.draw_rect(48, 48, 1004, 624, 0xFFFFFFFF, radius=24)
        renderer.draw_rect(80, 80, 52, 52, 0xFF6750A4, radius=16)
        renderer.draw_text(
            "Yuktara UI",
            148,
            119,
            color=0xFF202735,
            font=None,
        )
        renderer.draw_text(
            "SDL3 window host  •  Skia raster renderer  •  Inter typography",
            80,
            180,
            color=0xFF586174,
        )
        return renderer_frame(renderer, skia_module=skia)

    window.run(draw)


if __name__ == "__main__":
    main()
