"""Direct SDL3 + Skia OpenGL rendering and a simple animated shape.

Run with:
    python examples/native/gpu_window.py

Requires a working desktop OpenGL driver and a GPU-enabled skia-python wheel.
"""
from math import sin
from time import perf_counter

from novaui.native.platform.sdl3 import SDL3Window


def main() -> None:
    with SDL3Window(
        title="Yuktara UI · GPU rendering",
        width=1100,
        height=720,
        graphics_backend="opengl",
        vsync=1,
    ) as window:
        renderer = window.create_gpu_renderer()
        started = perf_counter()
        try:
            running = True
            while running:
                for event in window.poll_events():
                    if event.quit_requested:
                        running = False
                if not running:
                    break

                elapsed = perf_counter() - started
                x = 460 + sin(elapsed * 1.4) * 260
                y = 310 + sin(elapsed * 2.0) * 70

                renderer.clear(0xFF101820)
                renderer.draw_rect(
                    x, y, 180, 110, 0xFF2878D0, radius=22
                )
                renderer.draw_stroke_rect(
                    x - 2, y - 2, 184, 114, 0xFFB8D8FF,
                    stroke_width=2, radius=24,
                )
                window.present_gpu(renderer)
        finally:
            # The Skia surface must be released before SDL destroys its GL
            # context in the window context manager's __exit__.
            renderer.close()


if __name__ == "__main__":
    main()
