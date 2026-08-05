"""Volume-weighted average price helpers for TradeLens indicators.

Daily bars carry no intraday detail, so the VWAP computed here is a *rolling*
volume-weighted average over the last ``period`` complete sessions rather than a
single-session VWAP.  It answers the same question the UI asks of it — "what has
the average traded price been lately?" — from live data instead of a seeded
literal.
"""
from __future__ import annotations

from typing import Sequence


def typical_prices(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]
) -> list[float]:
    """Return the (high + low + close) / 3 price of each bar."""
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows and closes must be the same length")
    return [
        (float(high) + float(low) + float(close)) / 3
        for high, low, close in zip(highs, lows, closes)
    ]


def calculate_rolling_vwap(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    period: int = 20,
) -> float:
    """Return the volume-weighted average price of the last ``period`` bars.

    Falls back to the unweighted average of the typical prices when the window
    carries no volume at all, so an illiquid symbol still yields a usable price
    instead of a division by zero.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if not closes:
        raise ValueError("closes must not be empty")
    if len(volumes) != len(closes):
        raise ValueError("volumes and closes must be the same length")

    prices = typical_prices(highs, lows, closes)[-period:]
    window_volumes = [float(volume) for volume in volumes[-period:]]

    traded_value = sum(
        price * volume for price, volume in zip(prices, window_volumes)
    )
    traded_volume = sum(window_volumes)
    if traded_volume <= 0:
        return sum(prices) / len(prices)
    return traded_value / traded_volume
