import pytest

from novaui.native import RenderSize, SkiaGpuRenderer


class FakeCanvas:
    def __init__(self):
        self.scales = []

    def scale(self, x, y):
        self.scales.append((x, y))


class FakeSurface:
    def __init__(self):
        self.canvas = FakeCanvas()
        self.flush_count = 0

    def getCanvas(self):
        return self.canvas

    def flushAndSubmit(self):
        self.flush_count += 1

    def makeImageSnapshot(self):
        return "gpu-image"


class FakeContext:
    pass


class FakeSkia:
    class GrDirectContexts:
        calls = 0

        @classmethod
        def MakeGL(cls):
            cls.calls += 1
            return FakeContext()

    class ImageInfo:
        @staticmethod
        def MakeN32Premul(width, height):
            return (width, height)

    class Surfaces:
        calls = []
        framebuffer_calls = []

        @classmethod
        def MakeRenderTarget(cls, context, budgeted, image_info, samples, origin):
            surface = FakeSurface()
            cls.calls.append((context, budgeted, image_info, samples, origin, surface))
            return surface

        @classmethod
        def MakeFromBackendRenderTarget(cls, context, target, origin, color_type, color_space):
            surface = FakeSurface()
            cls.framebuffer_calls.append((context, target, origin, color_type, color_space, surface))
            return surface

    class GrGLFramebufferInfo:
        def __init__(self, fbo_id, format):
            self.fbo_id = fbo_id
            self.format = format

    class GrBackendRenderTarget:
        def __init__(self, width, height, samples, stencil_bits, info):
            self.width = width
            self.height = height
            self.samples = samples
            self.stencil_bits = stencil_bits
            self.info = info

    class ColorType:
        kRGBA_8888_ColorType = "rgba8888"

    class Budgeted:
        class kNo:
            pass

    class GrSurfaceOrigin:
        kTopLeft_GrSurfaceOrigin = "top-left"
        kBottomLeft_GrSurfaceOrigin = "bottom-left"


def test_gpu_renderer_creates_skia_opengl_render_target_and_scales_canvas():
    FakeSkia.GrDirectContexts.calls = 0
    FakeSkia.Surfaces.calls = []
    renderer = SkiaGpuRenderer(
        RenderSize(100, 50, scale=2.0, scale_y=1.5),
        skia_module=FakeSkia,
    )
    assert renderer.backend == "opengl"
    assert renderer.canvas.scales == [(2.0, 1.5)]
    assert FakeSkia.GrDirectContexts.calls == 1
    assert FakeSkia.Surfaces.calls[0][2] == (200, 75)
    assert renderer.snapshot() == "gpu-image"
    assert FakeSkia.Surfaces.calls[0][-1].flush_count == 1


def test_gpu_renderer_reuses_context_on_resize():
    FakeSkia.GrDirectContexts.calls = 0
    FakeSkia.Surfaces.calls = []
    renderer = SkiaGpuRenderer(RenderSize(20, 10), skia_module=FakeSkia)
    renderer.resize(RenderSize(40, 30, scale=2))
    assert FakeSkia.GrDirectContexts.calls == 1
    assert len(FakeSkia.Surfaces.calls) == 2
    assert FakeSkia.Surfaces.calls[-1][2] == (80, 60)


def test_gpu_renderer_requires_opengl_backend_and_current_context():
    class NoGpuSkia:
        pass

    with pytest.raises(RuntimeError, match="OpenGL GPU backend"):
        SkiaGpuRenderer(RenderSize(10, 10), skia_module=NoGpuSkia)

    class NoContextSkia(FakeSkia):
        class GrDirectContexts:
            @staticmethod
            def MakeGL():
                return None

    with pytest.raises(RuntimeError, match="could not create a GPU context"):
        SkiaGpuRenderer(RenderSize(10, 10), skia_module=NoContextSkia)


def test_gpu_renderer_close_releases_surface_references_and_disables_resize():
    renderer = SkiaGpuRenderer(RenderSize(10, 10), skia_module=FakeSkia)
    renderer.close()
    assert renderer.canvas is None
    with pytest.raises(RuntimeError, match="closed"):
        renderer.resize(RenderSize(20, 20))

def test_gpu_renderer_can_wrap_default_framebuffer_for_direct_window_rendering():
    FakeSkia.GrDirectContexts.calls = 0
    FakeSkia.Surfaces.framebuffer_calls = []
    renderer = SkiaGpuRenderer(
        RenderSize(640, 480, scale=2.0),
        skia_module=FakeSkia,
        framebuffer=True,
    )
    assert renderer.backend == "opengl"
    assert renderer.framebuffer is True
    context, target, origin, color_type, color_space, surface = FakeSkia.Surfaces.framebuffer_calls[0]
    assert target.width == 1280
    assert target.height == 960
    assert target.info.fbo_id == 0
    assert target.info.format == 0x8058
    assert origin == "bottom-left"
    assert color_type == "rgba8888"
    assert color_space is None
    renderer.flush()
    assert surface.flush_count == 1
