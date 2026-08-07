"""ER-0016: every recommendation is exactly one trading thesis.

Strategy is the parent decision.  These tests pin the consistency rules so a
Breakout can never invite a buy-now entry, a Pullback never asks for a breakout
as its primary next step, and so on.
"""
from __future__ import annotations

import pytest

from recommendation.engine import RecommendationEngine
from recommendation.models import Recommendation, RecommendationInput

engine = RecommendationEngine()


def _bullish(**overrides) -> RecommendationInput:
    values = {
        "symbol": "RELIANCE",
        "price": 110.0,
        "ema20": 105.0,
        "ema50": 100.0,
        "ema200": 90.0,
        "rsi": 60.0,
        "support": 100.0,
        "resistance": 120.0,
    }
    values.update(overrides)
    return RecommendationInput(**values)


# ---------- One representative snapshot per strategy under test ----------

TREND_CONTINUATION = _bullish()
PULLBACK = _bullish(rsi=85.0, resistance=125.0)
BREAKOUT = _bullish(
    price=100.0,
    ema20=99.0,
    ema50=98.0,
    ema200=97.0,
    support=99.0,
    resistance=101.9,
)
#: Reported bug shape: healthy trend, thin headroom, usable-looking zone.
BREAKOUT_REPORTED = RecommendationInput(
    symbol="TEST",
    price=3445.0,
    ema20=3294.0,
    ema50=3200.0,
    ema200=3000.0,
    rsi=65.0,
    support=3250.0,
    resistance=3485.0,
)
CONSOLIDATION = RecommendationInput(
    symbol="INFY",
    price=102.0,
    ema20=100.0,
    ema50=104.0,
    support=95.0,
    resistance=130.0,
)
AVOID = _bullish(price=80.0, support=70.0, resistance=95.0)

BY_STRATEGY = {
    "Trend Continuation": TREND_CONTINUATION,
    "Pullback": PULLBACK,
    "Breakout": BREAKOUT,
    "Consolidation": CONSOLIDATION,
    "Avoid": AVOID,
}


def _prose(recommendation: Recommendation) -> str:
    parts = [
        recommendation.verdict,
        recommendation.summary,
        recommendation.next_trigger,
        recommendation.entry_condition,
        *recommendation.why,
        *recommendation.positives,
        *recommendation.risks,
    ]
    return " ".join(parts).lower()


# ---------- Classification ----------

@pytest.mark.parametrize(
    ("market", "strategy"),
    [
        (TREND_CONTINUATION, "Trend Continuation"),
        (PULLBACK, "Pullback"),
        (BREAKOUT, "Breakout"),
        (BREAKOUT_REPORTED, "Breakout"),
        (CONSOLIDATION, "Consolidation"),
        (AVOID, "No Entry Yet"),
    ],
)
def test_strategy_classification(market: RecommendationInput, strategy: str):
    assert engine.recommend(market).strategy == strategy


def test_avoid_action_pairs_with_no_entry_strategy():
    recommendation = engine.recommend(AVOID)
    assert recommendation.action == "Avoid"
    assert recommendation.strategy == "No Entry Yet"


# ---------- One-thesis consistency ----------

def test_breakout_never_publishes_a_buy_now_entry_zone():
    """The reported contradiction: Entry Range vs Wait for breakout."""
    for market in (BREAKOUT, BREAKOUT_REPORTED):
        recommendation = engine.recommend(market)

        assert recommendation.strategy == "Breakout"
        assert recommendation.levels is None
        assert "close above" in recommendation.next_trigger.lower()
        assert "before entering" in recommendation.entry_condition.lower()
        # Must not invite buying between two prices below resistance.
        assert "between" not in recommendation.entry_condition.lower()
        prose = _prose(recommendation)
        assert "pullback into" not in prose


def test_breakout_reported_bug_shape_is_one_thesis():
    recommendation = engine.recommend(BREAKOUT_REPORTED)

    assert recommendation.strategy == "Breakout"
    assert recommendation.levels is None
    assert recommendation.next_trigger == (
        "Watch for a daily close above 3,485.00: that would confirm the "
        "breakout and create a fresh entry."
    )
    assert recommendation.entry_condition == (
        "Wait for a daily close above 3,485.00 before entering."
    )
    # The old contradictory zone must not leak into any field.
    assert recommendation.levels is None
    assert "3,294" not in recommendation.summary
    assert "3,294" not in recommendation.entry_condition


def test_pullback_never_asks_for_a_breakout_as_the_primary_next_step():
    recommendation = engine.recommend(PULLBACK)

    assert recommendation.strategy == "Pullback"
    assert recommendation.levels is not None
    trigger = recommendation.next_trigger.lower()
    assert "pullback" in trigger or "cool off" in trigger
    assert "confirm the breakout" not in trigger
    assert "close above" not in trigger


def test_trend_continuation_publishes_a_buy_now_plan():
    recommendation = engine.recommend(TREND_CONTINUATION)

    assert recommendation.strategy == "Trend Continuation"
    assert recommendation.action in ("Strong Buy", "Buy")
    assert recommendation.levels is not None
    assert str(recommendation.levels.entry_min) in recommendation.entry_condition
    assert str(recommendation.levels.stop_loss) in recommendation.entry_condition
    assert "close below" in recommendation.next_trigger.lower()
    assert "confirm the breakout" not in recommendation.next_trigger.lower()
    assert "pullback into" not in recommendation.next_trigger.lower()


def test_consolidation_has_no_entry_and_waits_for_direction():
    recommendation = engine.recommend(CONSOLIDATION)

    assert recommendation.strategy == "Consolidation"
    assert recommendation.action == "Wait"
    assert recommendation.levels is None
    trigger = recommendation.next_trigger.lower()
    assert "direction" in trigger or "range" in trigger or "steady" in trigger
    assert "confirm the breakout" not in trigger
    assert "between" not in recommendation.entry_condition.lower()


def test_avoid_has_no_levels_and_no_buy_invitation():
    recommendation = engine.recommend(AVOID)

    assert recommendation.action == "Avoid"
    assert recommendation.strategy == "No Entry Yet"
    assert recommendation.levels is None
    assert "no trade" in recommendation.entry_condition.lower()
    assert "between" not in recommendation.entry_condition.lower()
    assert "confirm the breakout" not in recommendation.next_trigger.lower()


@pytest.mark.parametrize("label", BY_STRATEGY)
def test_entry_condition_and_next_trigger_share_one_thesis(label: str):
    """Watch Next and the legacy entry condition must not fight each other."""
    recommendation = engine.recommend(BY_STRATEGY[label])
    entry = recommendation.entry_condition.lower()
    trigger = recommendation.next_trigger.lower()

    if recommendation.strategy == "Breakout":
        assert "close above" in entry and "close above" in trigger
    elif recommendation.strategy == "Pullback":
        assert "confirm the breakout" not in entry
        assert "confirm the breakout" not in trigger
    elif recommendation.strategy == "Trend Continuation":
        assert "entering between" in entry or "consider entering" in entry
        assert "close below" in trigger
    elif recommendation.strategy in ("Consolidation", "No Entry Yet"):
        assert recommendation.levels is None
        assert "between" not in entry


@pytest.mark.parametrize("label", BY_STRATEGY)
def test_levels_only_appear_for_strategies_with_a_buy_zone(label: str):
    recommendation = engine.recommend(BY_STRATEGY[label])
    if recommendation.strategy in ("Trend Continuation", "Pullback"):
        assert recommendation.levels is not None
    else:
        assert recommendation.levels is None
