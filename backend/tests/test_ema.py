"""Unit tests for exponential moving average helpers."""
from __future__ import annotations

import pytest

from indicators.ema import calculate_ema, calculate_ema_over_lookback, calculate_latest_ema


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


def test_calculate_ema_over_lookback_warms_after_period_observations():
    # SMA-seeded warm-up: values are None until `period` observations, then the
    # simple average seeds the series and EMA continues from there.
    assert calculate_ema_over_lookback([10, 11, 12, 13], 3) == [
        None,
        None,
        11.0,
        12.0,
    ]
    assert calculate_ema_over_lookback([10, 11, 12, 13], 20) == [
        None,
        None,
        None,
        None,
    ]
    assert calculate_ema_over_lookback([], 20) == []


def test_calculate_ema_over_lookback_seeds_from_simple_average():
    # After three observations (10, 20, 30) the seed is their average, 20.0.
    values = [10.0, 20.0, 30.0, 31.0]
    result = calculate_ema_over_lookback(values, 3)
    assert result[2] == 20.0
    alpha = 2.0 / (3 + 1)
    assert result[3] == pytest.approx(31.0 * alpha + 20.0 * (1 - alpha))


def test_calculate_ema_over_lookback_skips_gaps_without_breaking_warmup():
    # A None gap does not consume the running observation budget; warm-up needs
    # `period` real observations and the seed stays the real average.
    values = [10.0, 11.0, None, 12.0, 13.0]
    result = calculate_ema_over_lookback(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] is None  # gap emitted as None, does not count toward warm-up
    # Third real observation (idx3, value 12) makes warm-up complete: seed is the
    # average of 10, 11, 12 = 11.0 emitted at that index.
    assert result[3] == 11.0
    # From the fourth real observation the EMA continues smoothing (alpha=0.5).
    assert result[4] == pytest.approx(13.0 * 0.5 + 11.0 * 0.5)


def test_calculate_ema_over_lookback_returns_nulls_for_non_positive_period():
    assert calculate_ema_over_lookback([1.0, 2.0], 0) == [None, None]
    assert calculate_ema_over_lookback([1.0, 2.0], -1) == [None, None]
