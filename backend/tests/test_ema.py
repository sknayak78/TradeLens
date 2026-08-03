"""Unit tests for exponential moving average helpers."""
from __future__ import annotations

from indicators.ema import calculate_ema, calculate_latest_ema


def _manual_ema(values, period):
    alpha = 2.0 / (period + 1)
    ema_series = []
    prev = None
    for value in values:
        prev = float(value) if prev is None else alpha * float(value) + (1 - alpha) * prev
        ema_series.append(prev)
    return ema_series


def test_calculate_ema20_matches_expected_series():
    values = [10, 12, 11, 13, 14, 15, 16, 15, 17, 18, 16, 19, 20]

    ema = calculate_ema(values, 20)
    expected = _manual_ema(values, 20)

    assert len(ema) == len(values)
    assert ema[0] == 10.0
    assert ema[-1] == expected[-1]
    assert round(ema[4], 6) == round(expected[4], 6)


def test_calculate_latest_ema50_uses_final_smoothed_value():
    values = [100, 102, 101, 103, 104, 106, 105, 107, 108, 110, 109, 111, 112]

    ema = calculate_latest_ema(values, 50)
    expected = _manual_ema(values, 50)[-1]

    assert round(ema, 6) == round(expected, 6)
