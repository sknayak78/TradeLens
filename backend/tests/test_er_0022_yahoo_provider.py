"""ER-0022 Yahoo provider migration tests."""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd
import pytest

from services.market_data.models import MarketStatus
from services.market_data.normalized_provider import NormalizedMarketDataProvider
from services.market_data.session import market_session_status
from services.providers.seed_provider import SeedProvider
from services.providers.yahoo_finance_provider import (
    YahooFinanceProvider,
    YahooMarketDataProvider,
)


def _standard_history(rows: int = 20) -> pd.DataFrame:
  return pd.DataFrame(
    {
      "Open": [100.0 + i for i in range(rows)],
      "High": [101.0 + i for i in range(rows)],
      "Low": [99.0 + i for i in range(rows)],
      "Close": [100.5 + i for i in range(rows)],
      "Volume": [1000 + i for i in range(rows)],
    },
    index=pd.date_range("2024-01-01", periods=rows, freq="D"),
  )


def _unfinished_history(rows: int = 20) -> pd.DataFrame:
  closes = [100.0 + i for i in range(rows)]
  highs = [101.0 + i for i in range(rows)]
  lows = [99.0 + i for i in range(rows)]
  volumes = [1000 + i for i in range(rows)]
  closes.append(float("nan"))
  highs.append(float("nan"))
  lows.append(float("nan"))
  volumes.append(5000)
  return pd.DataFrame(
    {
      "Open": closes,
      "High": highs,
      "Low": lows,
      "Close": closes,
      "Volume": volumes,
    },
    index=pd.date_range("2024-01-01", periods=len(closes), freq="D"),
  )


def _attach_counting_history(
  yahoo: YahooFinanceProvider,
  monkeypatch: pytest.MonkeyPatch,
  history: pd.DataFrame,
) -> dict[str, int]:
  counter = {"count": 0}

  def fetch(symbol: str, period: str = "2y", interval: str = "1d"):
    counter["count"] += 1
    return history

  monkeypatch.setattr(yahoo, "_history", fetch)
  yahoo._history_call_counter = counter
  yahoo._normalized.clear_bundle_cache()
  return counter


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> YahooFinanceProvider:
  yahoo = YahooFinanceProvider(SeedProvider())
  _attach_counting_history(yahoo, monkeypatch, _standard_history())
  monkeypatch.setattr(yahoo, "_quote", lambda symbol: (3001.25, 1.5, 123456))
  return yahoo


def test_yahoo_normalized_provider_implements_abc(provider: YahooFinanceProvider) -> None:
  assert isinstance(provider._normalized, NormalizedMarketDataProvider)


def test_quote_conversion_from_mocked_history(provider: YahooFinanceProvider) -> None:
  quote = provider._normalized.get_quote("RELIANCE")
  assert quote is not None
  assert quote.price == 3001.25
  assert quote.change_pct == 1.5
  assert quote.volume == 123456


def test_ohlcv_conversion(provider: YahooFinanceProvider) -> None:
  bars = provider._normalized.get_historical_ohlcv("RELIANCE")
  assert len(bars) == 20
  assert bars[-1].close == 119.5


def test_indicator_derivation(provider: YahooFinanceProvider) -> None:
  stock = provider.get_stock("RELIANCE")
  assert stock is not None
  assert stock["ema20"] == 111.42
  assert stock["rsi"] == 100.0
  assert stock["vwap"] != SeedProvider().get_stock("RELIANCE")["vwap"]


def test_stock_snapshot_conversion(provider: YahooFinanceProvider) -> None:
  snapshot = provider._normalized.stock_snapshot("RELIANCE")
  assert snapshot is not None
  payload = snapshot.to_legacy_dict()
  assert payload["price"] == 3001.25
  assert payload["trend"] == SeedProvider().get_stock("RELIANCE")["trend"]


def test_stock_insight_conversion(provider: YahooFinanceProvider) -> None:
  insight = provider.get_stock_insight("RELIANCE")
  assert len(insight["series"]) == 13
  assert insight["series"][-1]["v"] == 119.5
  assert "3001.25" in insight["aiInsight"]


def test_bundle_cache_hit_on_second_read(provider: YahooFinanceProvider) -> None:
  provider.get_stock("RELIANCE")
  counter = provider._history_call_counter
  assert counter["count"] == 1
  provider.get_stock_insight("RELIANCE")
  assert counter["count"] == 1
  assert provider._normalized.bundle_cache_size() == 1


def test_stock_then_insight_share_one_history_fetch(provider: YahooFinanceProvider) -> None:
  counter = provider._history_call_counter
  provider.get_stock("RELIANCE")
  provider.get_stock_insight("RELIANCE")
  assert counter["count"] == 1


def test_insight_then_stock_share_one_history_fetch(provider: YahooFinanceProvider) -> None:
  counter = provider._history_call_counter
  provider.get_stock_insight("RELIANCE")
  provider.get_stock("RELIANCE")
  assert counter["count"] == 1


