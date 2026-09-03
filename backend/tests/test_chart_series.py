"""Unit tests for chart-series aggregation and EMA-over-lookback behaviour."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.chart_series import (
    EMA_PERIODS,
    aggregate_weekly,
    build_display_points,
    build_ema_overlay,
    compute_ema,
    _ema_availability,
)
from services.market_data.models import OHLCVBar

IST = ZoneInfo("Asia/Kolkata")


def test_ema_is_single_source_of_truth_in_indicators_module():
    # chart-series EMA must not carry its own algorithm; it must delegate to the
    # one authoritative implementation in indicators/ema.py and agree with it on
    # representative inputs (including warm-up and gap handling).
    import indicators.ema as indicators_ema

    for values, period in [
        ([10, 11, 12, 13], 3),
        ([10, 11, 12, 13], 20),
        ([], 20),
        ([10.0, 11.0, None, 12.0, 13.0], 3),
        ([100.0] * 230, 200),
    ]:
        assert compute_ema(values, period) == indicators_ema.calculate_ema_over_lookback(
            values, period
        )


def _week_number(bar: OHLCVBar) -> tuple[int, int]:
    local = bar.timestamp.astimezone(IST)
    week_start = local.date() - timedelta(days=local.date().weekday())
    return week_start.isocalendar()[:2]


def _bar(days_ago: int, day_since_midnight: int = 0) -> OHLCVBar:
    base = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    ts = base - timedelta(days=days_ago)
    value = 100.0 + day_since_midnight
    return OHLCVBar(
        timestamp=ts,
        open=value,
        high=value + 5,
        low=value - 5,
        close=value + 1,
        volume=100.0,
    )


def test_ema_emits_only_after_full_warmup():
    assert compute_ema([10, 11, 12, 13], 3) == [None, None, 11.0, 12.0]
    assert compute_ema([10, 11, 12, 13], 20) == [None, None, None, None]
    assert compute_ema([], 20) == []


def test_ema_availability_reflects_lookback_length():
    bars = [_bar(i) for i in range(25)]
    avail = _ema_availability(bars)
    assert avail["ema20"] is True
    assert avail["ema50"] is False
    assert avail["ema200"] is False

    long_bars = [_bar(i) for i in range(210)]
    long_avail = _ema_availability(long_bars)
    assert long_avail["ema50"] is True
    assert long_avail["ema200"] is True


def test_weekly_aggregation_uses_real_ohlc_only():
    bars = [_bar(i) for i in range(14)]
    weekly = aggregate_weekly(bars)
    # 14 consecutive daily bars starting 2026-08-01 -> spans multiple weeks.
    assert len(weekly) > 1
    for week in weekly:
        assert week.high >= week.open
        assert week.high >= week.close
        assert week.low <= week.open
        assert week.low <= week.close
        # Volume is the exact sum of the bars binned into this week.
        day_count = sum(1 for b in bars if _week_number(b) == _week_number(week))
        assert week.volume == 100.0 * day_count


def test_weekly_open_is_first_close_is_last_of_the_week():
    # Build three consecutive days in the same IST week starting Monday.
    monday = datetime(2026, 8, 3, 9, 15, tzinfo=IST)
    bars = [
        OHLCVBar(timestamp=monday, open=100, high=110, low=95, close=105, volume=1),
        OHLCVBar(
            timestamp=monday + timedelta(days=1),
            open=106,
            high=120,
            low=102,
            close=118,
            volume=2,
        ),
        OHLCVBar(
            timestamp=monday + timedelta(days=4),
            open=114,
            high=115,
            low=111,
            close=112,
            volume=7,
        ),
    ]
    weekly = aggregate_weekly(bars)
    assert len(weekly) == 1
    week = weekly[0]
    assert week.open == 100  # first bar of the week
    assert week.high == 120  # max high
    assert week.low == 95  # min low
    assert week.close == 112  # last close
    assert week.volume == 10  # sum


def test_clipped_series_attaches_ema_aligned_to_candles():
    bars = [_bar(i) for i in range(30)]
    points = build_display_points(bars, build_ema_overlay(bars), max_points=10)
    assert len(points) == 10
    assert all("ema20" in p and "ema50" in p and "ema200" in p for p in points)
    # Lookback of 30 >= 20 means EMA20 is warmed and present on the clipped view.
    assert any(p["ema20"] is not None for p in points)
    # 30 < 50 means EMA50/EMA200 are not meaningful -> null, not invented.
    assert all(p["ema50"] is None for p in points)
    assert all(p["ema200"] is None for p in points)


def test_clipped_ema_matches_hand_computation_on_last_point():
    bars = [_bar(i) for i in range(60)]
    points = build_display_points(bars, build_ema_overlay(bars), max_points=1)
    last = points[0]
    closes = [bar.close for bar in bars]
    expected = compute_ema(closes, 20)[-1]
    assert last["ema20"] == (None if expected is None else round(expected, 2))
    # EMA200 over 60 points is not meaningful -> null.
    assert last["ema200"] is None


def test_ema_periods_are_the_expected_triple():
    assert EMA_PERIODS == (20, 50, 200)


def test_intraday_ema_warmed_before_visible_window():
    # Simulate a 1D intraday plan: the raw lookback has several sessions of 5m
    # bars, but only the last `max_points` (one session) are shown. EMA20/EMA50
    # must already be non-null at the FIRST visible candle — no mid-session gap.
    sessions = 5
    bars_per_session = 78
    bars = []
    ts = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    for _ in range(sessions * bars_per_session):
        bars.append(
            OHLCVBar(
                timestamp=ts,
                open=100.0,
                high=104.0,
                low=98.0,
                close=101.0,
                volume=10.0,
            )
        )
        ts += timedelta(minutes=5)

    max_points = bars_per_session
    points = build_display_points(bars, build_ema_overlay(bars), max_points)
    assert len(points) == max_points
    # Over ~390 lookback bars, EMA20 and EMA50 are fully warmed before the
    # visible session begins, so the first visible candle has non-null values.
    assert points[0]["ema20"] is not None
    assert points[0]["ema50"] is not None
    # EMA200 needs 200 observations; with ~390 it is warmed by the visible tail,
    # though not necessarily at the very first visible candle.
    assert points[-1]["ema200"] is not None


def test_weekly_candle_samples_converged_daily_ema():
    # A 1Y-style plan: ~240 daily closes (well over 200) are aggregated weekly,
    # but the EMA200 overlay is computed on the daily closes and sampled at each
    # weekly anchor — so the last weekly candle carries the converged daily EMA200
    # value, not a weekly-recomputed under-converged value.
    daily = [_bar(i) for i in range(240)]
    weekly = aggregate_weekly(daily)
    overlay = build_ema_overlay(daily)
    points = build_display_points(weekly, overlay, max_points=60)
    last = points[-1]
    # The weekly candle's anchor is its last day, present in the daily overlay.
    expected = overlay[weekly[-1].timestamp]["ema200"]
    assert last["ema200"] == expected
    assert last["ema200"] is not None
    # And it should be close to a direct EMA200 over the daily closes.
    daily_ema = compute_ema([b.close for b in daily], 200)[-1]
    assert abs(last["ema200"] - round(daily_ema, 2)) < 1e-9
