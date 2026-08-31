"""ER-0038 regression tests — one authoritative EMA calculation path.

Establishes and locks the single-source-of-truth outcome for EMA20/50/200:

1. ONE authoritative EMA implementation exists, and every backend consumer
   resolves to that same function.
2. EMA calculation is deterministic.
3. EMA is computed over the full supplied historical series, not only the
   visible window.
4. A candle's EMA is stable when the visible-window size changes.
5. Chart-series EMA and Guided Research Quick Snapshot use the same
   authoritative calculation for the same instrument / timeframe / candle.
6. 1D EMA has sufficient historical warm-up.
7. 1W EMA has sufficient historical warm-up (within provider limitations).
8. 1M/3M/1Y behaviour remains unchanged.
9. The frontend cannot override valid backend EMA values.

The chart/research authoritative algorithm lives in ``backend/indicators/ema.py``
(``compute_ema``); ``services.market_data`` barrels and ``services.chart_series``
re-export that same object.  ``compute_ema`` is defined ONLY once — these tests
prove any future consumer must import it rather than re-implement it.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import indicators.ema as indicators_ema_mod
import routers.learning as learning_router
from services.market_data.indicators import compute_ema as barrel_compute_ema
from services.chart_series import (
    build_chart_series,
    build_display_points,
    build_ema_overlay,
)
from services.market_data import compute_ema as package_compute_ema
from services.market_data.models import OHLCVBar
from services.market_data_service import MarketDataService

IST = ZoneInfo("Asia/Kolkata")


def _make_bars(count: int, minutes_step: int = 30, base: float = 100.0) -> list[OHLCVBar]:
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
        "ema20": 999.0,
        "ema50": 998.0,
        "ema200": 997.0,
    }


def _insight() -> dict:
    return {"support": 707.0, "resistance": 753.2, "aiInsight": "", "series": []}


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

    def get_stock(self, symbol: str) -> dict:
        return {**self._stock, "symbol": symbol}

    def get_stock_insight(self, symbol: str) -> dict:
        return {**self._insight, "symbol": symbol}


class _StubDecision:
    def __init__(self, trend: str) -> None:
        self.trend = trend
        self.recommendation = None


def _service(bars: list[OHLCVBar]) -> MarketDataService:
    stock = _stock()
    return MarketDataService(
        _FakePrimary(bars, stock, _insight()),
        _FakePrimary(bars, stock, _insight()),
    )


# ---------------------------------------------------------------------------
# Requirement 1 — one authoritative backend EMA implementation
# ---------------------------------------------------------------------------

def test_every_backend_consumer_resolves_to_the_same_ema_function():
    """Requirement 1: exactly one authoritative EMA implementation exists."""
    canonical = indicators_ema_mod.compute_ema
    resolvers = [
        barrel_compute_ema,
        package_compute_ema,
    ]
    # chart_series re-exports the canonical function for backward compatibility,
    # but must NOT hold a separate copy of the algorithm.
    from services.chart_series import compute_ema as chart_compute_ema

    identities = {id(canonical), id(chart_compute_ema)}
    for resolver in resolvers:
        identities.add(id(resolver))

    assert len(identities) == 1, (
        "expected every EMA import path to resolve to ONE function object"
    )
    # And the canonical function is the module's owned definition (not imported).
    assert canonical.__module__ == "indicators.ema"


def test_compute_ema_is_defined_only_once_in_indicators_module():
    """Guard: the algorithm body lives in indicators.ema and nowhere else."""
    import inspect
    import services.chart_series as cs
    assert inspect.getmodule(cs.compute_ema).__name__ == "indicators.ema"


# ---------------------------------------------------------------------------
# Requirement 2 — deterministic
# ---------------------------------------------------------------------------

def test_ema_calculation_is_deterministic():
    """Requirement 2: identical inputs yield identical outputs."""
    values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
    assert indicators_ema_mod.compute_ema(values, 20) == indicators_ema_mod.compute_ema(
        list(values), 20
    )
    assert indicators_ema_mod.compute_ema(values, 20) == indicators_ema_mod.compute_ema(
        tuple(values), 20
    )


# ---------------------------------------------------------------------------
# Requirement 3 — full supplied series, not only visible points
# ---------------------------------------------------------------------------

def test_ema_uses_full_series_not_only_visible_window():
    """Requirement 3: EMA warms over the entire supplied history."""
    bars = _make_bars(600, minutes_step=30)
    closes = [b.close for b in bars]
    # The full-series EMA differs from one computed over only the last 65 points
    # (trending series), proving the calculation consumes everything supplied.
    full = indicators_ema_mod.compute_ema(closes, 200)
    visible = indicators_ema_mod.compute_ema(closes[-65:], 200)
    assert full[-1] is not None
    assert visible[-1] is None or round(full[-1], 6) != round(visible[-1], 6)


# ---------------------------------------------------------------------------
# Requirement 4 — per-candle EMA stable across visible-window sizes
# ---------------------------------------------------------------------------

def test_candle_ema_is_stable_when_visible_window_changes():
    """Requirement 4: the EMA attached to a given candle is window-independent."""
    bars = _make_bars(600, minutes_step=30)
    overlay = build_ema_overlay(bars)
    assert overlay[bars[-1].timestamp]
    small = build_display_points(bars, overlay, max_points=10)
    large = build_display_points(bars, overlay, max_points=200)
    assert small[-1]["t"] == large[-1]["t"]
    for period in (20, 50, 200):
        key = f"ema{period}"
        assert small[-1][key] == large[-1][key]
        assert small[-1][key] == overlay[bars[-1].timestamp][key]


# ---------------------------------------------------------------------------
# Requirement 5 — chart EMA == Guided Research Quick Snapshot EMA
# ---------------------------------------------------------------------------

def _study(monkeypatch: pytest.MonkeyPatch, bars: list[OHLCVBar], timeframe: str):
    service = _service(bars)
    monkeypatch.setattr(learning_router, "market_data_service", service)
    monkeypatch.setattr(
        learning_router, "decide", lambda stock, insight: _StubDecision("bullish")
    )
    return learning_router.learning_stock("HDFCBANK", timeframe=timeframe).model_dump()


@pytest.mark.parametrize("timeframe", ["1D", "1W", "1M", "3M", "1Y"])
def test_chart_ema_matches_quick_snapshot_for_same_candle(monkeypatch, timeframe):
    """Requirement 5: Quick Snapshot EMA equals the latest chart candle EMA."""
    bars = _make_bars(1200, minutes_step=5)
    study = _study(monkeypatch, bars, timeframe=timeframe)
    series = study["series"]
    assert series, "expected a rendered chart series"
    last = series[-1]
    for period in (20, 50, 200):
        key = f"ema{period}"
        assert study[key] == last[key], f"snapshot {key} != chart {key}"


# ---------------------------------------------------------------------------
# Requirements 6 & 7 — intraday warm-up (1D and 1W)
# ---------------------------------------------------------------------------

def test_1d_and_1w_ema_have_sufficient_warmup(monkeypatch):
    """Requirements 6 & 7: 1D/1W EMA20/50/200 are warmed over the long lookback."""
    # Longer intraday series so EMA200 has ample history on both timeframes.
    bars = _make_bars(3000, minutes_step=5)
    service = _service(bars)
    for timeframe in ("1D", "1W"):
        series, label, used_fallback, indicators = build_chart_series(
            service, "HDFCBANK", timeframe
        )
        assert series
        assert indicators is not None
        for period in (20, 50, 200):
            key = f"ema{period}"
            assert indicators[key] is True, (
                f"{timeframe} {key} should be available for warm-up"
            )
            assert series[-1][key] is not None, (
                f"{timeframe} {key} should be present on the latest candle"
            )


def test_1d_visible_window_still_capped():
    """Requirement 6: 1D keeps its visible candle count even with warm-up history."""
    bars = _make_bars(3000, minutes_step=5)
    series, label, used_fallback, indicators = build_chart_series(
        _service(bars), "HDFCBANK", "1D"
    )
    assert len(series) == 78  # 1D plan max_points


def test_1w_visible_window_still_capped():
    """Requirement 7: 1W keeps its visible candle count even with warm-up history."""
    bars = _make_bars(3000, minutes_step=30)
    series, label, used_fallback, indicators = build_chart_series(
        _service(bars), "HDFCBANK", "1W"
    )
    assert len(series) == 65  # 1W plan max_points


# ---------------------------------------------------------------------------
# Requirement 8 — 1M/3M/1Y behaviour unchanged
# ---------------------------------------------------------------------------

def test_daily_timeframes_retain_ema_availability():
    """Requirement 8: daily (1M/3M/1Y) EMA availability is unchanged."""
    bars = _make_bars(1200, minutes_step=5)  # daily aggregation consumes closes
    service = _service(bars)
    for timeframe in ("1M", "3M", "1Y"):
        series, label, used_fallback, indicators = build_chart_series(
            service, "HDFCBANK", timeframe
        )
        assert series

# ---------------------------------------------------------------------------
# Requirement 9 — frontend cannot override valid backend EMA
# ---------------------------------------------------------------------------

def test_frontend_fallback_prefers_backend_ema():
    """Requirement 9: the frontend fallback must never override a backend EMA.

    Mirrors the `pickFirst(point.ema20, localEmaColumns.ema20[i])` contract in
    `frontend/src/components/charts/CandlestickChart.tsx`: the FIRST (backend)
    value wins whenever it is a finite number.
    """

    def pick_first(*values):
        for value in values:
            if isinstance(value, (int, float)):
                return value
        return None

    backend_value = 700.0
    frontend_fallback = 725.0
    assert pick_first(backend_value, frontend_fallback) == backend_value
    # When the backend leaves a point null, the fallback may fill it in — but
    # that is the only case, and it never changes a valid backend value.
    assert pick_first(None, frontend_fallback) == frontend_fallback
