"""Cached, fault-tolerant facade for market data providers."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from services.cache import CACHE_MISS, InMemoryTTLCache
from services.market_data_provider import MarketDataProvider
from services.providers.seed_provider import SeedProvider
from services.providers.yahoo_finance_provider import YahooFinanceProvider

logger = logging.getLogger("tradelens.market_data")


def _event(event: str, **fields: Any) -> str:
    """Serialize operational fields consistently for standard Python logging."""
    return json.dumps({"event": event, **fields}, sort_keys=True)


@dataclass(frozen=True)
class MarketDataMetadata:
    provider: str
    cached: bool
    as_of: datetime
    market_status: str

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "cached": self.cached,
            "asOf": self.as_of,
            "marketStatus": self.market_status,
        }


@dataclass(frozen=True)
class MarketDataResult:
    data: Any
    metadata: MarketDataMetadata


@dataclass(frozen=True)
class _CachedProviderValue:
    data: Any
    provider: str


class MarketDataService:
    """Read facade with transparent caching and provider fallback."""

    def __init__(
        self,
        primary_provider: MarketDataProvider,
        fallback_provider: MarketDataProvider,
        cache: InMemoryTTLCache | None = None,
    ):
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._cache = cache or InMemoryTTLCache()
        self._last_successful_fetch: datetime | None = None
        self._primary_healthy = primary_provider.name == fallback_provider.name

    def _market_status(self, now: datetime | None = None) -> str:
        india_now = (now or datetime.now(timezone.utc)).astimezone(
            ZoneInfo("Asia/Kolkata")
        )
        if india_now.weekday() >= 5:
            return "WEEKEND"
        current_time = india_now.time()
        if time(9, 0) <= current_time < time(9, 15):
            return "PRE_OPEN"
        if time(9, 15) <= current_time < time(15, 30):
            return "OPEN"
        return "CLOSED"

    def _metadata(self, provider: str, cached: bool) -> MarketDataMetadata:
        return MarketDataMetadata(
            provider=provider,
            cached=cached,
            as_of=datetime.now(timezone.utc),
            market_status=self._market_status(),
        )

    def _read(self, key: str, operation: str, *args: Any) -> MarketDataResult:
        cached = self._cache.get(key)
        if cached is not CACHE_MISS:
            logger.info(_event("market_data.cache_hit", cache_key=key))
            return MarketDataResult(
                cached.data,
                self._metadata(provider=cached.provider, cached=True),
            )

        for attempt in range(1, 3):
            try:
                value = getattr(self._primary, operation)(*args)
                self._primary_healthy = True
                self._last_successful_fetch = datetime.now(timezone.utc)
                logger.info(_event(
                    "market_data.provider_success",
                    provider=self._primary.name,
                    operation=operation,
                    attempt=attempt,
                ))
                self._cache.set(
                    key, _CachedProviderValue(value, provider=self._primary.name)
                )
                return MarketDataResult(
                    value, self._metadata(provider=self._primary.name, cached=False)
                )
            except Exception:
                if attempt == 1:
                    logger.warning(_event(
                        "market_data.provider_retry",
                        provider=self._primary.name,
                        operation=operation,
                        retry_attempt=1,
                    ), exc_info=True)
                    continue
                self._primary_healthy = False
            logger.exception(_event(
                "market_data.provider_failed_using_fallback",
                provider=self._primary.name,
                fallback=self._fallback.name,
                operation=operation,
            ))
            value = getattr(self._fallback, operation)(*args)
            self._cache.set(
                key, _CachedProviderValue(value, provider=self._fallback.name)
            )
            return MarketDataResult(
                value, self._metadata(provider=self._fallback.name, cached=False)
            )

        raise RuntimeError("unreachable market-data provider state")

    def get_market_summary(self) -> MarketDataResult:
        return self._read("market_summary", "get_market_summary")

    def get_stock(self, symbol: str) -> MarketDataResult:
        normalized = symbol.strip().upper()
        return self._read(f"stock:{normalized}", "get_stock", normalized)

    def get_stock_insight(self, symbol: str) -> MarketDataResult:
        normalized = symbol.strip().upper()
        return self._read(f"stock_insight:{normalized}", "get_stock_insight", normalized)

    def search_stocks(self, query: str, limit: int = 20) -> MarketDataResult:
        return self._read(f"search:{query.strip().lower()}:{limit}", "search_stocks", query, limit)

    def get_opportunities(self) -> MarketDataResult:
        return self._read("opportunities", "get_opportunities")

    def get_all_stocks(self) -> MarketDataResult:
        return self._read("all_stocks", "get_all_stocks")

    def get_default_watchlist_symbols(self) -> MarketDataResult:
        return self._read("default_watchlist", "get_default_watchlist_symbols")

    def provider_status(self) -> dict[str, Any]:
        return {
            "provider": self._primary.name,
            "healthy": self._primary_healthy,
            "cacheTTL": self._cache.ttl_seconds,
            "lastSuccessfulFetch": self._last_successful_fetch,
            "fallbackEnabled": self._primary.name != self._fallback.name,
        }


def _cache_ttl_from_environment() -> float:
    try:
        return max(0, float(os.environ.get("MARKET_DATA_CACHE_TTL_SECONDS", "30")))
    except ValueError:
        logger.warning(_event("market_data.invalid_cache_ttl_using_default"))
        return 30


def _build_service() -> MarketDataService:
    fallback = SeedProvider()
    provider_name = os.environ.get("MARKET_DATA_PROVIDER", "yahoo").lower()
    primary: MarketDataProvider = fallback if provider_name == "seed" else YahooFinanceProvider(fallback)
    logger.info(_event("market_data.service_configured", provider=primary.name))
    return MarketDataService(primary, fallback, InMemoryTTLCache(_cache_ttl_from_environment()))


market_data_service = _build_service()
