"""Small observable state primitives for Yuktara UI's native runtime."""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
Subscriber = Callable[[object, object], None]

class State(Generic[T]):
    """A value that notifies subscribers when it changes.

    Equality is checked before notification. Subscribers are called outside
    the lock so they may safely update other state values.
    """
    def __init__(self, value: T):
        self._value = value
        self._subscribers: dict[int, Subscriber] = {}
        self._next_token = 0
        self._lock = RLock()

    @property
    def value(self) -> T:
        with self._lock:
            return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        with self._lock:
            old_value = self._value
            if old_value == new_value:
                return
            self._value = new_value
            callbacks = tuple(self._subscribers.values())
        for callback in callbacks:
            callback(new_value, old_value)

    def set(self, new_value: T) -> None:
        self.value = new_value

    def update(self, updater: Callable[[T], T]) -> T:
        self.value = updater(self.value)
        return self.value

    def subscribe(self, callback: Subscriber, *, fire_immediately: bool = False) -> "Subscription":
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            token = self._next_token
            self._next_token += 1
            self._subscribers[token] = callback
            current = self._value
        if fire_immediately:
            callback(current, current)
        return Subscription(lambda: self._unsubscribe(token))

    def _unsubscribe(self, token: int) -> None:
        with self._lock:
            self._subscribers.pop(token, None)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

@dataclass
class Subscription:
    _cancel: Callable[[], None]
    _active: bool = True
    def cancel(self) -> None:
        if self._active:
            self._active = False
            self._cancel()
    @property
    def active(self) -> bool:
        return self._active
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.cancel()
