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


def test_render_size_uses_uniform_content_scale_for_unequal_pixel_ratios():
    size = RenderSize(800, 600, 2.0, 1.5)

    assert size.pixel_width == 1600
    assert size.pixel_height == 900
    assert size.content_scale == 1.5
    assert size.content_offset_x == pytest.approx(200)
    assert size.content_offset_y == pytest.approx(0)


def test_render_size_centers_letterbox_for_taller_backing_surface():
    size = RenderSize(800, 600, 1.5, 2.0)

    assert size.content_scale == 1.5
    assert size.content_offset_x == pytest.approx(0)
    assert size.content_offset_y == pytest.approx(150)


def test_render_size_keeps_uniform_scale_without_letterboxing():
    size = RenderSize(800, 600, 2.0, 2.0)

    assert size.content_scale == 2.0
    assert size.content_offset_x == pytest.approx(0)
    assert size.content_offset_y == pytest.approx(0)
