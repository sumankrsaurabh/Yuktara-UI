import pytest

from novaui.native.layout import LayoutEngine, LayoutNode, Rect, Size, diagnose_overflow


def test_diagnose_overflow_reports_each_exceeded_edge():
    children = [
        LayoutNode("box", width=20, height=20, position="absolute",
                   left=-5, top=0, key="left"),
        LayoutNode("box", width=20, height=20, position="absolute",
                   left=0, top=-4, key="top"),
        LayoutNode("box", width=20, height=20, position="absolute",
                   left=30, top=0, key="right"),
        LayoutNode("box", width=20, height=20, position="absolute",
                   left=0, top=30, key="bottom"),
    ]
    parent = LayoutNode("box", children=children, width=40, height=40, key="parent")
    LayoutEngine().layout(parent, Rect(0, 0, 40, 40))

    issues = diagnose_overflow(parent)

    assert [issue.path for issue in issues] == [(0,), (1,), (2,), (3,)]
    assert [issue.child_key for issue in issues] == ["left", "top", "right", "bottom"]
    assert [issue.sides for issue in issues] == [
        ("left",), ("top",), ("right",), ("bottom",),
    ]
    assert [issue.overflow for issue in issues] == [
        (5, 0, 0, 0), (0, 4, 0, 0), (0, 0, 10, 0), (0, 0, 0, 10),
    ]
    assert all(issue.parent_key == "parent" for issue in issues)
    assert all(issue.intentional is False for issue in issues)

def test_diagnostics_walk_nested_layout_and_keep_stable_child_paths():
    grandchild = LayoutNode(
        "box", width=60, height=20, position="absolute",
        left=15, top=0, key="grandchild",
    )
    child = LayoutNode.box(grandchild, width=30, height=30, key="child")
    sibling = LayoutNode("box", width=10, height=10, key="sibling")
    root = LayoutNode.stack(child, sibling, width=100, height=50, key="root")
    LayoutEngine().layout(root, Rect(0, 0, 100, 50))

    issues = diagnose_overflow(root)

    assert [issue.path for issue in issues] == [(0, 0)]
    assert issues[0].parent_key == "child"
    assert issues[0].child_key == "grandchild"


def test_scroll_content_overflow_is_classified_as_intentional():
    content = LayoutNode("box", width=100, height=240, intrinsic_size=Size(100, 240))
    scroll = LayoutNode.scroll(content, width=100, height=80)
    LayoutEngine().layout(scroll, Rect(0, 0, 100, 80))

    assert diagnose_overflow(scroll) == ()
    issues = diagnose_overflow(scroll, include_intentional=True)
    assert len(issues) == 1
    assert issues[0].intentional is True
    assert issues[0].intentional_reason == "scroll-content"


def test_explicit_container_clip_is_classified_as_intentional():
    child = LayoutNode(
        "box", width=20, height=20, position="absolute",
        left=25, top=0,
    )
    parent = LayoutNode.box(child, width=40, height=40, clip_children=True)
    LayoutEngine().layout(parent, Rect(0, 0, 40, 40))

    assert diagnose_overflow(parent) == ()
    issue, = diagnose_overflow(parent, include_intentional=True)
    assert issue.intentional_reason == "clipped-container"


def test_tolerance_filters_subpixel_overflow():
    child = LayoutNode(
        "box", width=40, height=40, position="absolute",
        left=0.25, top=0,
    )
    parent = LayoutNode.box(child, width=40, height=40)
    LayoutEngine().layout(parent, Rect(0, 0, 40, 40))

    assert diagnose_overflow(parent, tolerance=0.5) == ()
    assert diagnose_overflow(parent, tolerance=0.1)[0].overflow[2] == pytest.approx(0.25)


@pytest.mark.parametrize("tolerance", [-1, float("inf"), float("nan"), True, "1"])
def test_diagnostics_reject_invalid_tolerance(tolerance):
    with pytest.raises(ValueError):
        diagnose_overflow(LayoutNode(), tolerance=tolerance)


def test_diagnostics_validate_root_and_flags():
    with pytest.raises(TypeError):
        diagnose_overflow(object())
    with pytest.raises(TypeError):
        diagnose_overflow(LayoutNode(), include_intentional=1)
