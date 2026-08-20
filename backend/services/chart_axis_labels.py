"""Timeframe-aware chart axis label helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.market_data.models import OHLCVBar

IST = ZoneInfo("Asia/Kolkata")


def bar_timestamp_ist(bar: OHLCVBar) -> datetime:
    timestamp = bar.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(IST)


def series_timestamp(bar: OHLCVBar) -> str:
    """Canonical ISO timestamp for a chart point (India timezone)."""
    return bar_timestamp_ist(bar).isoformat()


def format_axis_tick_label(timeframe: str, timestamp: datetime) -> str:
    """Format one X-axis tick label for the given timeframe."""
    ist = timestamp.astimezone(IST)
    if timeframe == "1D":
        return ist.strftime("%H:%M")
    if timeframe in {"1W", "1M", "3M"}:
        return ist.strftime("%d %b")
    if timeframe == "1Y":
        return ist.strftime("%b %Y")
    return ist.strftime("%d %b %Y")


def format_tooltip_label(timeframe: str, timestamp: datetime) -> str:
    """Human-readable label for chart tooltips."""
    ist = timestamp.astimezone(IST)
    if timeframe == "1D":
        return ist.strftime("%d %b %Y, %H:%M IST")
    if timeframe == "1Y":
        return ist.strftime("%d %b %Y")
    return ist.strftime("%d %b %Y, %H:%M IST")
