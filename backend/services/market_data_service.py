"""Cached, fault-tolerant facade for market data providers."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, time as wall_time, timezone
from time import perf_counter
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo

from services.cache import CACHE_MISS, InMemoryTTLCache
from services.market_data.diagnostic_logging import (
    classify_error,
    subject_of,
)
from services.market_data_provider import MarketDataProvider, ProviderRateLimitedError
from services.providers.seed_provider import SeedProvider
from services.providers.yahoo_finance_provider import YahooFinanceProvider

logger = logging.getLogger("tradelens.market_data")

#: Production cap on how long a read may honor a provider's ``Retry-After``.
#:
#: Deliberately conservative.  Stage-2 screening runs up to 16 concurrent
#: workers, so a larger cap would let many workers sleep at once and push the
#: 60s discovery deadline.  Kept as a constructor value so it can be raised
#: later without redesign.  This is a policy guard, not a claim about Upstox's
#: actual limit.
DEFAULT_MAX_RETRY_AFTER_SECONDS = 5.0

#: Operations for which waiting on a rate limit is permitted.
#:
#: ``get_historical_ohlcv`` is the Stage-2 screening read.  Deep analysis
#: resolves through ``get_stock`` / ``get_stock_insight`` instead, so it is
#: excluded structurally rather than via caller-side state: it runs after
#: screening, is already the slowest phase, and tolerates partial failure, so
#: sleeping there would turn a working fallback into a timeout.
_RETRY_AFTER_WAIT_OPERATIONS = frozenset({"get_historical_ohlcv"})


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

    A provider that reports temporary throttling (``ProviderRateLimitedError``)
    changes how that second attempt is spent, never how many are available:
    a short advisory wait is honored, an absent/long one skips the retry
    outright and falls back.  Non-rate-limit errors are unaffected.
    """

    def __init__(
        self,
        primary_provider: MarketDataProvider,
        fallback_provider: MarketDataProvider,
        cache: InMemoryTTLCache | None = None,
        *,
        chain: Sequence[MarketDataProvider] | None = None,
        max_retry_after_seconds: float = DEFAULT_MAX_RETRY_AFTER_SECONDS,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._cache = cache or InMemoryTTLCache()
        self._chain = list(chain) if chain is not None else [primary_provider, fallback_provider]
        if not self._chain:
            raise ValueError("market-data provider chain must not be empty")
        self._max_retry_after_seconds = max(0.0, float(max_retry_after_seconds))
        self._sleeper = sleeper
        self._last_successful_fetch: datetime | None = None
        self._active_provider_name: str | None = None
        self._primary_healthy = primary_provider.name == fallback_provider.name
        self._rate_limit_waits = 0
        self._rate_limit_skips = 0
        self._last_rate_limit_at: datetime | None = None

    def _market_status(self, now: datetime | None = None) -> str:
        india_now = (now or datetime.now(timezone.utc)).astimezone(
            ZoneInfo("Asia/Kolkata")
        )
        if india_now.weekday() >= 5:
            return "WEEKEND"
        current_time = india_now.time()
        if wall_time(9, 0) <= current_time < wall_time(9, 15):
            return "PRE_OPEN"
        if wall_time(9, 15) <= current_time < wall_time(15, 30):
            return "OPEN"
        return "CLOSED"

    def _rate_limit_pacing(
        self,
        exc: Exception,
        *,
        operation: str,
        provider: MarketDataProvider,
        retry_budget_available: bool,
        countable: bool,
    ) -> float | None:
        """Apply the Retry-After policy for a throttled provider read.

        Returns the number of seconds actually waited, or ``None`` when no wait
        happened.  This never changes the attempt budget: it only decides
        whether the already-allocated second attempt is spent immediately or
        after a short, capped wait.
        """
        if not isinstance(exc, ProviderRateLimitedError):
            return None

        retry_after = exc.retry_after
        if countable:
            self._last_rate_limit_at = datetime.now(timezone.utc)
        if not retry_budget_available:
            # No further attempt will be made, so there is nothing to pace: a
            # wait here would only add latency before falling back.
            return self._log_rate_limit(
                provider=provider,
                operation=operation,
                retry_after=retry_after,
                countable=countable,
                reason="no_retry_budget",
            )
        if operation not in _RETRY_AFTER_WAIT_OPERATIONS:
            # This operation must not block (deep analysis): fall back rather
            # than stall the slowest phase of the request.
            return self._log_rate_limit(
                provider=provider,
                operation=operation,
                retry_after=retry_after,
                countable=countable,
                reason="operation_not_waitable",
            )
        if retry_after is None or retry_after > self._max_retry_after_seconds:
            # The advisory wait is too long to honor safely, or it was
            # absent/unparseable so there is nothing to trust.  Never guess.
            return self._log_rate_limit(
                provider=provider,
                operation=operation,
                retry_after=retry_after,
                countable=countable,
                reason="no_usable_retry_after",
            )

        if countable:
            self._rate_limit_waits += 1
        self._sleeper(retry_after)
        logger.info(_event(
            "market_data.rate_limit_waited",
            provider=provider.name,
            operation=operation,
            retry_after=retry_after,
            max_retry_after_seconds=self._max_retry_after_seconds,
        ))
        return retry_after

    def _log_rate_limit(
        self,
        *,
        provider: MarketDataProvider,
        operation: str,
        retry_after: float | None,
        countable: bool,
        reason: str,
    ) -> None:
        """Record that a throttled read skipped its retry; returns ``None``."""
        if countable:
            self._rate_limit_skips += 1
        logger.info(_event(
            "market_data.rate_limit_skipped_retry",
            provider=provider.name,
            operation=operation,
            retry_after=retry_after,
            max_retry_after_seconds=self._max_retry_after_seconds,
            reason=reason,
        ))
        return None

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
        subject = subject_of(args)
        # Diagnostic-only: the failure raised by the primary during this read,
        # used to classify the fallback event.  Never alters control flow.
        primary_error: Exception | None = None
        for chain_index, provider in enumerate(self._chain):
            attempts = 2 if chain_index == 0 else 1
            for attempt in range(1, attempts + 1):
                started = perf_counter()
                try:
                    value = getattr(provider, operation)(*args, **kwargs)
                except NotImplementedError:
                    logger.info(_event(
                        "market_data.provider_unsupported",
                        provider=provider.name,
                        operation=operation,
                        **subject,
                    ))
                    break
                except Exception as exc:
                    last_error = exc
                    if chain_index == 0:
                        primary_error = exc
                        if not isinstance(exc, ProviderRateLimitedError):
                            # A transient rate limit is not an unhealthy
                            # provider, so the flip is skipped for it.  Every
                            # other failure keeps the pre-existing behavior.
                            self._primary_healthy = False
                    classified = classify_error(exc)
                    waited = self._rate_limit_pacing(
                        exc,
                        operation=operation,
                        provider=provider,
                        retry_budget_available=attempt < attempts,
                        countable=chain_index == 0,
                    )
                    # Diagnostic-only enrichment: extra fields, unchanged event
                    # name and unchanged error handling.  Makes the durable log
                    # sufficient to attribute every historical attempt.
                    logger.warning(_event(
                        "market_data.provider_failed",
                        provider=provider.name,
                        operation=operation,
                        attempt=attempt,
                        attempts=attempts,
                        chain_index=chain_index,
                        elapsed_ms=round((perf_counter() - started) * 1000, 2),
                        **subject,
                        **classified,
                        **(
                            {"retry_after": exc.retry_after}
                            if isinstance(exc, ProviderRateLimitedError) else {}
                        ),
                    ), exc_info=True)
                    if attempt < attempts and not _skips_remaining_attempt(
                        exc, waited, self._max_retry_after_seconds
                    ):
                        continue
                    break
                else:
                    elapsed_ms = round((perf_counter() - started) * 1000, 2)
                    if operation == "get_historical_ohlcv" and _is_empty_ohlcv(value):
                        logger.info(_event(
                            "market_data.provider_empty_result",
                            provider=provider.name,
                            operation=operation,
                            attempt=attempt,
                            chain_index=chain_index,
                            elapsed_ms=elapsed_ms,
                            **subject,
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
                        serving_provider=provider.name,
                        operation=operation,
                        attempt=attempt,
                        chain_index=chain_index,
                        elapsed_ms=elapsed_ms,
                        **subject,
                    ))
                    self._cache.set(
                        key, _CachedProviderValue(value, provider=reported_provider)
                    )
                    return MarketDataResult(
                        value, self._metadata(provider=reported_provider, cached=False)
                    )
            if chain_index == 0 and len(self._chain) > 1 and last_error is not None:
                # Explicit fallback attribution: names both providers, the
                # attempt budget spent, and the classified failure (including an
                # HTTP 429) so the durable log answers the attribution question
                # without needing tracebacks.  The gating condition is unchanged.
                logger.error(_event(
                    "market_data.provider_failed_using_fallback",
                    provider=provider.name,
                    failed_provider=provider.name,
                    fallback=self._chain[1].name,
                    fallback_provider=self._chain[1].name,
                    operation=operation,
                    attempts=2 if len(self._chain) > 1 else 1,
                    chain_index=chain_index,
                    **subject,
                    **classify_error(primary_error if primary_error is not None else last_error),
                ))

        logger.error(_event(
            "market_data.all_providers_failed",
            operation=operation,
            chain=[provider.name for provider in self._chain],
            **subject,
            **classify_error(last_error),
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

    @property
    def supports_bulk_market_quotes(self) -> bool:
        """Whether any provider in the chain overrides the optional bulk capability.

        Checked before calling so a provider without the capability produces an
        explicit ``provider_unsupported`` signal instead of a generic failure.
        """
        return any(
            type(provider).get_bulk_market_quotes
            is not MarketDataProvider.get_bulk_market_quotes
            for provider in self._chain
        )

    def get_bulk_market_quotes(
        self, instrument_keys: Sequence[str]
    ) -> MarketDataResult:
        """Bulk live snapshots for a whole instrument universe (MD-10).

        Routed through the normal provider chain, so a provider without the
        optional capability raises ``NotImplementedError`` here and the caller
        keeps its existing per-instrument behavior.  The cache key carries a
        digest of the requested keys because the same broad-market run always
        asks for the same universe; this deliberately stays on the existing
        short-TTL in-memory cache rather than adding a snapshot store.
        """
        keys = [str(key).strip() for key in instrument_keys if str(key).strip()]
        if not keys:
            raise ValueError("instrument_keys must not be empty")
        if not self.supports_bulk_market_quotes:
            raise NotImplementedError(
                "no configured market-data provider supports bulk market quotes"
            )
        digest = hashlib.sha1("|".join(keys).encode("utf-8")).hexdigest()[:16]
        return self._read(
            f"bulk_quotes:{len(keys)}:{digest}",
            "get_bulk_market_quotes",
            keys,
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
            "rateLimitWaits": self._rate_limit_waits,
            "rateLimitRetrySkips": self._rate_limit_skips,
            "lastRateLimitAt": self._last_rate_limit_at,
        }


def _cache_ttl_from_environment() -> float:
    try:
        return max(0, float(os.environ.get("MARKET_DATA_CACHE_TTL_SECONDS", "30")))
    except ValueError:
        logger.warning(_event("market_data.invalid_cache_ttl_using_default"))
        return 30


def _skips_remaining_attempt(
    exc: Exception,
    waited: float | None,
    max_retry_after_seconds: float,
) -> bool:
    """Whether a throttled read should abandon its remaining attempt.

    A rate limit only earns an immediate retry when a short advisory wait was
    actually honored.  Otherwise the provider has explicitly asked us to back
    off, so re-issuing the request instantly would be a guaranteed-futile call
    that deepens the penalty.  Non-rate-limit errors return ``False``, which
    preserves the original immediate-retry behavior.
    """
    if not isinstance(exc, ProviderRateLimitedError):
        return False
    return waited is None or waited > max_retry_after_seconds


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
