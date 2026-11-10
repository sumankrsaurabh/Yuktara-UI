"""Yuktara native design-system gallery.

Run with: python examples/native/design_system_gallery.py
Add --dark to inspect the dark semantic palette.
"""
from __future__ import annotations

import sys

from novaui.native.dependencies import ensure_skia_python

ensure_skia_python()
import skia

from novaui.native import (
    Alert,
    AppBar,
    Avatar,
    Badge,
    Button,
    Chip,
    FloatingActionButton,
    IconButton,
    Label,
    ListTile,
    NativeRuntime,
    NativeTheme,
    RenderSize,
    ScrollView,
    SkiaRenderer,
    Surface,
    Switch,
    TextField,
    column,
    row,
)
from novaui.native.platform import SDL3Window
from novaui.native.platform.skia_bridge import renderer_frame


def main() -> None:
    theme = NativeTheme.dark() if "--dark" in sys.argv else NativeTheme()
    heading = Label("Yuktara Design System", size=30, weight="bold", theme=theme)
    intro = Label(
        "A consistent native language for surfaces, controls, typography and states.",
        color=theme.muted,
        theme=theme,
    )

    actions = Surface(
        variant="low",
        children=(
            Label("Buttons", size=18, weight="semibold", theme=theme),
            row(
                Button("Primary", on_click=lambda _e: print("Primary"), theme=theme),
                Button("Tonal", variant="tonal", on_click=lambda _e: print("Tonal"), theme=theme),
                Button("Outlined", variant="outline", on_click=lambda _e: print("Outlined"), theme=theme),
                spacing=8,
                wrap=True,
            ),
            row(
                Button("Text", variant="text", on_click=lambda _e: print("Text"), theme=theme),
                Button("Destructive", variant="danger", on_click=lambda _e: print("Danger"), theme=theme),
                IconButton("＋", "Create", on_click=lambda _e: print("Create"), variant="tonal", theme=theme),
                spacing=8,
                wrap=True,
            ),
        ),
        theme=theme,
    )

    surfaces = Surface(
        variant="base",
        children=(
            Label("Surface roles", size=18, weight="semibold", theme=theme),
            row(
                Surface(variant="lowest", children=(Label("Lowest", theme=theme),), padding=12, theme=theme),
                Surface(variant="low", children=(Label("Low", theme=theme),), padding=12, theme=theme),
                Surface(variant="high", children=(Label("High", theme=theme),), padding=12, theme=theme),
                spacing=8,
                wrap=True,
            ),
            row(
                Badge("Neutral", theme=theme),
                Badge("Success", "success", theme=theme),
                Badge("Warning", "warning", theme=theme),
                Badge("Critical", "danger", theme=theme),
                spacing=8,
                wrap=True,
            ),
        ),
        theme=theme,
    )

    navigation = Surface(
        variant="base",
        children=(
            Label("Application bars", size=18, weight="semibold", theme=theme),
            AppBar(
                "Yuktara Workspace",
                subtitle="Design system preview",
                leading=IconButton("☰", "Open navigation", theme=theme),
                actions=(
                    IconButton("⌕", "Search", variant="tonal", theme=theme),
                    IconButton("⋯", "More options", variant="tonal", theme=theme),
                ),
                theme=theme,
            ),
            AppBar(
                "Compact toolbar",
                size="compact",
                variant="outlined",
                actions=(IconButton("＋", "Create", theme=theme),),
                theme=theme,
            ),
        ),
        theme=theme,
    )

    feedback = Surface(
        variant="low",
        children=(
            Label("Feedback and status", size=18, weight="semibold", theme=theme),
            Alert("Your workspace is ready to use.", title="All set", variant="success", theme=theme),
            Alert("A network connection is required to sync changes.", title="Sync paused", variant="warning", theme=theme),
            Alert("The document could not be saved.", title="Save failed", variant="danger", theme=theme),
        ),
        theme=theme,
    )

    inputs = Surface(
        variant="outlined",
        children=(
            Label("Input controls", size=18, weight="semibold", theme=theme),
            TextField(placeholder="Search or enter a value", theme=theme),
            Switch("Enable notifications", checked=True, theme=theme),
        ),
        theme=theme,
    )

    content = Surface(
        variant="low",
        children=(
            Label("Content components", size=18, weight="semibold", theme=theme),
            row(
                Avatar("Suman Kumar", initials="SK", size="large", theme=theme),
                Avatar("Design team", initials="DT", variant="tertiary", theme=theme),
                Chip("All items", selected=True, theme=theme),
                Chip("Archived", variant="neutral", theme=theme),
                Chip("Synced", variant="success", theme=theme),
                spacing=10,
                wrap=True,
            ),
            ListTile(
                "Project overview",
                subtitle="Last updated just now",
                leading=Avatar("Project", initials="P", theme=theme),
                trailing=Badge("Active", "success", theme=theme),
                theme=theme,
            ),
            ListTile(
                "Design resources",
                subtitle="18 files · Shared with your team",
                leading=Avatar("Design", initials="D", variant="tertiary", theme=theme),
                trailing=Chip("Shared", theme=theme),
                theme=theme,
            ),
        ),
        theme=theme,
    )

    floating_actions = Surface(
        variant="base",
        children=(
            Label("Floating actions", size=18, weight="semibold", theme=theme),
            row(
                FloatingActionButton("Create", size="small", theme=theme),
                FloatingActionButton("Create", size="regular", theme=theme),
                FloatingActionButton("New document", icon="+", extended=True, theme=theme),
                spacing=12,
                wrap=True,
            ),
        ),
        theme=theme,
    )

    root = ScrollView(
        column(
            heading,
            intro,
            actions,
            navigation,
            surfaces,
            inputs,
            content,
            floating_actions,
            feedback,
            spacing=theme.space_4,
            padding=theme.space_6,
            background=theme.background,
        ),
        axis="vertical",
    )
    renderer = SkiaRenderer(RenderSize(1120, 820), skia_module=skia)
    runtime = NativeRuntime(lambda: root, renderer, 1120, 820, clear_color=theme.background)
    window = SDL3Window(
        "Yuktara — Design System",
        1120,
        820,
        high_dpi=True,
        min_width=360,
        min_height=480,
    )
    window.run_runtime(
        runtime,
        lambda _runtime: renderer_frame(renderer, skia_module=skia),
    )


if __name__ == "__main__":
    main()
