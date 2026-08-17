"""ER-0022 normalized market-data model tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.market_data.models import (
    DataFreshness,
    Instrument,
    MarketStatus,
    OHLCVBar,
    Quote,
    StockInsight,
    StockSnapshot,
    ohlcv_bars_from_insight_series,
    quote_from_snapshot,
)
from services.market_data.normalized_provider import NormalizedMarketDataProvider
from services.providers.mock_provider import MockMarketDataProvider


def _snapshot() -> StockSnapshot:
    return StockSnapshot(
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


def test_quote_validates_positive_price() -> None:
    with pytest.raises(ValueError):
        Quote(symbol="RELIANCE", price=0.0, change_pct=1.0)


def test_ohlcv_bar_rejects_non_finite_values() -> None:
    when = datetime(2026, 1, 15, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        OHLCVBar(
            timestamp=when,
            open=1.0,
            high=2.0,
            low=1.0,
            close=float("nan"),
        )


def test_stock_snapshot_to_legacy_dict_preserves_screening_fields() -> None:
    payload = _snapshot().to_legacy_dict()
    assert payload["symbol"] == "RELIANCE"
    assert payload["day_high"] == 2940.0
    assert payload["avg_volume"] == 4_097_000


def test_stock_insight_to_legacy_dict_uses_existing_keys() -> None:
    insight = StockInsight(
        symbol="RELIANCE",
        support=2890.0,
        resistance=2985.0,
        ai_insight="test",
        series=({"t": "09:15", "v": 2905.2},),
    )
    payload = insight.to_legacy_dict()
    assert payload["aiInsight"] == "test"
    assert payload["series"][0]["v"] == 2905.2


def test_quote_from_snapshot_is_deterministic() -> None:
    snapshot = _snapshot()
    when = datetime(2026, 1, 15, tzinfo=timezone.utc)
    quote = quote_from_snapshot(snapshot, observed_at=when)
    assert quote.price == snapshot.price
    assert quote.volume == snapshot.volume
    assert quote.observed_at == when


def test_ohlcv_bars_from_insight_series() -> None:
    bars = ohlcv_bars_from_insight_series(
        "RELIANCE",
        [{"t": "09:15", "v": 100.0}, {"t": "09:45", "v": 101.0}],
    )
    assert len(bars) == 2
    assert bars[0].close == 100.0
    assert bars[1].close == 101.0


def test_mock_provider_satisfies_normalized_contract() -> None:
    provider = MockMarketDataProvider(
        instruments=[Instrument(symbol="RELIANCE", name="Reliance", sector="Energy")],
        snapshots={"RELIANCE": _snapshot()},
    )
    assert isinstance(provider, NormalizedMarketDataProvider)
    assert provider.get_quote("RELIANCE") is not None
    assert provider.latency_class() == "instant"
    assert provider.freshness().provider == "mock"


def test_intraday_is_explicitly_unsupported_by_default() -> None:
    provider = MockMarketDataProvider(
        instruments=[Instrument(symbol="RELIANCE", name="Reliance")],
        snapshots={"RELIANCE": _snapshot()},
    )
    with pytest.raises(NotImplementedError):
        provider.get_intraday_ohlcv("RELIANCE")


def test_market_status_and_freshness_models() -> None:
    when = datetime(2026, 1, 15, tzinfo=timezone.utc)
    status = MarketStatus(status="OPEN", as_of=when)
    freshness = DataFreshness(
        provider="mock",
        observed_at=when,
        latency_class="instant",
    )
    assert status.status == "OPEN"
    assert freshness.stale is False
