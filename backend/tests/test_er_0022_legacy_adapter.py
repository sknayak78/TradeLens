"""ER-0022 legacy adapter compatibility tests."""
from __future__ import annotations

from copy import deepcopy

from seed_data import DEFAULT_WATCHLIST_SYMBOLS, INSIGHTS, MARKET_INDICES, OPPORTUNITIES, STOCKS, TODAYS_FOCUS
from services.market_data.legacy_adapter import LegacyProviderAdapter
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


def test_indicator_barrel_reexports_underlying_functions() -> None:
    from indicators.ema import calculate_latest_ema as legacy_ema
    from services.market_data.indicators import calculate_latest_ema as barrel_ema

    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert barrel_ema(values, 3) == legacy_ema(values, 3)
