"""Integrated SDL3 + NativeRuntime example.

Run: python examples/native/runtime_window.py
"""

from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import Button, Label, NativeRuntime, RenderSize, SkiaRenderer, column
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame
from novaui.native.reactivity import State


def main():
    status = State("Ready")
    renderer = SkiaRenderer(RenderSize(960, 640))

    def build_ui():
        return column(
            Label("Yuktara UI", size=30, weight="bold"),
            Label("SDL3 events, retained components and high-DPI resize handling."),
            Label(f"Status: {status.value}", size=18),
            Button("Update status", on_click=lambda _event: setattr(
                status, "value", "Runtime event received"
            )).build(),
            spacing=18,
            padding=32,
            background=0xFFF7F8FA,
        )

    runtime = NativeRuntime(build_ui, renderer, 960, 640)
    runtime.component.bind_state(status)
    window = SDL3Window("Yuktara UI — Native Runtime", 960, 640)
    window.run_runtime(
        runtime,
        lambda _runtime: renderer_frame(renderer, skia_module=skia),
    )


if __name__ == "__main__":
    main()
