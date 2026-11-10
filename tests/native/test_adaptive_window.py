import pytest

from novaui.native.adaptive import (
    WindowHeightSizeClass,
    WindowSizeBreakpoints,
    WindowWidthSizeClass,
    compute_window_adaptive_info,
)


@pytest.mark.parametrize(
    "width,expected",
    [
        (599.99, WindowWidthSizeClass.COMPACT),
        (600, WindowWidthSizeClass.MEDIUM),
        (839.99, WindowWidthSizeClass.MEDIUM),
        (840, WindowWidthSizeClass.EXPANDED),
        (1199.99, WindowWidthSizeClass.EXPANDED),
        (1200, WindowWidthSizeClass.LARGE),
        (1599.99, WindowWidthSizeClass.LARGE),
        (1600, WindowWidthSizeClass.EXTRA_LARGE),
    ],
)
def test_width_class_breakpoints_use_logical_window_width(width, expected):
    info = compute_window_adaptive_info(width, 800)
    assert info.width_size_class is expected


@pytest.mark.parametrize(
    "height,expected",
    [
        (479.99, WindowHeightSizeClass.COMPACT),
        (480, WindowHeightSizeClass.MEDIUM),
        (899.99, WindowHeightSizeClass.MEDIUM),
        (900, WindowHeightSizeClass.EXPANDED),
    ],
)
def test_height_class_breakpoints(height, expected):
    assert compute_window_adaptive_info(1000, height).height_size_class is expected


def test_adaptive_classes_use_window_units_not_backing_resolution():
    info = compute_window_adaptive_info(
        900, 700, pixel_width=1800, pixel_height=1400,
    )
    assert info.width_size_class is WindowWidthSizeClass.EXPANDED
    assert info.height_size_class is WindowHeightSizeClass.MEDIUM
    assert info.scale_x == pytest.approx(2.0)
    assert info.scale_y == pytest.approx(2.0)
    assert info.pixel_width == 1800
    assert info.pixel_height == 1400


def test_adaptive_info_exposes_orientation_and_aspect_ratio():
    landscape = compute_window_adaptive_info(1200, 800)
    portrait = compute_window_adaptive_info(800, 1200)
    square = compute_window_adaptive_info(800, 800)
    assert landscape.orientation == "landscape"
    assert landscape.aspect_ratio == pytest.approx(1.5)
    assert landscape.is_landscape
    assert portrait.orientation == "portrait"
    assert not portrait.is_landscape
    assert square.orientation == "square"


def test_custom_window_size_breakpoints_are_supported():
    points = WindowSizeBreakpoints(
        width_medium=500, width_expanded=700, width_large=1000,
        width_extra_large=1400, height_medium=400, height_expanded=800,
    )
    info = compute_window_adaptive_info(750, 850, breakpoints=points)
    assert info.width_size_class is WindowWidthSizeClass.EXPANDED
    assert info.height_size_class is WindowHeightSizeClass.EXPANDED


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"width": 0}, ValueError),
        ({"height": float("inf")}, ValueError),
        ({"width": True}, TypeError),
        ({"pixel_width": 0}, ValueError),
        ({"pixel_height": 10.5}, ValueError),
        ({"scale_x": 0}, ValueError),
    ],
)
def test_adaptive_info_rejects_invalid_dimensions(kwargs, error):
    with pytest.raises(error):
        compute_window_adaptive_info(
            kwargs.pop("width", 800),
            kwargs.pop("height", 600),
            **kwargs,
        )


def test_window_breakpoints_must_be_strictly_increasing():
    with pytest.raises(ValueError):
        WindowSizeBreakpoints(width_medium=800, width_expanded=800)
    with pytest.raises(ValueError):
        WindowSizeBreakpoints(height_medium=900, height_expanded=800)


def test_native_runtime_updates_adaptive_info_after_resize():
    from types import SimpleNamespace
    from novaui.native.runtime import NativeRuntime

    renderer = SimpleNamespace(size=SimpleNamespace(scale=2.0, scale_y=1.5))
    runtime = NativeRuntime(lambda: None, renderer, 500, 700)
    assert runtime.adaptive_info.width_size_class is WindowWidthSizeClass.COMPACT
    assert runtime.adaptive_info.height_size_class is WindowHeightSizeClass.MEDIUM

    runtime.resize(1300, 900, pixel_width=2600, pixel_height=1350)

    assert runtime.adaptive_info.width_size_class is WindowWidthSizeClass.LARGE
    assert runtime.adaptive_info.height_size_class is WindowHeightSizeClass.EXPANDED
    assert runtime.adaptive_info.scale_x == pytest.approx(2.0)
    assert runtime.adaptive_info.scale_y == pytest.approx(1.5)


def test_native_runtime_ignores_identical_resize_metrics():
    from types import SimpleNamespace
    from novaui.native.runtime import NativeRuntime

    renderer = SimpleNamespace(size=SimpleNamespace(scale=2.0, scale_y=1.5))
    runtime = NativeRuntime(lambda: None, renderer, 500, 700)
    previous_info = runtime.adaptive_info
    runtime.resize(500, 700, pixel_width=1000, pixel_height=1050)
    assert runtime.adaptive_info is previous_info
