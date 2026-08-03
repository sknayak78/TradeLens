"""Unit tests for provider selection, cache behaviour, and safe fallback."""
from __future__ import annotations

from typing import Any

import pandas as pd

from services.cache import InMemoryTTLCache
from services.market_data_provider import MarketDataProvider
from services.market_data_service import MarketDataService
from services.providers.seed_provider import SeedProvider
from services.providers.yahoo_finance_provider import YahooFinanceProvider
from services.symbol_mapper import SymbolMapper


class StubProvider(MarketDataProvider):
    name = "stub"

    def __init__(self, value: dict[str, Any] | None = None, error: Exception | None = None):
        self.value = value or {"symbol": "RELIANCE", "price": 100.0}
        self.error = error
        self.stock_calls = 0

    def _result(self, value: Any) -> Any:
        if self.error:
            raise self.error
        return value

    def get_market_summary(self):
        return self._result({"indices": [], "todaysFocus": []})

    def get_stock(self, symbol: str):
        self.stock_calls += 1
        return self._result({**self.value, "symbol": symbol})

    def get_stock_insight(self, symbol: str):
        return self._result({"support": 1, "resistance": 2, "aiInsight": "test", "series": []})

    def search_stocks(self, query: str, limit: int = 20):
        return self._result([])

    def get_opportunities(self):
        return self._result([])

    def get_all_stocks(self):
        return self._result([])

    def get_default_watchlist_symbols(self):
        return self._result([])


def test_successful_yahoo_fetch_overlays_live_quote(monkeypatch):
    provider = YahooFinanceProvider(SeedProvider())
    monkeypatch.setattr(provider, "_quote", lambda symbol: (3001.25, 1.5, 123456))

    stock = provider.get_stock("RELIANCE")

    assert stock is not None
    assert stock["symbol"] == "RELIANCE"
    assert stock["price"] == 3001.25
    assert stock["changePct"] == 1.5
    assert stock["volume"] == 123456
    # Sprint 1 deliberately retains compatibility indicators.
    assert stock["rsi"] == 62.4


def test_cache_hit_avoids_second_provider_call():
    primary = StubProvider()
    service = MarketDataService(primary, StubProvider(), InMemoryTTLCache(ttl_seconds=30))

    assert service.get_stock("RELIANCE").data["price"] == 100.0
    assert service.get_stock("RELIANCE").data["price"] == 100.0

    assert primary.stock_calls == 1


def test_cache_expiry_fetches_provider_again():
    now = [0.0]
    primary = StubProvider()
    cache = InMemoryTTLCache(ttl_seconds=30, clock=lambda: now[0])
    service = MarketDataService(primary, StubProvider(), cache)

    service.get_stock("RELIANCE")
    now[0] = 30.0
    service.get_stock("RELIANCE")

    assert primary.stock_calls == 2


def test_provider_error_falls_back_without_breaking_call(caplog):
    primary = StubProvider(error=RuntimeError("Yahoo unavailable"))
    fallback = StubProvider(value={"symbol": "RELIANCE", "price": 99.0})
    service = MarketDataService(primary, fallback, InMemoryTTLCache(ttl_seconds=30))

    result = service.get_stock("RELIANCE")

    assert result.data["price"] == 99.0
    assert result.metadata.provider == "stub"
    assert primary.stock_calls == 1
    assert fallback.stock_calls == 1
    assert "market_data.provider_failed_using_fallback" in caplog.text


def test_stock_uses_live_ema_values_from_history(monkeypatch):
    provider = YahooFinanceProvider(SeedProvider())
    history = pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(20)],
            "High": [101.0 + i for i in range(20)],
            "Low": [99.0 + i for i in range(20)],
            "Close": [100.5 + i for i in range(20)],
            "Volume": [1000 + i for i in range(20)],
        },
        index=pd.date_range("2024-01-01", periods=20, freq="D"),
    )
    monkeypatch.setattr(provider, "_history", lambda symbol, period="2d", interval="1d": history)
    monkeypatch.setattr(provider, "_quote", lambda symbol: (3001.25, 1.5, 123456))

    stock = provider.get_stock("RELIANCE")

    assert stock is not None
    assert stock["ema20"] == 111.42
    assert stock["ema50"] == 106.46
    assert stock["ema200"] == 102.28
    assert stock["support"] == 99.0
    assert stock["resistance"] == 120.0
    assert stock["price"] == 3001.25


def test_stock_insight_uses_live_historical_close_series(monkeypatch):
    provider = YahooFinanceProvider(SeedProvider())
    history = pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(20)],
            "High": [101.0 + i for i in range(20)],
            "Low": [99.0 + i for i in range(20)],
            "Close": [100.5 + i for i in range(20)],
            "Volume": [1000 + i for i in range(20)],
        },
        index=pd.date_range("2024-01-01", periods=20, freq="D"),
    )
    monkeypatch.setattr(provider, "_history", lambda symbol, period="2d", interval="1d": history)

    insight = provider.get_stock_insight("RELIANCE")

    assert insight["support"] == 99.0
    assert insight["resistance"] == 120.0
    assert len(insight["series"]) == 13
    assert insight["series"][0]["v"] == 107.5
    assert insight["series"][-1]["v"] == 119.5


def test_symbol_mapper_uses_nse_suffix_and_explicit_aliases():
    mapper = SymbolMapper()

    assert mapper.to_yahoo("SBIN") == "SBIN.NS"
    assert mapper.to_yahoo("infy") == "INFY.NS"
    assert mapper.to_yahoo("M&M") == "M&M.NS"
