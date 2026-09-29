"""Small, thread-safe in-memory TTL cache for market-provider reads."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any, Callable


CACHE_MISS = object()


@dataclass
class _CacheEntry:
    expires_at: float
    value: Any


class InMemoryTTLCache:
    """A process-local cache which owns every value it stores.

    The cache never copies values on the way in or out, so a hit returns the
    very object that was stored.  Cached values are owned by the cache and
    consumers MUST treat returned cached values as immutable; a consumer that
    needs to mutate a value must take its own copy first.
    """

    def __init__(self, ttl_seconds: float = 30, clock: Callable[[], float] = monotonic):
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return CACHE_MISS
            if entry.expires_at <= self._clock():
                del self._entries[key]
                return CACHE_MISS
            return entry.value

    def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        effective_ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        with self._lock:
            self._entries[key] = _CacheEntry(
                expires_at=self._clock() + effective_ttl,
                value=value,
            )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
