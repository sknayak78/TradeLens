"""Provider exposing TradeLens' existing deterministic seed dataset."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from services.market_data.legacy_adapter import (
    LegacyBatchCatalogueSupport,
    LegacyCatalogueSupport,
    LegacyProviderAdapter,
)
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
from services.market_data.session import current_market_status
from services.market_data.snapshot_builder import (
    legacy_row_to_stock_insight,
    legacy_row_to_stock_snapshot,
)
from services.market_data.universe import InstrumentUniverse, default_universe
from services.market_data_provider import MarketDataProvider


class SeedMarketDataProvider(
    NormalizedMarketDataProvider,
    LegacyCatalogueSupport,
    LegacyBatchCatalogueSupport,
):
    """Normalized seed catalogue backed by InstrumentUniverse."""

    name = "seed"

    def __init__(self, universe: InstrumentUniverse | None = None):
        self._universe = universe or default_universe

    def get_instruments(self) -> Sequence[Instrument]:
        return self._universe.instruments()

    def get_quote(self, symbol: str) -> Quote | None:
        row = self._universe.stock_row(symbol)
        if row is None:
            return None
        snapshot = legacy_row_to_stock_snapshot(row)
        return quote_from_snapshot(snapshot, observed_at=self._observed_at())

    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> Sequence[OHLCVBar]:
        normalized = symbol.strip().upper()
        insight_row = self._universe.insight_row(normalized)
        series = insight_row.get("series", [])
        if series:
            return ohlcv_bars_from_insight_series(
                normalized,
                series,
                base_date=self._observed_at(),
            )
        row = self._universe.stock_row(normalized)
        if row is None:
            raise RuntimeError(f"no seed OHLCV for {normalized}")
        snapshot = legacy_row_to_stock_snapshot(row)
        close = snapshot.price
        when = self._observed_at()
        return (
            OHLCVBar(
                timestamp=when,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=float(snapshot.volume),
            ),
        )

    def get_market_status(self) -> MarketStatus:
        return current_market_status()

    def freshness(self) -> DataFreshness:
        when = self._observed_at()
        return DataFreshness(
            provider=self.name,
            observed_at=when,
            latency_class=self.latency_class(),
            stale=False,
        )

    def latency_class(self) -> LatencyClass:
        return "instant"

    def stock_snapshot(self, symbol: str) -> StockSnapshot | None:
        row = self._universe.stock_row(symbol)
        if row is None:
            return None
        return legacy_row_to_stock_snapshot(row)

    def stock_insight(self, symbol: str) -> StockInsight | None:
        normalized = symbol.strip().upper()
        insight_row = self._universe.insight_row(normalized)
        return legacy_row_to_stock_insight(insight_row, normalized)

    def all_stock_snapshots(self) -> Sequence[StockSnapshot]:
        return [
            legacy_row_to_stock_snapshot(row)
            for row in self._universe.all_stock_rows()
        ]

    def search_stock_snapshots(
        self,
        query: str,
        limit: int = 20,
    ) -> Sequence[StockSnapshot]:
        return [
            legacy_row_to_stock_snapshot(row)
            for row in self._universe.search_stock_rows(query, limit)
        ]

    def market_summary(self) -> dict[str, Any]:
        return self._universe.market_summary_seed()

    def opportunity_contexts(self) -> Sequence[OpportunityContext]:
        return self._universe.opportunities()

    def watchlist_symbols(self) -> Sequence[str]:
        return self._universe.watchlist_symbols()

    @staticmethod
    def _observed_at() -> datetime:
        return datetime.now(timezone.utc)


class SeedProvider(MarketDataProvider):
    """Canonical compatibility provider for the pre-existing mock dataset."""

    name = "seed"

    def __init__(self, universe: InstrumentUniverse | None = None):
        self._adapter = LegacyProviderAdapter(SeedMarketDataProvider(universe))

    def get_market_summary(self) -> dict[str, Any]:
        return self._adapter.get_market_summary()

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        return self._adapter.get_stock(symbol)

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        return self._adapter.get_stock_insight(symbol)

    def search_stocks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._adapter.search_stocks(query, limit)

    def get_opportunities(self) -> list[dict[str, Any]]:
        return self._adapter.get_opportunities()

    def get_all_stocks(self) -> list[dict[str, Any]]:
        return self._adapter.get_all_stocks()

    def get_default_watchlist_symbols(self) -> list[str]:
        return self._adapter.get_default_watchlist_symbols()
