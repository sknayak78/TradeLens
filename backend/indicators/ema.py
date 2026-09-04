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


def calculate_ema_over_lookback(
    values: Sequence[float | None],
    period: int,
) -> list[float | None]:
    """Return the EMA series using the chart/research warm-up contract.

    This is the authoritative implementation behind the chart and Guided
    Research EMA overlays (see ``test_er_0037_ema_consistency.py``). Unlike
    :func:`calculate_ema` (a continuous, first-value-seeded series), each
    emitted value is SMA-seeded once ``period`` valid observations have
    accumulated, and ``None`` is emitted until the series is warm. That way the
    result never implies meaningfulness from too little history, and gaps
    (``None`` inputs) are skipped without breaking the sequence.

    ``services/chart_series`` delegates to this function rather than keeping a
    second EMA algorithm.
    """
    out: list[float | None] = [None] * len(values)
    if period <= 0:
        return out
    alpha = 2.0 / (period + 1)
    seen = 0
    seed_sum = 0.0
    previous_ema = 0.0
    for index, value in enumerate(values):
        if value is None:
            continue
        if seen < period:
            seed_sum += value
            seen += 1
            if seen == period:
                previous_ema = seed_sum / period
                out[index] = previous_ema
            continue
        previous_ema = value * alpha + previous_ema * (1 - alpha)
        out[index] = previous_ema
    return out
