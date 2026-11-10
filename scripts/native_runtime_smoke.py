"""Short real-window smoke test for the SDL3 + Skia runtime.

Run under a desktop session or a virtual X11 display after:
    python -m novaui setup
"""

from novaui.native import Button, Label, NativeRuntime, RenderSize, SkiaRenderer, TextField, column
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame


def main() -> None:
    width, height = 640, 420
    renderer = SkiaRenderer(RenderSize(width, height))
    skia = renderer._module()
    root = column(
        Label("Yuktara UI native runtime smoke test"),
        Label("SDL3 window + Skia CPU raster presentation"),
        TextField("", placeholder="IME-capable native text field", width=360),
        Button("Rendered successfully"),
        spacing=14,
        padding=24,
    )
    runtime = NativeRuntime(lambda: root, renderer, width, height)
    window = SDL3Window(
        "Yuktara UI — Native integration smoke",
        width,
        height,
        resizable=False,
    )
    window.run_runtime(
        runtime,
        lambda _app: renderer_frame(renderer, skia_module=skia),
        max_frames=3,
    )
    print("SDL3 + Skia native runtime smoke test passed.")


if __name__ == "__main__":
    main()
