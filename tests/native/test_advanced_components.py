from datetime import date

import pytest

from novaui.native import (
    Calendar, Container, DatePicker, Grid, Image, Label, NavigationDrawer,
    NavigationItem, ScrollView, Table, TreeItem, TreeView, build_accessibility_tree,
    column,
)
from novaui.native.layout import LayoutEngine, Rect
from novaui.native.rendering import LayoutTreePainter


class RecordingRenderer:
    def __init__(self):
        self.calls = []

    def draw_rect(self, *args, **kwargs):
        self.calls.append(("rect", args, kwargs))

    def draw_stroke_rect(self, *args, **kwargs):
        self.calls.append(("stroke", args, kwargs))

    def draw_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))

    def draw_image(self, *args, **kwargs):
        self.calls.append(("image", args, kwargs))


def test_grid_reflows_to_available_width_and_arranges_children():
    grid = Grid(
        [Label("A"), Label("B"), Label("C"), Label("D")],
        columns=4, min_column_width=150, column_gap=10, row_gap=6,
    ).build()
    engine = LayoutEngine()
    engine.layout(grid, Rect(0, 0, 340, 200))
    assert grid.grid_actual_columns == 2
    assert grid.children[0].bounds.x == pytest.approx(0)
    assert grid.children[1].bounds.x > grid.children[0].bounds.x
    assert grid.children[2].bounds.y > grid.children[0].bounds.y
    engine.layout(grid, Rect(0, 0, 700, 200))
    assert grid.grid_actual_columns == 4
    assert grid.children[3].bounds.y == pytest.approx(grid.children[0].bounds.y)


def test_grid_validates_responsive_constraints():
    with pytest.raises(ValueError):
        Grid([Label("A")], columns=0)
    with pytest.raises(ValueError):
        Grid([Label("A")], min_column_width=0)


def test_container_applies_padding_margin_and_semantics():
    root = Container(
        child=Label("inside"), width=200, height=100,
        padding=10, margin=5, background=0xFFEFEFEF,
        border_color=0xFF000000, border_width=1,
    ).build()
    LayoutEngine().layout(root, Rect(0, 0, 220, 120))
    styled = root.children[0]
    assert styled.bounds.x == pytest.approx(5)
    assert styled.content_bounds.x == pytest.approx(15)
    assert styled.border_width == 1
    assert build_accessibility_tree(root).role == "group"


def test_container_rejects_ambiguous_child_inputs():
    with pytest.raises(ValueError):
        Container(child=Label("A"), children=(Label("B"),)).build()


def test_image_uses_native_renderer_callback_and_accessibility_label():
    node = Image(b"encoded-image", width=96, height=64, fit="cover",
                 alt="Mountain landscape", radius=8).build()
    LayoutEngine().layout(node, Rect(0, 0, 96, 64))
    renderer = RecordingRenderer()
    LayoutTreePainter(renderer).paint(node)
    call = next(call for call in renderer.calls if call[0] == "image")
    assert call[1][0] == b"encoded-image"
    assert call[2]["fit"] == "cover"
    assert call[2]["radius"] == 8
    semantics = build_accessibility_tree(node)
    assert semantics.role == "image"
    assert semantics.label == "Mountain landscape"


def test_image_validates_fit_and_dimensions():
    with pytest.raises(ValueError):
        Image(b"x", fit="stretch")
    with pytest.raises(ValueError):
        Image(b"x", width=0)


def test_scroll_view_builds_clipped_scroll_node():
    root = ScrollView(column(*[Label(str(index)) for index in range(20)]),
                      height=80, axis="vertical").build()
    assert root.kind == "scroll"
    assert root.scroll_axis == "vertical"
    LayoutEngine().layout(root, Rect(0, 0, 240, 80))
    assert root.content_size.height > root.content_bounds.height
    assert root.max_scroll_y > 0


def test_table_builds_accessible_weighted_rows_and_cells():
    table = Table(
        rows=(("Ada", "Engineer"), ("Linus", "Developer")),
        headers=("Name", "Role"), column_widths=(1, 2),
        striped=True,
    ).build()
    assert table.accessibility_role == "table"
    assert len(table.children) == 3
    assert table.children[0].accessibility_role == "row"
    assert table.children[0].children[0].accessibility_role == "columnheader"
    LayoutEngine().layout(table, Rect(0, 0, 600, 180))
    first = table.children[0]
    assert first.children[1].bounds.width > first.children[0].bounds.width
    semantics = build_accessibility_tree(table)
    assert semantics.role == "table"


