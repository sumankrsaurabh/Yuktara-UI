from __future__ import annotations

import math

import pytest

from novaui.native.layout.geometry import Constraints, Insets, Point, Rect, Size


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "12"])
def test_size_rejects_non_finite_or_non_numeric_dimensions(value):
    with pytest.raises((TypeError, ValueError)):
        Size(width=value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "12"])
def test_point_rejects_non_finite_or_non_numeric_coordinates(value):
    with pytest.raises((TypeError, ValueError)):
        Point(x=value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "12"])
def test_rect_rejects_invalid_coordinates(value):
    with pytest.raises((TypeError, ValueError)):
        Rect(x=value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "12", -1])
def test_rect_rejects_invalid_extents(value):
    with pytest.raises((TypeError, ValueError)):
        Rect(width=value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "12", -1])
def test_insets_reject_invalid_values(value):
    with pytest.raises((TypeError, ValueError)):
        Insets(top=value)


def test_constraints_allow_unbounded_maxima_but_not_infinite_minima():
    constraints = Constraints(max_width=math.inf, max_height=math.inf)

    assert math.isinf(constraints.max_width)
    assert math.isinf(constraints.max_height)
    with pytest.raises(ValueError):
        Constraints(min_width=math.inf)
    with pytest.raises(ValueError):
        Constraints(max_width=math.nan)
    with pytest.raises(ValueError):
        Constraints(max_height=-math.inf)


def test_constraints_reject_boolean_and_non_numeric_values():
    with pytest.raises(TypeError):
        Constraints(min_width=True)
    with pytest.raises(TypeError):
        Constraints(max_width="500")


def test_rect_inset_and_constraints_keep_existing_geometry_semantics():
    rect = Rect(10, 20, 100, 80).inset(Insets.symmetric(5, 8))

    assert rect == Rect(18, 25, 84, 70)
    assert Constraints(max_width=200, max_height=100).constrain(Size(250, 50)) == Size(200, 50)
