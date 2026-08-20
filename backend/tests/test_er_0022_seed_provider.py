"""ER-0022 seed provider migration tests."""
from __future__ import annotations

import ast
import inspect
from copy import deepcopy
from pathlib import Path

import pytest

from seed_data import (
    DEFAULT_WATCHLIST_SYMBOLS,
    INSIGHTS,
    MARKET_INDICES,
    OPPORTUNITIES,
    STOCKS,
    TODAYS_FOCUS,
)
from services.market_data.models import Instrument
from services.market_data.normalized_provider import NormalizedMarketDataProvider
from services.market_data.snapshot_builder import SCREENING_REQUIRED_FIELDS
from services.market_data.universe import InstrumentUniverse
from services.providers.seed_provider import SeedMarketDataProvider, SeedProvider


def _legacy_seed_provider_outputs() -> dict[str, object]:
    """Reference outputs built directly from seed_data for parity checks."""
    from copy import deepcopy as dc

    from seed_data import STOCKS as LEGACY_STOCKS
    from seed_data import STOCKS_BY_SYMBOL, synthesize_insight

    return {
        "all_stocks": dc(LEGACY_STOCKS),
        "reliance": dc(STOCKS_BY_SYMBOL["RELIANCE"]),
        "reliance_insight": dc(INSIGHTS["RELIANCE"]),
        "search_adan": [
            stock
            for stock in LEGACY_STOCKS
            if "adan" in stock["symbol"].lower() or "adan" in stock["name"].lower()
        ][:5],
        "opportunities": dc(OPPORTUNITIES),
        "market_summary": {
            "indices": dc(MARKET_INDICES),
            "todaysFocus": dc(TODAYS_FOCUS),
        },
        "watchlist": list(DEFAULT_WATCHLIST_SYMBOLS),
        "synthetic_insight": dc(synthesize_insight("UNKNOWN")),
    }


def test_seed_provider_constructs_normally() -> None:
    provider = SeedProvider()
    assert provider.name == "seed"
    assert provider.get_stock("RELIANCE") is not None


def test_seed_market_data_provider_satisfies_normalized_contract() -> None:
    provider = SeedMarketDataProvider()
    assert isinstance(provider, NormalizedMarketDataProvider)


def test_get_instruments_returns_forty_stock_universe() -> None:
    provider = SeedMarketDataProvider()
    instruments = provider.get_instruments()
    assert len(instruments) == 40
    assert all(isinstance(item, Instrument) for item in instruments)


def test_get_quote_matches_expected_seed_row() -> None:
    provider = SeedMarketDataProvider()
    quote = provider.get_quote("RELIANCE")
    legacy = _legacy_seed_provider_outputs()["reliance"]
    assert quote is not None
    assert quote.symbol == "RELIANCE"
    assert quote.price == legacy["price"]
    assert quote.change_pct == legacy["changePct"]
    assert quote.volume == legacy["volume"]


def test_get_historical_ohlcv_is_deterministic() -> None:
    provider = SeedMarketDataProvider()
    first = provider.get_historical_ohlcv("RELIANCE")
    second = provider.get_historical_ohlcv("RELIANCE")
    assert len(first) == len(second) > 0
    assert [bar.close for bar in first] == [bar.close for bar in second]


def test_stock_snapshot_preserves_legacy_fields() -> None:
    provider = SeedMarketDataProvider()
    snapshot = provider.stock_snapshot("RELIANCE")
    legacy = _legacy_seed_provider_outputs()["reliance"]
    assert snapshot is not None
    payload = snapshot.to_legacy_dict()
    for field in SCREENING_REQUIRED_FIELDS:
        assert payload[field] == legacy[field]
    assert payload.get("ema50") == legacy.get("ema50")
    assert payload.get("ema200") == legacy.get("ema200")


def test_stock_insight_preserves_legacy_fields() -> None:
    provider = SeedMarketDataProvider()
    insight = provider.stock_insight("RELIANCE")
    legacy = _legacy_seed_provider_outputs()["reliance_insight"]
    assert insight is not None
    payload = insight.to_legacy_dict()
    assert payload["support"] == legacy["support"]
    assert payload["resistance"] == legacy["resistance"]
    assert payload["aiInsight"] == legacy["aiInsight"]
    assert payload["series"] == legacy["series"]


def test_all_stock_snapshots_returns_all_forty() -> None:
    provider = SeedMarketDataProvider()
    snapshots = provider.all_stock_snapshots()
    assert len(snapshots) == 40
    symbols = {snapshot.symbol for snapshot in snapshots}
    assert symbols == {stock["symbol"] for stock in STOCKS}


def test_all_stock_snapshots_does_not_hydrate_symbols_individually(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = SeedMarketDataProvider()

    def forbidden_stock_row(symbol: str):
        raise AssertionError("stock_row must not be called per symbol during batch read")

    monkeypatch.setattr(provider._universe, "stock_row", forbidden_stock_row)
    snapshots = provider.all_stock_snapshots()
    assert len(snapshots) == 40


def test_search_stock_snapshots_preserves_expected_search_behavior() -> None:
    provider = SeedMarketDataProvider()
    snapshots = provider.search_stock_snapshots("ADAN", limit=5)
    expected_symbols = [
        row["symbol"] for row in _legacy_seed_provider_outputs()["search_adan"]  # type: ignore[index]
    ]
    assert [snapshot.symbol for snapshot in snapshots] == expected_symbols


def test_get_all_stocks_equivalent_to_legacy_seed_provider() -> None:
    provider = SeedProvider()
    legacy_rows = _legacy_seed_provider_outputs()["all_stocks"]
    adapted_rows = provider.get_all_stocks()
    assert len(adapted_rows) == len(legacy_rows)  # type: ignore[arg-type]
    for adapted, legacy in zip(adapted_rows, legacy_rows):  # type: ignore[arg-type]
        for field in SCREENING_REQUIRED_FIELDS:
            assert adapted[field] == legacy[field]


def test_search_stocks_equivalent_to_legacy_seed_provider() -> None:
    provider = SeedProvider()
    adapted = provider.search_stocks("ADAN", limit=5)
    legacy = _legacy_seed_provider_outputs()["search_adan"]
    assert [row["symbol"] for row in adapted] == [row["symbol"] for row in legacy]  # type: ignore[index]


def test_get_opportunities_remains_compatible() -> None:
    provider = SeedProvider()
    assert provider.get_opportunities() == _legacy_seed_provider_outputs()["opportunities"]


def test_market_summary_remains_compatible() -> None:
    provider = SeedProvider()
    assert provider.get_market_summary() == _legacy_seed_provider_outputs()["market_summary"]


def test_default_watchlist_remains_compatible() -> None:
    provider = SeedProvider()
    assert provider.get_default_watchlist_symbols() == _legacy_seed_provider_outputs()["watchlist"]


def test_seed_provider_has_no_direct_seed_data_catalogue_imports() -> None:
    module_path = Path(inspect.getfile(SeedProvider)).resolve()
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "STOCKS",
        "STOCKS_BY_SYMBOL",
        "OPPORTUNITIES",
        "INSIGHTS",
        "MARKET_INDICES",
        "TODAYS_FOCUS",
        "DEFAULT_WATCHLIST_SYMBOLS",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "seed_data":
            imported.update(alias.name for alias in node.names)
    assert imported.isdisjoint(forbidden)


def test_seed_provider_accepts_explicit_universe() -> None:
    subset = deepcopy(STOCKS[:2])
    universe = InstrumentUniverse(stocks=subset)
    provider = SeedProvider(universe=universe)
    assert len(provider.get_all_stocks()) == 2