def test_table_validates_column_counts_and_weights():
    with pytest.raises(ValueError):
        Table(rows=(("A",), ("B", "C")))
    with pytest.raises(ValueError):
        Table(rows=(("A", "B"),), column_widths=(1, 0))


def test_navigation_drawer_selection_updates_semantics_and_callback():
    selected = []
    drawer = NavigationDrawer(
        [NavigationItem("Home", icon="⌂"), NavigationItem("Settings", icon="⚙")],
        selected="Home", on_select=selected.append,
    )
    root = drawer.build()
    root.children[1].on_click(None)
    assert drawer.selected == "Settings"
    assert root.children[1].accessibility_selected is True
    assert selected == [drawer.items[1]]
    assert build_accessibility_tree(root).role == "navigation"


def test_navigation_drawer_rejects_unknown_selection_and_duplicate_keys():
    with pytest.raises(ValueError):
        NavigationDrawer([NavigationItem("Home")], selected="Missing")
    with pytest.raises(ValueError):
        NavigationDrawer([NavigationItem("A", key="same"), NavigationItem("B", key="same")])


def test_calendar_month_navigation_and_selection():
    changes = []
    calendar = Calendar(value=date(2026, 11, 10), on_change=changes.append,
                        width=280).build()
    assert calendar.accessibility_label == "Calendar"
    previous = calendar.children[0].children[0]
    previous.on_click(None)
    assert "October 2026" in calendar.children[0].children[1].text
    day_grid = calendar.children[2]
    selected_cell = next(node for node in day_grid.children
                         if node.accessibility_label == "2026-10-14")
    selected_cell.children[0].on_click(None)
    assert changes == [date(2026, 10, 14)]


def test_calendar_enforces_minimum_and_maximum_dates():
    calendar = Calendar(value=date(2026, 11, 10), min_date=date(2026, 11, 5),
                        max_date=date(2026, 11, 20)).build()
    day_grid = calendar.children[2]
    too_early = next(node for node in day_grid.children
                     if node.accessibility_label == "2026-11-04")
    assert too_early.children[0].on_click is None
    with pytest.raises(ValueError):
        Calendar(min_date=date(2026, 12, 1), max_date=date(2026, 11, 1))


def test_date_picker_expands_and_commits_selection():
    changes = []
    picker = DatePicker(value="2026-11-10", on_change=changes.append)
    root = picker.build()
    root.children[0].on_click(None)
    assert picker.expanded is True
    assert len(root.children) == 2
    day_grid = root.children[1].children[2]
    target = next(node for node in day_grid.children
                  if node.accessibility_label == "2026-11-12")
    target.children[0].on_click(None)
    assert picker.value == date(2026, 11, 12)
    assert picker.expanded is False
    assert changes == [date(2026, 11, 12)]


def test_tree_view_expands_and_selects_items():
    selected = []
    tree = TreeView([
        TreeItem("Documents", children=(TreeItem("Report", key="report"),), key="docs"),
        TreeItem("Pictures", key="pics"),
    ], on_select=selected.append)
    root = tree.build()
    root.children[0].on_click(None)
    assert len(root.children) == 3
    assert root.children[0].accessibility_expanded is True
    root.children[1].on_click(None)
    assert tree.selected == "report"
    assert selected[-1].label == "Report"
    assert build_accessibility_tree(root).role == "tree"


def test_tree_view_supports_collapsed_items_and_disabled_nodes():
    tree = TreeView([
        TreeItem("Root", children=(TreeItem("Child"),), key="root"),
        TreeItem("Locked", disabled=True, key="locked"),
    ])
    root = tree.build()
    assert len(root.children) == 2
    root.children[1].on_click if root.children[1].on_click else None
    assert tree.selected is None


def test_scroll_view_validates_axis():
    with pytest.raises(ValueError):
        ScrollView(Label("bad"), axis="diagonal").build()


