"""ER-0022 mock normalized provider tests."""
from __future__ import annotations

import pytest

from services.market_data.models import Instrument, OpportunityContext, StockInsight, StockSnapshot
from services.providers.mock_provider import MockMarketDataProvider


def _snapshot(symbol: str = "RELIANCE") -> StockSnapshot:
    return StockSnapshot(
        symbol=symbol,
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


def _provider() -> MockMarketDataProvider:
    return MockMarketDataProvider(
        instruments=[Instrument(symbol="RELIANCE", name="Reliance", sector="Energy")],
        snapshots={"RELIANCE": _snapshot()},
        insights={
            "RELIANCE": StockInsight(
                symbol="RELIANCE",
                support=2890.0,
                resistance=2985.0,
                ai_insight="test",
                series=({"t": "09:15", "v": 2905.2},),
            )
        },
        opportunities=[OpportunityContext(symbol="RELIANCE", score=88, reason="test")],
        watchlist_symbols=["RELIANCE"],
        market_summary={"indices": [{"symbol": "NIFTY"}], "todaysFocus": []},
    )


def test_mock_quote_is_deterministic() -> None:
    provider = _provider()
    first = provider.get_quote("RELIANCE")
    second = provider.get_quote("RELIANCE")
    assert first is not None and second is not None
    assert first.price == second.price == 2934.55


def test_mock_historical_ohlcv_from_insight_series() -> None:
    provider = _provider()
    bars = provider.get_historical_ohlcv("RELIANCE")
    assert len(bars) == 1
    assert bars[0].close == 2905.2


def test_mock_market_status_and_freshness() -> None:
    provider = _provider()
    assert provider.get_market_status().status == "OPEN"
    assert provider.freshness().provider == "mock"
    assert provider.latency_class() == "instant"


def test_mock_catalogue_helpers() -> None:
    provider = _provider()
    assert provider.stock_snapshot("RELIANCE") is not None
    assert provider.stock_insight("RELIANCE") is not None
    assert list(provider.watchlist_symbols()) == ["RELIANCE"]
    assert provider.market_summary()["indices"][0]["symbol"] == "NIFTY"


def test_mock_failure_injection() -> None:
    provider = _provider()
    provider.inject_quote_failure("RELIANCE", RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        provider.get_quote("RELIANCE")
