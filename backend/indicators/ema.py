"""Exponentially weighted moving average helpers for TradeLens indicators."""
from __future__ import annotations

from typing import Sequence


def calculate_ema(values: Sequence[float], period: int) -> list[float]:
    """Return the EMA series for the supplied values.

    The implementation uses the standard EMA smoothing formula:
    EMA_today = alpha * price + (1 - alpha) * EMA_previous
    where alpha = 2 / (period + 1)
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []

    alpha = 2.0 / (period + 1)
    ema_series: list[float] = []
    previous_ema: float | None = None

    for value in values:
        if previous_ema is None:
            previous_ema = float(value)
        else:
            previous_ema = alpha * float(value) + (1 - alpha) * previous_ema
        ema_series.append(previous_ema)

    return ema_series


def calculate_latest_ema(values: Sequence[float], period: int) -> float:
    """Return the latest EMA value for the supplied values."""
    if not values:
        raise ValueError("values must not be empty")
    ema_series = calculate_ema(values, period)
    return ema_series[-1]
