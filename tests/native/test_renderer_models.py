import pytest

from novaui.native.renderer import RenderSize


def test_render_size_calculates_scaled_pixels():
    size = RenderSize(800, 600, 1.5)
    assert size.pixel_width == 1200
    assert size.pixel_height == 900


@pytest.mark.parametrize("width,height", [(0, 10), (10, 0), (-1, 10)])
def test_render_size_rejects_invalid_dimensions(width, height):
    with pytest.raises(ValueError):
        RenderSize(width, height)
