"""Cached, fault-tolerant facade for market data providers."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Sequence
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


_NESTED_PROVIDER_FIELD = "_market_data_provider"


class MarketDataService:
    """Read facade with transparent caching and provider fallback.

    Reads walk an ordered provider ``chain`` (default: ``[primary, fallback]``).
    Providers are tried left to right until one succeeds; a structural
    ``NotImplementedError`` is skipped without a retry or a health flip, and an
    empty OHLCV result falls through to the next provider.  The first chain
    link receives two attempts before the service moves on.
    """

    def __init__(
        self,
        primary_provider: MarketDataProvider,
        fallback_provider: MarketDataProvider,
        cache: InMemoryTTLCache | None = None,
        *,
        chain: Sequence[MarketDataProvider] | None = None,
    ):
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._cache = cache or InMemoryTTLCache()
        self._chain = list(chain) if chain is not None else [primary_provider, fallback_provider]
        if not self._chain:
            raise ValueError("market-data provider chain must not be empty")
        self._last_successful_fetch: datetime | None = None
        self._active_provider_name: str | None = None
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

    def _read(
        self,
        key: str,
        operation: str,
        *args: Any,
        **kwargs: Any,
    ) -> MarketDataResult:
        cached = self._cache.get(key)
        if cached is not CACHE_MISS:
            logger.info(_event("market_data.cache_hit", cache_key=key))
            return MarketDataResult(
                cached.data,
                self._metadata(provider=cached.provider, cached=True),
            )

        last_error: Exception | None = None
        for chain_index, provider in enumerate(self._chain):
            attempts = 2 if chain_index == 0 else 1
            for attempt in range(1, attempts + 1):
                try:
                    value = getattr(provider, operation)(*args, **kwargs)
                except NotImplementedError:
                    logger.info(_event(
                        "market_data.provider_unsupported",
                        provider=provider.name,
                        operation=operation,
                    ))
                    break
                except Exception as exc:
                    last_error = exc
                    if chain_index == 0:
                        self._primary_healthy = False
                    logger.warning(_event(
                        "market_data.provider_failed",
                        provider=provider.name,
                        operation=operation,
                        attempt=attempt,
                        attempts=attempts,
                    ), exc_info=True)
                    if attempt < attempts:
                        continue
                    break
                else:
                    if operation == "get_historical_ohlcv" and _is_empty_ohlcv(value):
                        logger.info(_event(
                            "market_data.provider_empty_result",
                            provider=provider.name,
                            operation=operation,
                        ))
                        break
                    reported_provider = provider.name
                    if isinstance(value, dict):
                        nested_provider = value.pop(_NESTED_PROVIDER_FIELD, None)
                        if isinstance(nested_provider, str) and nested_provider:
                            reported_provider = nested_provider
                    else:
                        nested_provider = getattr(value, "provider", None)
                        if isinstance(nested_provider, str) and nested_provider:
                            reported_provider = nested_provider
                    if chain_index == 0:
                        self._primary_healthy = reported_provider == provider.name
                    self._active_provider_name = reported_provider
                    self._last_successful_fetch = datetime.now(timezone.utc)
                    logger.info(_event(
                        "market_data.provider_success",
                        provider=reported_provider,
                        operation=operation,
                        attempt=attempt,
                        chain_index=chain_index,
                    ))
                    self._cache.set(
                        key, _CachedProviderValue(value, provider=reported_provider)
                    )
                    return MarketDataResult(
                        value, self._metadata(provider=reported_provider, cached=False)
                    )
            if chain_index == 0 and len(self._chain) > 1 and last_error is not None:
                logger.error(_event(
                    "market_data.provider_failed_using_fallback",
                    provider=provider.name,
                    fallback=self._chain[1].name,
                    operation=operation,
                ))

        logger.error(_event(
            "market_data.all_providers_failed",
            operation=operation,
            chain=[provider.name for provider in self._chain],
        ))
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"no market-data provider produced a result for {operation}")

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

    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> MarketDataResult:
        normalized = symbol.strip().upper()
        return self._read(
            f"ohlcv:{normalized}:{period}:{interval}",
            "get_historical_ohlcv",
            normalized,
            period=period,
            interval=interval,
        )

    def provider_status(self) -> dict[str, Any]:
        return {
            "provider": self._primary.name,
            "healthy": self._primary_healthy,
            "cacheTTL": self._cache.ttl_seconds,
            "lastSuccessfulFetch": self._last_successful_fetch,
            "fallbackEnabled": self._primary.name != self._fallback.name,
            "chain": [provider.name for provider in self._chain],
            "activeProvider": self._active_provider_name,
        }


def _cache_ttl_from_environment() -> float:
    try:
        return max(0, float(os.environ.get("MARKET_DATA_CACHE_TTL_SECONDS", "30")))
    except ValueError:
        logger.warning(_event("market_data.invalid_cache_ttl_using_default"))
        return 30


def _is_empty_ohlcv(value: Any) -> bool:
    """An empty OHLCV result falls through to the next provider (MD-03)."""
    return isinstance(value, (list, tuple)) and len(value) == 0


def _build_service() -> MarketDataService:
    fallback = SeedProvider()
    provider_name = os.environ.get("MARKET_DATA_PROVIDER", "yahoo").lower()
    if provider_name == "upstox":
        from services.providers.upstox_instrument_mapper import (
            UpstoxInstrumentMapper,
        )
        from services.providers.upstox_instrument_source import (
            UpstoxInstrumentMasterError,
            load_instrument_master,
        )
        from services.providers.upstox_provider import UpstoxMarketDataProvider

        try:
            master_mapping = load_instrument_master()
        except UpstoxInstrumentMasterError as exc:
            raise RuntimeError(
                "UPSTOX_MARKET_DATA_PROVIDER requested but the NSE_EQ instrument "
                f"master failed validation: {exc}"
            ) from exc
        mapper = UpstoxInstrumentMapper(master_mapping=master_mapping)
        primary = UpstoxMarketDataProvider(
            instrument_mapper=mapper,
            seed_provider=fallback,
        )
        yahoo = YahooFinanceProvider(fallback)
        chain = [primary, yahoo, fallback]
    elif provider_name == "seed":
        primary = fallback
        chain = [fallback]
    else:
        primary = YahooFinanceProvider(fallback)
        chain = [primary, fallback]
    logger.info(
        _event(
            "market_data.service_configured",
            provider=primary.name,
            chain=[provider.name for provider in chain],
        )
    )
    return MarketDataService(primary, fallback, InMemoryTTLCache(_cache_ttl_from_environment()), chain=chain)


market_data_service = _build_service()
