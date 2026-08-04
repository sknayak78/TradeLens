"""Regression tests for non-finite (NaN/inf) values in Yahoo history.

The bar for an in-progress session is published with `Close` unset, so the
newest row is a placeholder.  Reading it as a quote produced `price: nan` and
NaN EMA/RSI values, which FastAPI rejected with
"Out of range float values are not JSON compliant: nan".
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from services.providers.seed_provider import SeedProvider
from services.providers.yahoo_finance_provider import YahooFinanceProvider


def _history(close_tail: float | None) -> pd.DataFrame:
    """20 complete daily bars, optionally followed by an unfinished one."""
    closes = [100.0 + i for i in range(20)]
    highs = [101.0 + i for i in range(20)]
    lows = [99.0 + i for i in range(20)]
    volumes = [1000 + i for i in range(20)]
    if close_tail is None:
        closes.append(float("nan"))
        highs.append(float("nan"))
        lows.append(float("nan"))
        volumes.append(5000)
    else:
        closes.append(close_tail)
        highs.append(close_tail + 1)
        lows.append(close_tail - 1)
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


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> YahooFinanceProvider:
    """A provider whose Yahoo history ends in an unfinished bar."""
    # Patched on the class so the static `_quote` helper sees it too.
    monkeypatch.setattr(
        YahooFinanceProvider,
        "_history",
        staticmethod(lambda symbol, period="2d", interval="1d": _history(None)),
    )
    return YahooFinanceProvider(SeedProvider())


def test_unfinished_bar_does_not_poison_the_quote(provider) -> None:
    stock = provider.get_stock("RELIANCE")

    assert stock is not None
    for field in ("price", "changePct", "rsi", "ema20", "ema50", "ema200",
                  "support", "resistance"):
        assert math.isfinite(stock[field]), field
    # The last complete bar (close 119.0) is quoted, not the placeholder.
    assert stock["price"] == 119.0
    # Support/resistance skip the placeholder row too.
    assert stock["support"] == 99.0
    assert stock["resistance"] == 120.0


def test_unfinished_bar_is_excluded_from_the_insight_series(provider) -> None:
    insight = provider.get_stock_insight("RELIANCE")

    assert all(math.isfinite(point["v"]) for point in insight["series"])
    assert insight["series"][-1]["v"] == 119.0
    assert math.isfinite(insight["support"])
    assert "nan" not in insight["aiInsight"]


def test_recommendation_survives_an_unfinished_bar(provider) -> None:
    """End-to-end guard: the endpoint payload must be JSON compliant."""
    import json

    import routers.market as market_router
    from services.market_data_service import MarketDataService

    service = MarketDataService(
        primary_provider=provider, fallback_provider=SeedProvider()
    )
    original = market_router.market_data_service
    market_router.market_data_service = service
    try:
        payload = market_router.stock_detail("RELIANCE").model_dump()
    finally:
        market_router.market_data_service = original

    # allow_nan=False raises exactly the ValueError the live API reported.
    assert json.loads(json.dumps(payload, allow_nan=False, default=str))
    assert payload["recommendation"] is not None


def test_all_bars_unfinished_falls_back_to_seed_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty = pd.DataFrame(
        {"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [float("nan")],
         "Volume": [1]},
        index=pd.date_range("2024-01-01", periods=1, freq="D"),
    )
    monkeypatch.setattr(
        YahooFinanceProvider,
        "_history",
        staticmethod(lambda symbol, period="2d", interval="1d": empty),
    )

    stock = YahooFinanceProvider(SeedProvider()).get_stock("RELIANCE")

    assert stock is not None
    assert math.isfinite(stock["price"])
    assert stock["rsi"] == 62.4  # untouched seed value


def test_non_finite_indicator_is_rejected_rather_than_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        YahooFinanceProvider,
        "_history",
        staticmethod(lambda symbol, period="2d", interval="1d": _history(120.0)),
    )
    monkeypatch.setattr(
        YahooFinanceProvider,
        "_finite",
        staticmethod(lambda value, label: (_ for _ in ()).throw(
            RuntimeError(f"non-finite {label}")
        )),
    )

    stock = YahooFinanceProvider(SeedProvider()).get_stock("RELIANCE")

    # Seed values survive; no NaN is published.
    assert stock is not None
    assert stock["rsi"] == 62.4
