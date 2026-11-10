"""Deterministic invalidation scheduler with nested batching."""
from __future__ import annotations
from contextlib import contextmanager
from threading import RLock
from typing import Callable

class Scheduler:
    def __init__(self):
        self._pending: dict[object, Callable[[], None]] = {}
        self._batch_depth = 0
        self._flushing = False
        self._lock = RLock()

    def schedule(self, key: object, callback: Callable[[], None]) -> None:
        with self._lock:
            self._pending[key] = callback
            should_flush = self._batch_depth == 0 and not self._flushing
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
                should_flush = self._batch_depth == 0
            if should_flush:
                self.flush()

    def flush(self) -> int:
        with self._lock:
            if self._flushing or self._batch_depth:
                return 0
            self._flushing = True
        count = 0
        try:
            while True:
                with self._lock:
                    if not self._pending:
                        break
                    pending = tuple(self._pending.values())
                    self._pending.clear()
                for callback in pending:
                    callback()
                    count += 1
        finally:
            with self._lock:
                self._flushing = False
        return count

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)
