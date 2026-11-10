# Native retained component tree

Yuktara UI native `Component.rebuild()` now reconciles the newly built `LayoutNode` description with the previous tree. Matching nodes are updated in place, preserving object identity and their runtime geometry until the next layout pass.

## Keyed children

```python
from novaui.native.layout import LayoutNode
from novaui.native.reactivity import Component

items = ["alpha", "beta"]
component = Component(lambda: LayoutNode.column(*[
    LayoutNode("text", text=value, key=value) for value in items
]))
component.mount()

# Reorder and rebuild: nodes with matching keys retain identity.
items[:] = ["beta", "alpha"]
component.invalidate()
component.scheduler.flush()
```

Keys must be unique among siblings. Keyed children match by key across reordering. Unkeyed children match by position when their node kinds are compatible. A kind change replaces that node and reports the old/new instances as removed/created.

`Component.last_reconcile` exposes a `ReconcileResult` with `created`, `reused` and `removed` node tuples. The legacy 0.x runtime is not modified.

## Current boundaries

This is a minimal reconciler for the native `LayoutNode` tree, not yet a general virtual-DOM diff. It does not implement component-local state preservation, lifecycle hooks per node, animation transitions, keyed state stores or fine-grained subtree scheduling. Those are separate follow-up work.
