"""Ownership contract for the no-copy market-data cache.

Cached values are owned by the cache and MUST be treated as immutable by
consumers.  The cache does not make defensive copies: the same object is
stored and returned on every hit, and the resident ``DailyBarStore`` shares
one frozen ``StoredSeries`` across reads.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

from services.cache import CACHE_MISS, InMemoryTTLCache
from services.market_data.daily_store import DailyBarStore, StoredSeries
from services.market_data.models import OHLCVBar


def test_cache_stores_without_defensive_copy() -> None:
    cache = InMemoryTTLCache()
    value = {"sequence": [1, 2, 3]}

    cache.set("k", value)

    assert cache.get("k") is value


def test_cache_returns_same_identity_across_hits() -> None:
    cache = InMemoryTTLCache()
    # A container value, not a tuple of immutable atoms: deepcopy() returns
    # such tuples unchanged, so an atom-only fixture could not detect copying.
    value = {"ticks": [1, 2, 3]}

    cache.set("k", value)

    assert cache.get("k") is value
    assert cache.get("k") is cache.get("k")


def test_identity_ends_at_per_entry_ttl_expiry() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    cache = InMemoryTTLCache(ttl_seconds=30, clock=clock)
    value = {"v": 1}

    cache.set("k", value, ttl_seconds=10)
    now[0] += 10.1

    assert cache.get("k") is CACHE_MISS


def test_daily_store_shares_stored_series_identity(tmp_path) -> None:
    store = DailyBarStore(tmp_path)
    bars = (
        OHLCVBar(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        ),
    )

    store.set("ohlcv:TCS:1y:1d", "stub", bars)

    first = store.get("ohlcv:TCS:1y:1d")
    second = store.get("ohlcv:TCS:1y:1d")

    assert first is not None
    assert first is second
    assert isinstance(first, StoredSeries)
    assert first.bars is bars


def test_stored_series_cannot_be_mutated_by_assignment() -> None:
    stored = StoredSeries(
        provider="stub",
        bars=(
            OHLCVBar(
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0,
            ),
        ),
    )

    try:
        stored.provider = "other"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("StoredSeries must be an immutable frozen dataclass")
    assert stored.provider == "stub"