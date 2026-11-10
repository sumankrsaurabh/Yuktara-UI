"""Lifecycle-aware component wrapper around a native LayoutNode."""
from __future__ import annotations
from typing import Callable
from .state import State, Subscription
from .scheduler import Scheduler
from .reconcile import reconcile, ReconcileResult

class Component:
    """Owns a layout node and subscriptions used to keep it current.

    `build` may return a LayoutNode. State bindings should use `bind_state`
    so a changed value schedules one component rebuild. This intentionally
    leaves the legacy 0.x component API untouched.
    """
    def __init__(self, build: Callable[[], object], *, scheduler: Scheduler | None = None,
                 on_invalidate: Callable[["Component"], None] | None = None):
        if not callable(build):
            raise TypeError("build must be callable")
        self._build_fn = build
        self.scheduler = scheduler or Scheduler()
        self.on_invalidate = on_invalidate
        self.node = None
        self.mounted = False
        self.dirty = True
        self._subscriptions: list[Subscription] = []
        self._binding_deactivators: list[Callable[[], None]] = []
        self.build_count = 0
        self.last_reconcile: ReconcileResult | None = None

    def mount(self):
        if self.mounted:
            return self.node
        self.mounted = True
        self.rebuild()
        return self.node

    def bind_state(self, state: State, apply: Callable[[object, object], None] | None = None):
        if not isinstance(state, State):
            raise TypeError("bind_state expects a State instance")
        active = [True]

        def changed(new, old):
            if not active[0]:
                return

            def apply_and_invalidate():
                # State subscribers may run on worker threads. Keep user-supplied
                # apply callbacks on the scheduler's owner thread alongside the
                # retained-tree rebuild they trigger.
                if not active[0]:
                    return
                if apply is not None:
                    apply(new, old)
                self.invalidate()

            # Use a unique queue key so each apply callback is delivered, while
            # component invalidations themselves remain coalesced by `self`.
            self.scheduler.schedule(object(), apply_and_invalidate)

        subscription = state.subscribe(changed)
        self._subscriptions.append(subscription)
        self._binding_deactivators.append(lambda: active.__setitem__(0, False))
        return subscription

    def invalidate(self):
        if not self.mounted:
            self.dirty = True
            return
        self.dirty = True
        self.scheduler.schedule(self, self._scheduled_rebuild)

    def _scheduled_rebuild(self):
        if self.mounted and self.dirty:
            self.rebuild()

    def rebuild(self):
        if not self.mounted:
            return None
        candidate = self._build_fn()
        self.last_reconcile = reconcile(self.node, candidate)
        self.node = self.last_reconcile.root
        self.dirty = False
        self.build_count += 1
        if self.on_invalidate is not None:
            self.on_invalidate(self)
        return self.node

    def unmount(self):
        if not self.mounted and not self._subscriptions:
            return
        self.mounted = False
        for deactivate in self._binding_deactivators:
            deactivate()
        self._binding_deactivators.clear()
        for subscription in self._subscriptions:
            subscription.cancel()
        self._subscriptions.clear()
        self.node = None
        self.dirty = True
