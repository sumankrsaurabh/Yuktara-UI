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


def test_render_size_supports_independent_high_dpi_scale_axes():
    size = RenderSize(800, 600, 2.0, 1.5)
    assert size.pixel_width == 1600
    assert size.pixel_height == 900


def test_render_size_rejects_non_positive_vertical_scale():
    import pytest
    with pytest.raises(ValueError):
        RenderSize(800, 600, 1.0, 0.0)
