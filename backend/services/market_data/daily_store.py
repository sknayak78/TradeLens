"""Tiny flat-file store for completed daily OHLCV series (session-scoped).

Each entry is keyed by the exact market-data cache key (``ohlcv:SYM:1y:1d``)
so the provider series round-trips without slicing or re-derivation.  Entries
expire at the next NSE pre-open (09:15 IST) and are only *served* by
``MarketDataService`` outside the OPEN session, when every stored bar is
final.  The resident layer is a wall-clock :class:`InMemoryTTLCache` using
per-entry TTLs, so the session boundary is honoured without a background
worker; the durable layer is one flat JSON file per key written atomically,
so writes never rewrite unrelated entries.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from services.cache import CACHE_MISS, InMemoryTTLCache
from services.market_data.models import OHLCVBar

logger = logging.getLogger("tradelens.daily_store")

_IST = ZoneInfo("Asia/Kolkata")
_UTC = timezone.utc
_DEFAULT_STORE_ENV = "INTEL_DAILY_BARS_PATH"
# Guard against a wildly misconfigured calendar (not a real expiry ceiling).
_MAX_EXPIRY_SECONDS = 90 * 24 * 3600.0


def next_pre_open_epoch(now: datetime | None = None) -> float:
    """Epoch seconds of the upcoming pre-open 09:15 IST (next weekday)."""
    moment = now if now is not None else datetime.now(_UTC)
    india_now = moment.astimezone(_IST)
    candidate = india_now.replace(hour=9, minute=15, second=0, microsecond=0)
    if india_now >= candidate:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.timestamp()


def default_store_dir() -> Path:
    """Resolve the store directory from env or the system temp area."""
    env = os.environ.get(_DEFAULT_STORE_ENV)
    if env:
        return Path(env).expanduser()
    return Path(tempfile.gettempdir()) / "tradelens_intel_daily_bars"


@dataclass(frozen=True)
class StoredSeries:
    """A persisted provider series plus the provider that produced it."""

    provider: str
    bars: tuple[OHLCVBar, ...]


def _bar_to_dict(bar: OHLCVBar) -> dict[str, Any]:
    return {
        "timestamp": bar.timestamp.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
    }


def _bar_from_dict(data: dict[str, Any]) -> OHLCVBar:
    return OHLCVBar(
        timestamp=datetime.fromisoformat(data["timestamp"]),
        open=data["open"],
        high=data["high"],
        low=data["low"],
        close=data["close"],
        volume=data["volume"],
    )


def _file_key(key: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in key)


class DailyBarStore:
    """Restart-safe, session-scoped flat-file store for daily bar series."""

    def __init__(self, base_dir: str | os.PathLike | None = None):
        self._dir = Path(base_dir) if base_dir is not None else default_store_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._resident = InMemoryTTLCache(ttl_seconds=0, clock=time.monotonic)
        self._lock = threading.RLock()

    def _path_for(self, key: str) -> Path:
        return self._dir / f"{_file_key(key)}.json"

    def get(self, key: str) -> StoredSeries | None:
        with self._lock:
            cached = self._resident.get(key)
            if cached is not CACHE_MISS:
                return cached
            return self._load(key)

    def _load(self, key: str) -> StoredSeries | None:
        path = self._path_for(key)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "tradelens.daily_store.read_failed key=%s error=%s", key, exc
            )
            return None
        try:
            expires_at = float(payload["expires_at"])
            if expires_at <= time.time():
                return None
            series = StoredSeries(
                provider=str(payload["provider"]),
                bars=tuple(_bar_from_dict(item) for item in payload["bars"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "tradelens.daily_store.corrupt key=%s error=%s", key, exc
            )
            return None
        remaining = expires_at - time.time()
        self._resident.set(
            key, series, ttl_seconds=min(max(remaining, 1.0), _MAX_EXPIRY_SECONDS)
        )
        return series

    def set(
        self,
        key: str,
        provider: str,
        bars: Sequence[OHLCVBar],
    ) -> None:
        expires_at = next_pre_open_epoch()
        remaining = expires_at - time.time()
        series = StoredSeries(provider=provider, bars=tuple(bars))
        with self._lock:
            self._resident.set(
                key,
                series,
                ttl_seconds=min(max(remaining, 1.0), _MAX_EXPIRY_SECONDS),
            )
            self._flush_key(key, series, expires_at)

    def _flush_key(self, key: str, series: StoredSeries, expires_at: float) -> None:
        payload = {
            "provider": series.provider,
            "expires_at": expires_at,
            "bars": [_bar_to_dict(bar) for bar in series.bars],
        }
        path = self._path_for(key)
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
            os.replace(tmp, path)
        except OSError as exc:
            logger.warning(
                "tradelens.daily_store.write_failed key=%s error=%s", key, exc
            )

    def clear(self) -> None:
        with self._lock:
            self._resident.clear()
            for path in self._dir.glob("*.json"):
                try:
                    path.unlink()
                except OSError as exc:
                    logger.warning(
                        "tradelens.daily_store.clear_failed path=%s error=%s",
                        path,
                        exc,
                    )