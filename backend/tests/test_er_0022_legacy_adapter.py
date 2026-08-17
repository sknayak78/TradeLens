"""ER-0022 legacy adapter compatibility tests."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from seed_data import DEFAULT_WATCHLIST_SYMBOLS, INSIGHTS, MARKET_INDICES, OPPORTUNITIES, STOCKS, TODAYS_FOCUS
from services.market_data.legacy_adapter import LegacyCatalogueSupport, LegacyProviderAdapter
from services.market_data.models import Instrument, StockInsight, StockSnapshot
from services.market_data.normalized_provider import NormalizedMarketDataProvider
from services.market_data.snapshot_builder import SCREENING_REQUIRED_FIELDS
from services.providers.mock_provider import MockMarketDataProvider
from services.providers.seed_provider import SeedProvider


def _seed_mock_provider() -> MockMarketDataProvider:
    return MockMarketDataProvider.from_legacy_rows(
        STOCKS,
        INSIGHTS,
        market_summary={"indices": deepcopy(MARKET_INDICES), "todaysFocus": deepcopy(TODAYS_FOCUS)},
        opportunities=deepcopy(OPPORTUNITIES),
        watchlist_symbols=list(DEFAULT_WATCHLIST_SYMBOLS),
    )


class _CatalogueOnlyProvider(NormalizedMarketDataProvider, LegacyCatalogueSupport):
    """Fixture provider without batch catalogue support for adapter fallback tests."""

    name = "catalogue-only"

    def __init__(
        self,
        *,
        instruments: Sequence[Instrument],
        snapshots: dict[str, StockSnapshot],
        insights: dict[str, StockInsight],
    ):
        self._instruments = tuple(instruments)
        self._snapshots = snapshots
        self._insights = insights

    def get_instruments(self) -> Sequence[Instrument]:
        return self._instruments

    def get_quote(self, symbol: str):
        snapshot = self._snapshots.get(symbol.strip().upper())
        if snapshot is None:
            return None
        from services.market_data.models import Quote

        return Quote(
            symbol=snapshot.symbol,
            price=snapshot.price,
            change_pct=snapshot.change_pct,
            volume=snapshot.volume,
        )

    def get_historical_ohlcv(self, symbol: str, *, period: str = "2y", interval: str = "1d"):
        raise NotImplementedError

    def get_market_status(self):
        from datetime import datetime, timezone

        from services.market_data.models import MarketStatus

        return MarketStatus(status="OPEN", as_of=datetime.now(timezone.utc))

    def freshness(self):
        from datetime import datetime, timezone

        from services.market_data.models import DataFreshness

        return DataFreshness(
            provider=self.name,
            observed_at=datetime.now(timezone.utc),
            latency_class="instant",
        )

    def latency_class(self):
        return "instant"

    def stock_snapshot(self, symbol: str) -> StockSnapshot | None:
        return self._snapshots.get(symbol.strip().upper())

    def stock_insight(self, symbol: str) -> StockInsight | None:
        return self._insights.get(symbol.strip().upper())

    def market_summary(self) -> dict[str, Any]:
        return {"indices": [], "todaysFocus": []}

    def opportunity_contexts(self):
        return ()

    def watchlist_symbols(self):
        return [instrument.symbol for instrument in self._instruments]


def test_legacy_adapter_exposes_seed_parity_for_stock_and_insight() -> None:
    seed = SeedProvider()
    mock = _seed_mock_provider()
    adapter = LegacyProviderAdapter(mock)

    seed_stock = seed.get_stock("RELIANCE")
    adapted_stock = adapter.get_stock("RELIANCE")
    assert seed_stock is not None and adapted_stock is not None
    for field in SCREENING_REQUIRED_FIELDS:
        assert adapted_stock[field] == seed_stock[field]

    seed_insight = seed.get_stock_insight("RELIANCE")
    adapted_insight = adapter.get_stock_insight("RELIANCE")
    assert adapted_insight["support"] == seed_insight["support"]
    assert adapted_insight["resistance"] == seed_insight["resistance"]
    assert adapted_insight["aiInsight"] == seed_insight["aiInsight"]


def test_legacy_adapter_search_and_catalogue_methods() -> None:
    seed = SeedProvider()
    adapter = LegacyProviderAdapter(_seed_mock_provider())

    seed_matches = seed.search_stocks("ADAN", limit=5)
    adapted_matches = adapter.search_stocks("ADAN", limit=5)
    assert [row["symbol"] for row in adapted_matches] == [row["symbol"] for row in seed_matches]

    assert len(adapter.get_all_stocks()) == len(seed.get_all_stocks())
    assert adapter.get_default_watchlist_symbols() == seed.get_default_watchlist_symbols()
    assert adapter.get_opportunities() == seed.get_opportunities()


def test_legacy_adapter_market_summary_shape() -> None:
    seed = SeedProvider()
    adapter = LegacyProviderAdapter(_seed_mock_provider())
    adapted = adapter.get_market_summary()
    seed_summary = seed.get_market_summary()
    assert len(adapted["indices"]) == len(seed_summary["indices"])
    assert len(adapted["todaysFocus"]) == len(seed_summary["todaysFocus"])


def test_legacy_adapter_get_all_stocks_uses_batch_support() -> None:
    adapter = LegacyProviderAdapter(_seed_mock_provider())

    def forbidden_get_stock(symbol: str):
        raise AssertionError("get_stock must not be called when batch catalogue exists")

    adapter.get_stock = forbidden_get_stock  # type: ignore[method-assign]
    stocks = adapter.get_all_stocks()
    assert len(stocks) == len(STOCKS)


def test_legacy_adapter_search_stocks_uses_batch_support() -> None:
    adapter = LegacyProviderAdapter(_seed_mock_provider())

    def forbidden_get_stock(symbol: str):
        raise AssertionError("get_stock must not be called when batch catalogue exists")

    adapter.get_stock = forbidden_get_stock  # type: ignore[method-assign]
    matches = adapter.search_stocks("ADAN", limit=5)
    assert matches


def test_legacy_adapter_fallback_without_batch_support() -> None:
    snapshot = StockSnapshot(
        symbol="RELIANCE",
        name="Reliance Industries",
        price=2934.55,
        change_pct=1.24,
        rsi=62.4,
        ema20=2891.32,
        vwap=2918.75,
        volume=4_820_000,
        trend="bullish",
        day_high=2940.0,
        avg_volume=4_097_000,
        sector="Energy",
    )
    provider = _CatalogueOnlyProvider(
        instruments=[Instrument(symbol="RELIANCE", name="Reliance", sector="Energy")],
        snapshots={"RELIANCE": snapshot},
        insights={
            "RELIANCE": StockInsight(
                symbol="RELIANCE",
                support=2890.0,
                resistance=2985.0,
                ai_insight="test",
                series=(),
            )
        },
    )
    adapter = LegacyProviderAdapter(provider)
    stock = adapter.get_stock("RELIANCE")
    assert stock is not None
    assert stock["symbol"] == "RELIANCE"
    assert len(adapter.get_all_stocks()) == 1
    assert adapter.search_stocks("REL", limit=5)[0]["symbol"] == "RELIANCE"


def test_indicator_barrel_reexports_underlying_functions() -> None:
    from indicators.ema import calculate_latest_ema as legacy_ema
    from services.market_data.indicators import calculate_latest_ema as barrel_ema

    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert barrel_ema(values, 3) == legacy_ema(values, 3)
