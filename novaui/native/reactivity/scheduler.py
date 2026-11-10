"""Deterministic invalidation scheduler with batching and UI-thread affinity."""
from __future__ import annotations

from contextlib import contextmanager
from threading import RLock, get_ident
from typing import Callable


class Scheduler:
    """Coalesce invalidations and optionally marshal them to an owner thread.

    The default scheduler remains synchronous for small standalone components.
    A native runtime binds its scheduler to the thread that owns the window;
    invalidations from other threads are queued until ``flush`` is called on
    that owner thread. This keeps SDL, Skia and retained-tree mutation on one
    predictable UI thread.
    """

    def __init__(self):
        self._pending: dict[object, Callable[[], None]] = {}
        self._batch_depth = 0
        self._flushing = False
        self._lock = RLock()
        self._owner_thread_id: int | None = None

    @property
    def owner_thread_id(self) -> int | None:
        return self._owner_thread_id

    def bind_owner_thread(self, thread_id: int | None = None) -> None:
        """Bind flushes to one thread; repeated binding must use the same ID."""
        resolved = get_ident() if thread_id is None else int(thread_id)
        with self._lock:
            if self._owner_thread_id is not None and self._owner_thread_id != resolved:
                raise RuntimeError("scheduler is already bound to another thread")
            self._owner_thread_id = resolved

    def _is_owner_thread(self) -> bool:
        return self._owner_thread_id is None or get_ident() == self._owner_thread_id

    def schedule(self, key: object, callback: Callable[[], None]) -> None:
        if not callable(callback):
            raise TypeError("scheduled callback must be callable")
        with self._lock:
            self._pending[key] = callback
            should_flush = (
                self._batch_depth == 0 and not self._flushing and self._is_owner_thread()
            )
        if should_flush:
            self.flush()

    @contextmanager
    def batch(self):
        with self._lock:
            self._batch_depth += 1
        try:
            yield
        finally:
            with self._lock:
                self._batch_depth -= 1
                should_flush = (
                    self._batch_depth == 0 and not self._flushing and self._is_owner_thread()
                )
            if should_flush:
                self.flush()

    def flush(self) -> int:
        with self._lock:
            if not self._is_owner_thread():
                raise RuntimeError("scheduler callbacks must be flushed on the owner thread")
            if self._flushing or self._batch_depth:
                return 0
            self._flushing = True
        count = 0
        try:
            while True:
                with self._lock:
                    if not self._pending:
                        break
                    pending = tuple(self._pending.items())
                    self._pending.clear()
                for index, (_key, callback) in enumerate(pending):
                    try:
                        callback()
                    except Exception:
                        # A failing callback must not discard unrelated work
                        # that was in the same drained batch. Preserve newer
                        # callbacks already queued under the same key.
                        with self._lock:
                            for pending_key, pending_callback in pending[index + 1:]:
                                self._pending.setdefault(pending_key, pending_callback)
                        raise
                    count += 1
        finally:
            with self._lock:
                self._flushing = False
        return count

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)
