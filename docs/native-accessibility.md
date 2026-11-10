# Native accessibility semantics

Yuktara UI builds a backend-neutral accessibility snapshot from its retained
layout tree. It is intended as the stable input contract for future native
providers. It is **not** a native accessibility provider and does not currently
expose a UI Automation, NSAccessibility or AT-SPI tree to the operating system.

## Building a semantic snapshot

```python
from novaui.native import LayoutEngine, LayoutNode, Rect, build_accessibility_tree

save = LayoutNode(
    "text",
    text="Save",
    accessibility_role="button",
    accessibility_label="Save document",
    accessibility_identifier="document.save",
    accessibility_actions=("activate",),
)
root = LayoutNode.column(save, accessibility_role="group", accessibility_label="Editor")
LayoutEngine().layout(root, Rect(0, 0, 900, 600))
semantics = build_accessibility_tree(root)
```

Each immutable `SemanticNode` can contain its role, label, value, hint,
disabled/checked/selected/expanded/focused state, stable identifier, role
description, orientation, live-region politeness, read-only/required/invalid
state, numeric range metadata, supported action names, logical-pixel bounds and
semantic children.

## Node metadata

Set these properties on `LayoutNode`:

| Property | Meaning |
|---|---|
| `accessibility_identifier` | Stable app-defined identifier, unique within the exposed snapshot. |
| `accessibility_role_description` | Optional human-readable refinement of a standard role. |
| `accessibility_orientation` | `horizontal` or `vertical` for composite controls. |
| `accessibility_live` | `off`, `polite` or `assertive`; a provider must still implement announcement delivery. |
| `accessibility_hidden` | Prunes the node and all descendants from the semantic snapshot. |
| `accessibility_read_only`, `accessibility_required`, `accessibility_invalid` | Optional form/control states. |
| `accessibility_range_min`, `accessibility_range_max`, `accessibility_range_value` | Finite numeric range values, validated for ordering and bounds. |
| `accessibility_actions` | Supported action hints from the standard vocabulary below. |

Supported actions are `activate`, `collapse`, `decrement`, `dismiss`,
`expand`, `focus`, `scroll_backward`, `scroll_forward`, `set_value` and
`show_menu`. These are declarations for a provider adapter; the provider is
responsible for mapping each action to the matching widget callback or runtime
operation.

Progress bars and sliders publish numeric range metadata automatically.
Sliders also publish horizontal orientation and increment/decrement/set-value
actions. Text fields publish their read-only state. Dropdowns publish their
option-selector role description and expand/collapse/set-value actions. Radio
groups and segmented controls publish their layout orientation.

## Hidden content, identifiers and overlays

A hidden node removes its complete subtree from accessibility exposure. Visible
identifiers must be unique; duplicate identifiers raise `ValueError` so an OS
provider does not receive an ambiguous element reference.

When a modal overlay is active, the snapshot contains the topmost modal and
overlays above it, but not the obscured application subtree or overlays behind
the modal. This scope is established before identifier checks, so identifiers
in content that is not exposed do not conflict with the active modal tree. Pass
`runtime.overlays.entries` to include overlay semantics:

```python
semantics = build_accessibility_tree(
    runtime.root,
    overlays=runtime.overlays.entries,
)
```

Node bounds are expressed in the framework's logical window coordinate space.
A platform adapter must translate those bounds into that platform's expected
screen/window coordinate system and account for the current display scale.

## Current platform boundary

The semantic snapshot, keyboard focus state, visible focus rings, modal focus
scope and component roles/states have backend-neutral regression coverage.
This does not certify screen-reader behavior. Native UI Automation,
NSAccessibility and AT-SPI bridges, action dispatch from those APIs, live-region
announcement events, native focus notifications, and platform testing with
assistive technologies remain future work. The Linux/Xvfb SDL3/Skia smoke test
only verifies window creation and frame presentation; it is not an accessibility
test.