def test_bundle_cache_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
  now = [0.0]
  yahoo = YahooFinanceProvider(SeedProvider(), bundle_ttl_seconds=30, clock=lambda: now[0])
  counter = _attach_counting_history(yahoo, monkeypatch, _standard_history())
  monkeypatch.setattr(yahoo, "_quote", lambda symbol: (3001.25, 1.5, 123456))

  yahoo.get_stock("RELIANCE")
  assert counter["count"] == 1
  yahoo.get_stock_insight("RELIANCE")
  assert counter["count"] == 1

  now[0] = 31.0
  yahoo.get_stock("RELIANCE")
  assert counter["count"] == 2


def test_get_all_stocks_causes_zero_yahoo_calls(provider: YahooFinanceProvider) -> None:
  counter = provider._history_call_counter
  stocks = provider.get_all_stocks()
  assert len(stocks) == 40
  assert counter["count"] == 0


def test_search_stocks_causes_zero_yahoo_calls(provider: YahooFinanceProvider) -> None:
  counter = provider._history_call_counter
  matches = provider.search_stocks("ADAN", limit=5)
  assert matches
  assert counter["count"] == 0


def test_yahoo_failure_returns_seed_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
  yahoo = YahooFinanceProvider(SeedProvider())
  monkeypatch.setattr(
    yahoo,
    "_history",
    lambda symbol, period="2d", interval="1d": (_ for _ in ()).throw(RuntimeError("boom")),
  )
  stock = yahoo.get_stock("RELIANCE")
  seeded = SeedProvider().get_stock("RELIANCE")
  assert stock is not None
  assert stock["price"] == seeded["price"]
  assert stock["rsi"] == seeded["rsi"]


def test_empty_history_returns_seed_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
  yahoo = YahooFinanceProvider(SeedProvider())
  monkeypatch.setattr(yahoo, "_history", lambda symbol, period="2d", interval="1d": None)
  stock = yahoo.get_stock("RELIANCE")
  assert stock is not None
  assert stock["rsi"] == 62.4


def test_non_finite_values_return_seed_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
  yahoo = YahooFinanceProvider(SeedProvider())
  monkeypatch.setattr(yahoo, "_history", lambda symbol, period="2d", interval="1d": _standard_history())
  monkeypatch.setattr(
    YahooFinanceProvider,
    "_finite",
    staticmethod(lambda value, label: (_ for _ in ()).throw(RuntimeError(f"non-finite {label}"))),
  )
  stock = yahoo.get_stock("RELIANCE")
  assert stock is not None
  assert stock["rsi"] == 62.4


def test_incomplete_final_bar_is_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
  yahoo = YahooFinanceProvider(SeedProvider())
  monkeypatch.setattr(yahoo, "_history", lambda symbol, period="2d", interval="1d": _unfinished_history())
  stock = yahoo.get_stock("RELIANCE")
  assert stock is not None
  assert stock["price"] == 119.0
  insight = yahoo.get_stock_insight("RELIANCE")
  assert insight["series"][-1]["v"] == 119.0


def test_unknown_symbol_behavior_preserved() -> None:
  provider = YahooFinanceProvider(SeedProvider())
  assert provider.get_stock("NOTAREAL") is None
  insight = provider.get_stock_insight("NOTAREAL")
  assert "support" in insight


def test_latency_class_is_delayed(provider: YahooFinanceProvider) -> None:
  assert provider._normalized.latency_class() == "delayed"


def test_market_status_semantics_preserved() -> None:
  provider = YahooFinanceProvider(SeedProvider())
  status = provider._normalized.get_market_status()
  assert isinstance(status, MarketStatus)
  assert status.status == market_session_status(status.as_of)


def test_constructor_compatibility_seed_provider_argument() -> None:
  provider = YahooFinanceProvider(SeedProvider())
  assert provider.get_stock("RELIANCE") is not None


def test_repeated_reads_within_ttl_use_zero_additional_history_fetches(
  provider: YahooFinanceProvider,
) -> None:
  counter = provider._history_call_counter
  provider.get_stock("RELIANCE")
  provider.get_stock_insight("RELIANCE")
  provider.get_stock("RELIANCE")
  provider.get_stock_insight("RELIANCE")
  assert counter["count"] == 1


def test_performance_call_counts_report(provider: YahooFinanceProvider) -> None:
  counter = provider._history_call_counter
  provider._normalized.clear_bundle_cache()
  counter["count"] = 0

  provider.get_stock("RELIANCE")
  provider.get_stock_insight("RELIANCE")
  stock_then_insight = counter["count"]

  provider._normalized.clear_bundle_cache()
  counter["count"] = 0
  provider.get_stock_insight("TCS")
  provider.get_stock("TCS")
  insight_then_stock = counter["count"]

  provider._normalized.clear_bundle_cache()
  counter["count"] = 0
  provider.get_all_stocks()
  all_stocks_calls = counter["count"]

  provider._normalized.clear_bundle_cache()
  counter["count"] = 0
  provider.search_stocks("ADAN", limit=5)
  search_calls = counter["count"]

  provider._normalized.clear_bundle_cache()
  counter["count"] = 0
  provider.get_stock("INFY")
  provider.get_stock_insight("INFY")
  provider.get_stock("INFY")
  provider.get_stock_insight("INFY")
  repeated_within_ttl = counter["count"]

  assert stock_then_insight == 1
  assert insight_then_stock == 1
  assert all_stocks_calls == 0
  assert search_calls == 0
  assert repeated_within_ttl == 1
