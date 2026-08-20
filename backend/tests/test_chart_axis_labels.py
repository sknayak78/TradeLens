"""Tests for timeframe-specific chart axis label formatting."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.chart_axis_labels import (
    format_axis_tick_label,
    format_tooltip_label,
    series_timestamp,
)
from services.chart_series import bars_to_series
from services.market_data.models import OHLCVBar

IST = ZoneInfo("Asia/Kolkata")


def _bar(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    *,
    close: float = 100.0,
) -> OHLCVBar:
    return OHLCVBar(
        timestamp=datetime(year, month, day, hour, minute, tzinfo=IST),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1.0,
    )


def test_1d_axis_uses_ist_intraday_time():
    bar = _bar(2026, 8, 20, 9, 30)
    assert format_axis_tick_label("1D", bar.timestamp) == "09:30"


def test_1w_axis_uses_calendar_date_not_time():
    bar = _bar(2026, 8, 14, 15, 45)
    assert format_axis_tick_label("1W", bar.timestamp) == "14 Aug"


def test_1m_and_3m_axis_use_short_dates():
    bar = _bar(2026, 8, 19, 10, 0)
    assert format_axis_tick_label("1M", bar.timestamp) == "19 Aug"
    assert format_axis_tick_label("3M", bar.timestamp) == "19 Aug"


def test_1y_axis_uses_month_and_year():
    bar = _bar(2026, 3, 15, 10, 0)
    assert format_axis_tick_label("1Y", bar.timestamp) == "Mar 2026"


def test_series_timestamp_is_iso_in_ist():
    bar = _bar(2026, 8, 20, 9, 30)
    iso = series_timestamp(bar)
    parsed = datetime.fromisoformat(iso)
    assert parsed.tzinfo is not None
    assert parsed.astimezone(IST).hour == 9
    assert parsed.astimezone(IST).minute == 30


def test_bars_to_series_returns_iso_timestamps():
    bars = [
        _bar(2026, 8, 14, 10, 0, close=101.0),
        _bar(2026, 8, 15, 11, 30, close=102.0),
    ]
    series = bars_to_series(bars, max_points=10)
    assert len(series) == 2
    assert "T" in series[0]["t"]
    assert series[0]["v"] == 101.0


def test_utc_bar_is_converted_to_ist_for_1d_label():
    utc_bar = OHLCVBar(
        timestamp=datetime(2026, 8, 20, 4, 0, tzinfo=timezone.utc),
        open=100,
        high=100,
        low=100,
        close=100,
        volume=1.0,
    )
    assert format_axis_tick_label("1D", utc_bar.timestamp) == "09:30"


def test_tooltip_label_includes_ist_for_intraday():
    bar = _bar(2026, 8, 20, 9, 30)
    assert "IST" in format_tooltip_label("1D", bar.timestamp)
