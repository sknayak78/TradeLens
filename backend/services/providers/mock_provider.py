"""Deterministic normalized provider for ER-0022 tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from services.market_data.legacy_adapter import LegacyCatalogueSupport
from services.market_data.models import (
    DataFreshness,
    Instrument,
    LatencyClass,
    MarketStatus,
    OHLCVBar,
    OpportunityContext,
    Quote,
    StockInsight,
    StockSnapshot,
    ohlcv_bars_from_insight_series,
    quote_from_snapshot,
)
from services.market_data.normalized_provider import NormalizedMarketDataProvider


class MockMarketDataProvider(NormalizedMarketDataProvider, LegacyCatalogueSupport):
    """Fixture-driven normalized provider with no network or seed_data dependency."""

    name = "mock"

    def __init__(
        self,
        *,
        instruments: Sequence[Instrument] | None = None,
        snapshots: Mapping[str, StockSnapshot] | None = None,
        insights: Mapping[str, StockInsight] | None = None,
        ohlcv: Mapping[str, Sequence[OHLCVBar]] | None = None,
        market_summary: Mapping[str, Any] | None = None,
        opportunities: Sequence[OpportunityContext | Mapping[str, Any]] | None = None,
        watchlist_symbols: Sequence[str] | None = None,
        market_status: MarketStatus | None = None,
        freshness: DataFreshness | None = None,
        latency_class: LatencyClass = "instant",
        quote_failures: Mapping[str, Exception] | None = None,
        ohlcv_failures: Mapping[str, Exception] | None = None,
        observed_at: datetime | None = None,
    ):
        self._instruments = tuple(instruments or ())
        self._snapshots = {
            symbol.strip().upper(): snapshot
            for symbol, snapshot in (snapshots or {}).items()
        }
        self._insights = {
            symbol.strip().upper(): insight
            for symbol, insight in (insights or {}).items()
        }
        self._ohlcv = {
            symbol.strip().upper(): tuple(bars)
            for symbol, bars in (ohlcv or {}).items()
        }
        self._market_summary = dict(
            market_summary
            or {"indices": [], "todaysFocus": []}
        )
        self._opportunities = tuple(opportunities or ())
        self._watchlist_symbols = tuple(
            watchlist_symbols
            or [instrument.symbol for instrument in self._instruments]
        )
        when = observed_at or datetime(2026, 1, 15, 9, 30, tzinfo=timezone.utc)
        self._market_status = market_status or MarketStatus(status="OPEN", as_of=when)
        self._freshness = freshness or DataFreshness(
            provider=self.name,
            observed_at=when,
            latency_class=latency_class,
            stale=False,
        )
        self._latency_class = latency_class
        self._quote_failures = dict(quote_failures or {})
        self._ohlcv_failures = dict(ohlcv_failures or {})

    def get_instruments(self) -> Sequence[Instrument]:
        return self._instruments

    def get_quote(self, symbol: str) -> Quote | None:
        normalized = symbol.strip().upper()
        failure = self._quote_failures.get(normalized)
        if failure is not None:
            raise failure
        snapshot = self._snapshots.get(normalized)
        if snapshot is None:
            return None
        return quote_from_snapshot(snapshot, observed_at=self._freshness.observed_at)

    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> Sequence[OHLCVBar]:
        normalized = symbol.strip().upper()
        failure = self._ohlcv_failures.get(normalized)
        if failure is not None:
            raise failure
        if normalized in self._ohlcv:
            return self._ohlcv[normalized]
        insight = self._insights.get(normalized)
        if insight is not None and insight.series:
            return ohlcv_bars_from_insight_series(
                normalized,
                insight.series,
                base_date=self._freshness.observed_at,
            )
        snapshot = self._snapshots.get(normalized)
        if snapshot is None:
            raise RuntimeError(f"no OHLCV fixture for {normalized}")
        close = snapshot.price
        return (
            OHLCVBar(
                timestamp=self._freshness.observed_at,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=float(snapshot.volume),
            ),
        )

    def get_market_status(self) -> MarketStatus:
        return self._market_status

    def freshness(self) -> DataFreshness:
        return self._freshness

    def latency_class(self) -> LatencyClass:
        return self._latency_class

    # Legacy catalogue support used by LegacyProviderAdapter in Phase 1A tests.

    def stock_snapshot(self, symbol: str) -> StockSnapshot | None:
        return self._snapshots.get(symbol.strip().upper())

    def stock_insight(self, symbol: str) -> StockInsight | None:
        return self._insights.get(symbol.strip().upper())

    def market_summary(self) -> dict[str, Any]:
        return deepcopy(self._market_summary)

    def opportunity_contexts(self) -> Sequence[OpportunityContext | Mapping[str, Any]]:
        return self._opportunities

    def watchlist_symbols(self) -> Sequence[str]:
        return self._watchlist_symbols

    def inject_quote_failure(self, symbol: str, error: Exception) -> None:
        self._quote_failures[symbol.strip().upper()] = error

    def inject_ohlcv_failure(self, symbol: str, error: Exception) -> None:
        self._ohlcv_failures[symbol.strip().upper()] = error

    @staticmethod
    def from_legacy_rows(
        stock_rows: Sequence[Mapping[str, Any]],
        insight_rows: Mapping[str, Mapping[str, Any]] | None = None,
        *,
        market_summary: Mapping[str, Any] | None = None,
        opportunities: Sequence[Mapping[str, Any]] | None = None,
        watchlist_symbols: Sequence[str] | None = None,
    ) -> "MockMarketDataProvider":
        """Build a mock provider from existing legacy dictionaries for parity tests."""
        snapshots: dict[str, StockSnapshot] = {}
        instruments: list[Instrument] = []
        insights: dict[str, StockInsight] = {}
        for row in stock_rows:
            symbol = str(row["symbol"]).strip().upper()
            instruments.append(
                Instrument(
                    symbol=symbol,
                    name=str(row["name"]),
                    sector=str(row.get("sector", "")),
                )
            )
            snapshots[symbol] = StockSnapshot(
                symbol=symbol,
                name=str(row["name"]),
                price=float(row["price"]),
                change_pct=float(row["changePct"]),
                rsi=float(row["rsi"]),
                ema20=float(row["ema20"]),
                vwap=float(row["vwap"]),
                volume=int(row["volume"]),
                trend=str(row["trend"]),
                day_high=float(row["day_high"]),
                avg_volume=int(row["avg_volume"]),
                sector=str(row.get("sector", "")),
                ema50=float(row["ema50"]) if row.get("ema50") is not None else None,
                ema200=float(row["ema200"]) if row.get("ema200") is not None else None,
                score=int(row["score"]) if row.get("score") is not None else None,
                support=float(row["support"]) if row.get("support") is not None else None,
                resistance=float(row["resistance"]) if row.get("resistance") is not None else None,
            )
        for symbol, payload in (insight_rows or {}).items():
            normalized = symbol.strip().upper()
            insights[normalized] = StockInsight(
                symbol=normalized,
                support=float(payload["support"]),
                resistance=float(payload["resistance"]),
                ai_insight=str(payload["aiInsight"]),
                series=tuple(dict(point) for point in payload.get("series", [])),
            )
        return MockMarketDataProvider(
            instruments=instruments,
            snapshots=snapshots,
            insights=insights,
            market_summary=market_summary,
            opportunities=opportunities,
            watchlist_symbols=watchlist_symbols,
        )
