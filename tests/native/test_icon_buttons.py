from novaui.native.widgets.core import IconButton
from novaui.native.theme import NativeTheme


def test_icon_button_uses_vector_paint_instead_of_font_glyph():
    node = IconButton("menu", "Open navigation").build()
    assert node.text is None
    assert callable(node.paint_callback)
    assert node.accessibility_label == "Open navigation"
    assert node.accessibility_role == "button"


def test_icon_button_preserves_disabled_accessibility_state():
    node = IconButton("search", "Search", disabled=True).build()
    assert node.text is None
    assert node.accessibility_disabled is True
    assert node.on_click is None


def test_icon_button_uses_theme_metrics_for_square_touch_target():
    theme = NativeTheme()
    node = IconButton("add", "Create", theme=theme).build()
    assert node.width == theme.control_height_medium
    assert node.min_width == theme.control_height_medium
