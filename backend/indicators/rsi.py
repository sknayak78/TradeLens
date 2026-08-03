"""Relative strength index helpers for TradeLens indicators."""
from __future__ import annotations

from typing import Sequence


def calculate_rsi(values: Sequence[float], period: int = 14) -> list[float]:
    """Return the RSI series for the supplied values.

    The implementation uses the standard Wilder RSI formula with a default
    14-period lookback.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []

    if len(values) < 2:
        return [0.0]

    changes = [float(values[index]) - float(values[index - 1]) for index in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [abs(min(change, 0.0)) for change in changes]

    period = min(period, len(changes))
    if period <= 0:
        return [0.0] * len(values)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_series = [0.0] * len(values)
    for index in range(1, len(values)):
        if index < period:
            continue
        if index == period:
            if avg_loss == 0:
                rsi_series[index] = 100.0
            else:
                rsi_series[index] = 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))
        else:
            gain = gains[index - 1]
            loss = losses[index - 1]
            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period
            if avg_loss == 0:
                rsi_series[index] = 100.0
            else:
                rsi_series[index] = 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))

    return rsi_series


def calculate_latest_rsi(values: Sequence[float], period: int = 14) -> float:
    """Return the latest RSI value for the supplied values."""
    if not values:
        raise ValueError("values must not be empty")
    rsi_series = calculate_rsi(values, period)
    return rsi_series[-1]
