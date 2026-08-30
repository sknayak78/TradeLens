"""End-to-end tests for chart-series building across multi-timeframe plans."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from services.chart_series import build_chart_series, EMA_PERIODS
from services.market_data.models import OHLCVBar
from services.market_data_service import MarketDataService

IST = ZoneInfo("Asia/Kolkata")


class _FakeNormalized:
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self._bars = bars

    def get_historical_ohlcv(self, symbol, *, period, interval) -> list[OHLCVBar]:
        return self._bars


class _FakePrimary:
    name = "fake"

    def __init__(self, bars: list[OHLCVBar]) -> None:
        self._normalized = _FakeNormalized(bars)


class _FakeFallback:
    name = "fake"


def _generate_daily(window_years: int = 5) -> list[OHLCVBar]:
    """Realistic non-degenerate OHLC bars, one per trading day, trending up."""
    bars: list[OHLCVBar] = []
    start = datetime(2026, 8, 27, 9, 15, tzinfo=IST)
    for i in range(int(window_years * 252)):
        ts = start - timedelta(days=i * 1.4)
        base = 1500 + i * 0.5
        open_ = base
        close = base + 4
        high = max(open_, close) + 6
        low = min(open_, close) - 5
        bars.append(
            OHLCVBar(
                timestamp=ts,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=1_000_000,
            )
        )
    return bars


def _service(bars: list[OHLCVBar]) -> MarketDataService:
    return MarketDataService(_FakePrimary(bars), _FakeFallback())


def _assert_candle_shaped(points) -> None:
    assert points
    for point in points:
        assert isinstance(point["o"], (int, float))
        assert isinstance(point["h"], (int, float))
        assert isinstance(point["l"], (int, float))
        assert point["h"] >= max(point["o"], point["v"])
        assert point["l"] <= min(point["o"], point["v"])


@pytest.mark.parametrize("timeframe", ["1M", "3M", "1Y"])
def test_build_chart_series_produces_candles_for_every_timeframe(timeframe):
    service = _service(_generate_daily(window_years=5))
    series, label, used_fallback, indicators = build_chart_series(
        service, "EICHERMOT.NS", timeframe
    )
    assert used_fallback is False
    assert not label == "Recent"
    assert len(series) > 0
    _assert_candle_shaped(series)
    assert indicators is not None
    assert set(indicators.keys()) == {f"ema{p}" for p in EMA_PERIODS}
    # 5 years of daily lookback supports every EMA.
    assert all(indicators.values())
    # Every visible point carries aligned EMA columns.
    for point in series:
        for p in EMA_PERIODS:
            assert f"ema{p}" in point


def test_1y_collapses_daily_bars_into_weekly_candles():
    service = _service(_generate_daily(window_years=5))
    series_1y, _, _, _ = build_chart_series(service, "EICHERMOT.NS", "1Y")
    series_3m, _, _, _ = build_chart_series(service, "EICHERMOT.NS", "3M")
    # 1Y is weekly-aggregated: far fewer candles than 3M (which is daily and
    # capped at ~66), yet still spans a full year of market data.
    assert len(series_1y) < len(series_3m)
    assert 30 <= len(series_1y) <= 70


def test_ema200_not_reported_when_lookback_is_short():
    # Only ~100 daily bars (well under the EMA200 period) are available, so the
    # 3M view cannot support EMA200 -> explicitly not meaningful.
    bars = _generate_daily(window_years=1)[-100:]
    service = _service(bars)
    _, _, _, indicators = build_chart_series(service, "EICHERMOT.NS", "3M")
    assert indicators["ema20"] is True
    assert indicators["ema50"] is True
    assert indicators["ema200"] is False


def test_series_are_aligned_and_one_point_per_candle():
    service = _service(_generate_daily(window_years=5))
    series, _, _, _ = build_chart_series(service, "EICHERMOT.NS", "1M")
    assert len(series) <= 22  # 1M plan caps the visible window
    for point in series:
        assert point["t"]
        assert isinstance(point["v"], (int, float))
