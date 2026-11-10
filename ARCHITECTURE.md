# Yuktara UI native architecture boundary

## Runtime pipeline

1. Application build function returns a retained `LayoutNode` tree.
2. `Component` owns lifecycle and reconciles compatible nodes by key.
3. `LayoutEngine` measures intrinsic content and arranges absolute logical-pixel bounds.
4. `LayoutTreePainter` paints backgrounds/text and enters nested clip regions for scroll viewports.
5. `SkiaRenderer` owns a CPU raster surface and exports a snapshot.
6. `skia_bridge` converts the snapshot to RGBA8 and `SDL3Window` presents it.
7. `SDL3EventDecoder` normalizes SDL events; `InputDispatcher` routes pointer/wheel/touch interactions.

## Separation rules

- Layout, event models, state, reconciliation, and dispatch must remain backend-neutral.
- Skia-specific operations stay inside the renderer and text measurement adapter.
- SDL3-specific operations stay inside `platform/sdl3.py` and `platform/sdl3_events.py`.
- Do not reintroduce HTML/CSS/DOM/webview rendering into this package.
- Preserve the old runtime only in its separate branch/distribution; this source package is the native 2.x line.

## Validation policy

Unit tests validate pure Python behavior and injected interfaces. Hardware/window integration must be validated separately on Windows, Linux, and macOS with actual SDL3 and skia-python builds.


## Native component library (2.2 development)

Built-in widgets in `novaui.native.widgets` create retained `LayoutNode` trees.
They do not call SDL3 or Skia directly. The `NativeTheme` semantic token palette
feeds the painter, while `accessibility.py` translates annotated nodes to an
OS-neutral semantic tree. See `docs/native-component-library.md`.
