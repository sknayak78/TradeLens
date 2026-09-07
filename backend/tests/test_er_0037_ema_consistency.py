"""Focused regression tests for EMA consistency (CandlestickChart vs Quick Snapshot).

Root cause regressed by these tests: Guided Research's Quick Snapshot EMA came
from the daily `stock` snapshot (a 2y/1d EMA, computed independently by the
Yahoo provider), while the chart's EMA came from the timeframe-specific
historical series (`build_chart_series`, warmed over the plan lookback). The two
paths drifted on intraday timeframes (1D/1W) by a large margin (e.g. EMA200).

The authoritative path is the timeline EMA computed by `build_chart_series`:
it uses the full continuous historical series for the selected timeframe's
candle interval, warmed well beyond the visible window. The Quick Snapshot now
sources its EMA20/50/200 from that same series' latest displayed candle.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import routers.learning as learning_router
from services.chart_series import (
    build_chart_series,
    build_display_points,
    build_ema_overlay,
    compute_ema,
)
from services.market_data.models import OHLCVBar
from services.market_data_service import MarketDataService

IST = ZoneInfo("Asia/Kolkata")

# Deliberately divergent "daily snapshot" EMA values the provider could return;
# they must never leak into the Quick Snapshot once EMA follows the chart series.
WRONG_DAILY_EMA = {"ema20": 999.0, "ema50": 998.0, "ema200": 997.0}


class _FakeNormalized:
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self._bars = bars

    def get_historical_ohlcv(self, symbol, *, period, interval) -> list[OHLCVBar]:
        return self._bars


class _FakePrimary:
    name = "fake"

    def __init__(self, bars, stock: dict, insight: dict) -> None:
        self._normalized = _FakeNormalized(bars)
        self._stock = stock
        self._insight = insight

    def get_historical_ohlcv(self, symbol, *, period, interval) -> list[OHLCVBar]:
        return self._normalized.get_historical_ohlcv(
            symbol, period=period, interval=interval
        )

    def get_stock(self, symbol: str) -> dict:
        return {**self._stock, "symbol": symbol}

    def get_stock_insight(self, symbol: str) -> dict:
        return {**self._insight, "symbol": symbol}


def _make_regime_bars(count: int, minutes_step: int = 30) -> list[OHLCVBar]:
    """Flat lead-in then a sharp rise, so a full-lookback EMA clearly differs from
    an EMA computed over only the final visible candles."""
    rise_len = 65
    flat_len = count - rise_len
    bars: list[OHLCVBar] = []
    ts = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    for i in range(count):
        if i < flat_len:
            close = 100.0
        else:
            close = 100.0 + (i - flat_len) * 0.5
        open_ = close - 0.3
        bars.append(
            OHLCVBar(
                timestamp=ts,
                open=open_,
                high=max(open_, close) + 0.4,
                low=min(open_, close) - 0.4,
                close=close,
                volume=1000_000,
            )
        )
        ts += timedelta(minutes=minutes_step)
    return bars


def _make_bars(count: int, minutes_step: int, base: float = 100.0) -> list[OHLCVBar]:
    """Continuous non-degenerate intraday bars trending gently upward."""
    bars: list[OHLCVBar] = []
    ts = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    for i in range(count):
        close = base + i * 0.01
        open_ = close - 0.5
        bars.append(
            OHLCVBar(
                timestamp=ts,
                open=open_,
                high=max(open_, close) + 0.6,
                low=min(open_, close) - 0.6,
                close=close,
                volume=1000_000,
            )
        )
        ts += timedelta(minutes=minutes_step)
    return bars


def _stock(price: float = 720.0) -> dict:
    return {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank",
        "price": price,
        "changePct": 0.5,
        "trend": "bullish",
        "sector": "Banking",
        "rsi": 55.0,
        "vwap": 715.0,
        "volume": 1_000_000,
        # The provider's independent daily snapshot EMAs — intentionally wrong to
        # prove the Quick Snapshot no longer trusts them.
        **WRONG_DAILY_EMA,
    }


def _insight() -> dict:
    return {"support": 707.0, "resistance": 753.2, "aiInsight": "", "series": []}


def _study(
    monkeypatch: pytest.MonkeyPatch,
    bars: list[OHLCVBar],
    timeframe: str = "1W",
    price: float = 720.0,
) -> dict:
    stock = _stock(price=price)
    primary = _FakePrimary(bars, stock, _insight())
    service = MarketDataService(primary, _FakePrimary(bars, stock, _insight()))
    monkeypatch.setattr(learning_router, "market_data_service", service)
    # Recommendation engine is out of scope for these EMA-consistency tests.
    monkeypatch.setattr(
        learning_router,
        "decide",
        lambda stock, insight: _StubDecision("bullish"),
    )
    return learning_router.learning_stock("HDFCBANK", timeframe=timeframe).model_dump()


class _StubDecision:
    def __init__(self, trend: str) -> None:
        self.trend = trend
        self.recommendation = None


@pytest.mark.parametrize("timeframe", ["1D", "1W", "1M", "3M", "1Y"])
def test_quick_snapshot_ema_matches_latest_chart_candle(monkeypatch, timeframe):
    """Requirement 1: Chart EMA and Quick Snapshot EMA share one authoritative value."""
    bars = _make_bars(1200, minutes_step=5)
    study = _study(monkeypatch, bars, timeframe=timeframe)

    series = study["series"]
    assert series, "expected a rendered chart series"
    last = series[-1]

    for period in (20, 50, 200):
        key = f"ema{period}"
        # The Quick Snapshot must equal the latest displayed chart candle.
        assert study[key] == last[key], f"snapshot {key} != chart {key}"
        # And it must be the chart-series value, never the divergent daily snapshot.
        assert study[key] != WRONG_DAILY_EMA[key]


def test_snapshot_ema_uses_full_lookback_not_just_visible_candles(monkeypatch):
    """Requirement 2: EMA20/50/200 are warmed over sufficient historical lookback.

    Build 600 bars but a 1W plan only *displays* the last 65. The study EMA must
    equal a full-600-bar EMA, and must differ from an EMA of just the 65 visible
    closes (proving it is not computed from the displayed candles alone).
    """
    bars = _make_regime_bars(600)
    study = _study(monkeypatch, bars, timeframe="1W")

    all_closes = [b.close for b in bars]
    visible_closes = all_closes[-65:]  # 1W plan max_points

    for period in (20, 50, 200):
        key = f"ema{period}"
        full_ema = compute_ema(all_closes, period)[-1]
        visible_ema = compute_ema(visible_closes, period)[-1]
        assert study[key] == round(full_ema, 2)
        # The EMA is NOT merely the visible-window EMA: either the visible window
        # cannot even support the period (None) or it yields a different value.
        assert visible_ema is None or study[key] != round(visible_ema, 2)


def test_visible_window_does_not_change_ema_for_a_given_candle():
    """Requirement 3: the EMA attached to a candle is stable across windows.

    The overlay is keyed by timestamp and computed over the full lookback, so the
    latest candle carries the same EMA no matter how many points are displayed.
    """
    bars = _make_bars(600, minutes_step=30)
    overlay = build_ema_overlay(bars)
    small = build_display_points(bars, overlay, max_points=10)
    large = build_display_points(bars, overlay, max_points=200)
    assert small[-1]["t"] == large[-1]["t"]
    for period in (20, 50, 200):
        key = f"ema{period}"
        assert small[-1][key] == large[-1][key]
        assert small[-1][key] == overlay[bars[-1].timestamp][key]


@pytest.mark.parametrize("timeframe,max_points", [("1D", 78), ("1W", 65)])
def test_intraday_ema_warmed_and_visible_window_capped(monkeypatch, timeframe, max_points):
    """Requirements 4 & 5: intraday (1D/1W) EMAs are warmed over the lookback and
    the visible candle window is preserved (no candlestick/aggregation regression)."""
    bars = _make_bars(1200, minutes_step=5 if timeframe == "1D" else 30)
    study = _study(monkeypatch, bars, timeframe=timeframe)

    series = study["series"]
    assert len(series) == max_points, "visible window must stay capped by the plan"
    all_closes = [b.close for b in bars]
    for period in (20, 50, 200):
        key = f"ema{period}"
        # Every EMA is available (sufficient intraday lookback) and equals the
        # full-series value, not a recompute over the 78/65 visible candles.
        assert study[key] is not None
        assert study[key] == round(compute_ema(all_closes, period)[-1], 2)


def test_chart_series_still_produces_candle_shaped_points_for_1d_and_1w(monkeypatch):
    """Requirement 5: 1D/1W chart behaviour (candle shape) does not regress."""
    bars = _make_bars(1200, minutes_step=5)
    primary = _FakePrimary(bars, _stock(), _insight())
    service = MarketDataService(primary, _FakePrimary(bars, _stock(), _insight()))
    for timeframe in ("1D", "1W"):
        series, label, used_fallback, indicators = build_chart_series(
            service, "HDFCBANK", timeframe
        )
        assert used_fallback is False
        assert series
        for point in series:
            assert point["h"] >= max(point["o"], point["v"])
            assert point["l"] <= min(point["o"], point["v"])
            for period in (20, 50, 200):
                assert f"ema{period}" in point
        assert indicators is not None
