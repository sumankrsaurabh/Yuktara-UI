# Native retained component tree

`Component.rebuild()` reconciles a newly built `LayoutNode` description with the
previous tree. Matching nodes are updated in place, preserving their identity
for input dispatch and other runtime state.

## Keyed children

```python
from novaui.native.layout import LayoutNode
from novaui.native.reactivity import Component

items = ["alpha", "beta"]
component = Component(lambda: LayoutNode.column(*[
    LayoutNode("text", text=value, key=value) for value in items
]))
component.mount()

items[:] = ["beta", "alpha"]
component.invalidate()
component.scheduler.flush()
```

Keys must be unique among siblings. Keyed children match by key across
reordering. Unkeyed children match by position when node kinds are compatible.
A kind change replaces that node and reports the old/new instances as
removed/created. `Component.last_reconcile` exposes `ReconcileResult` with
`created`, `reused` and `removed` tuples.

## Reconciled versus runtime-owned fields

Declarative `LayoutNode` dataclass fields are copied automatically, excluding
child references and derived geometry. This includes visuals, typography,
accessibility metadata, event callbacks, paint callbacks and grid settings.
Text layout is invalidated after an update so it cannot be reused with stale
text or style configuration. Live accessibility focus, scroll offsets and text
scroll offsets remain attached to compatible reused nodes.

The runtime keeps its dispatcher when the component rebuilds. It updates the
root reference and drops detached nodes from pointer capture, hover, touch
scroll and focus-history collections. This lets compatible state-driven
rebuilds retain active focus and interactions without retaining removed nodes.

## Current boundaries

This is a reconciler for the native `LayoutNode` tree, not a general virtual DOM.
It does not provide arbitrary component-local state stores, per-node mount/unmount
effects, keyed animation state or fine-grained subtree scheduling. Those can be
added separately without changing the basic node identity contract.
