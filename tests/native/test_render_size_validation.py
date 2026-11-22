from __future__ import annotations

import math

import pytest

from novaui.native.renderer import RenderSize


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"width": 0}, ValueError),
        ({"height": -1}, ValueError),
        ({"width": True}, TypeError),
        ({"height": 10.5}, TypeError),
        ({"scale": True}, TypeError),
        ({"scale": "2"}, TypeError),
        ({"scale": 0}, ValueError),
        ({"scale": -1}, ValueError),
        ({"scale": math.nan}, ValueError),
        ({"scale": math.inf}, ValueError),
        ({"scale_y": False}, TypeError),
        ({"scale_y": math.nan}, ValueError),
        ({"scale_y": math.inf}, ValueError),
        ({"scale_y": 0}, ValueError),
    ],
)
def test_render_size_rejects_invalid_dimensions_and_scales(kwargs, error):
    with pytest.raises(error):
        RenderSize(100, 50, **kwargs)


def test_render_size_preserves_independent_fractional_scale_factors():
    size = RenderSize(100, 50, scale=1.5, scale_y=2.0)

    assert size.pixel_width == 150
    assert size.pixel_height == 100


def test_render_size_never_exposes_a_zero_pixel_backing_dimension():
    size = RenderSize(1, 1, scale=0.1, scale_y=0.1)

    assert size.pixel_width == 1
    assert size.pixel_height == 1