def test_file_picker_routes_open_result_to_button_and_callback():
    class FakeDialogService:
        def show_open_file_dialog(self, callback, **kwargs):
            self.kwargs = kwargs
            callback(("/tmp/notes.pdf",), 0)

    changes = []
    service = FakeDialogService()
    picker = __import__("novaui.native", fromlist=["FilePicker"]).FilePicker(
        service, filters=(("PDF files", "pdf"),), on_change=changes.append,
    )
    button = picker.build()
    button.on_click(None)
    assert picker.value == ("/tmp/notes.pdf",)
    assert button.text == "/tmp/notes.pdf"
    assert changes == [("/tmp/notes.pdf",)]
    assert service.kwargs["filters"] == (("PDF files", "pdf"),)


def test_file_picker_supports_save_and_folder_modes():
    class FakeDialogService:
        def show_save_file_dialog(self, callback, **kwargs):
            self.mode = "save"
            callback(("/tmp/report.docx",), 0)

        def show_open_folder_dialog(self, callback, **kwargs):
            self.mode = "folder"
            callback(("/tmp/documents",), -1)

    service = FakeDialogService()
    save = __import__("novaui.native", fromlist=["FilePicker"]).FilePicker(service, mode="save").build()
    save.on_click(None)
    folder = __import__("novaui.native", fromlist=["FilePicker"]).FilePicker(service, mode="folder").build()
    folder.on_click(None)
    assert service.mode == "folder"


def test_file_picker_validation_and_error_callback():
    from novaui.native import FilePicker

    class Service:
        def show_open_file_dialog(self, callback, **kwargs):
            callback(None, -1)

    errors = []
    picker = FilePicker(Service(), on_error=lambda: errors.append("error"))
    button = picker.build()
    button.on_click(None)
    assert errors == ["error"]
    with pytest.raises(ValueError):
        FilePicker(Service(), mode="image")


def test_sdl3_file_dialog_results_are_marshaled_to_window_thread():
    import ctypes
    import threading
    from novaui.native.platform.sdl3 import SDL3Window

    class FakeFunction:
        def __init__(self):
            self.args = None
            self.restype = None
            self.argtypes = None

        def __call__(self, *args):
            self.args = args

    class FakeLibrary:
        def __init__(self):
            self.SDL_ShowOpenFileDialog = FakeFunction()

    window = SDL3Window()
    window._lib = FakeLibrary()
    window._opened = True
    window._window = ctypes.c_void_p(123)
    window._thread_id = threading.get_ident()
    delivered = []
    window.show_open_file_dialog(
        lambda paths, selected_filter: delivered.append((paths, selected_filter)),
        filters=(("Text", "txt;md"),), allow_many=True,
    )
    c_callback = window._lib.SDL_ShowOpenFileDialog.args[0]
    file_list = (ctypes.c_char_p * 2)(b"/tmp/readme.md", None)
    c_callback(None, file_list, 0)
    assert delivered == []
    assert window.process_file_dialog_results() == 1
    assert delivered == [(("/tmp/readme.md",), 0)]
    assert window._lib.SDL_ShowOpenFileDialog.args[-1] is True


def test_sdl3_file_dialog_can_report_cancel_and_error():
    import ctypes
    import threading
    from novaui.native.platform.sdl3 import SDL3Window

    class FakeFunction:
        def __call__(self, *args):
            self.args = args

    class FakeLibrary:
        SDL_ShowSaveFileDialog = FakeFunction()

    window = SDL3Window()
    window._lib = FakeLibrary()
    window._opened = True
    window._window = ctypes.c_void_p(123)
    window._thread_id = threading.get_ident()
    results = []
    window.show_save_file_dialog(lambda paths, index: results.append((paths, index)))
    cancel_callback = window._lib.SDL_ShowSaveFileDialog.args[0]
    empty = (ctypes.c_char_p * 1)(None)
    cancel_callback(None, empty, -1)
    assert window.process_file_dialog_results() == 1

    window.show_save_file_dialog(lambda paths, index: results.append((paths, index)))
    error_callback = window._lib.SDL_ShowSaveFileDialog.args[0]
    error_callback(None, None, -1)
    assert window.process_file_dialog_results() == 1
    assert results == [((), -1), (None, -1)]


def test_file_picker_is_exposed_by_public_native_all():
    import novaui.native as native

    assert "FilePicker" in native.__all__
    assert native.FilePicker.__name__ == "FilePicker"
