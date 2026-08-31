"""Exponentially weighted moving average helpers for TradeLens indicators.

Single authoritative EMA module — all consumers that compute EMA values for
TradeLens must import from here (or its re-export barrels).  Two public series
functions are exposed:

* ``compute_ema`` — chart/research authoritative path: emits ``None`` until
  ``period`` valid observations accumulate (seeded by their simple average),
  then smooths with the standard recursive formula.  Handles nullable inputs.
* ``calculate_ema`` — daily-context path: seeds with the first observed value
  and emits from index 0.  Designed for gapless float series and short-history
  contexts (e.g. the daily-2y recommendation snapshot).

Both implement the same recursive smoothing recurrence
``prev = value * k + (1 - k) * prev`` where ``k = 2 / (period + 1)``; the
difference is the warm-up/seed strategy, which is an explicit context concern,
not a distinct algorithm.
"""
from __future__ import annotations

from typing import Sequence


# ---------------------------------------------------------------------------
# Authoritative chart / research EMA
# ---------------------------------------------------------------------------

def compute_ema(
    values: Sequence[float | None],
    period: int,
) -> list[float | None]:
    """Exponential moving average over optionally-gapless numeric values.

    A value is emitted only once ``period`` valid observations have accumulated
    (seeded by their simple average), so the result never implies meaningful
    from too little history.  ``None`` inputs are skipped without breaking the
    observation count.

    This is the single authoritative EMA series algorithm for chart overlays
    and Guided Research display (established ER-0037, centralized ER-0038).
    """
    out: list[float | None] = [None] * len(values)
    if period <= 0:
        return out
    k = 2.0 / (period + 1)
    seen = 0
    seed_sum = 0.0
    prev = 0.0
    for i, value in enumerate(values):
        if value is None:
            continue
        if seen < period:
            seed_sum += value
            seen += 1
            if seen == period:
                prev = seed_sum / period
                out[i] = prev
            continue
        prev = value * k + prev * (1 - k)
        out[i] = prev
    return out


# ---------------------------------------------------------------------------
# Daily-context convenience functions (preserves existing behaviour)
# ---------------------------------------------------------------------------

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
