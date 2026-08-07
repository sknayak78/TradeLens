"""Mentor Engine: Trading Setup vs Setup Progress.

The setup (strategy, structural entry zone, planned entry, R:R) must stay fixed
when only the last price moves. Progress and action may change.
"""
from __future__ import annotations

import pytest

from recommendation.engine import RecommendationEngine
from recommendation.models import RecommendationInput

engine = RecommendationEngine()


def _struct(**price_and_overrides) -> RecommendationInput:
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
    values.update(price_and_overrides)
    return RecommendationInput(**values)


# ---------- Core Mentor Engine invariants ----------

def test_setup_stable_when_only_price_moves():
    day1 = engine.recommend(_struct(price=110.0))
    day2 = engine.recommend(_struct(price=112.0))

    assert day1.setup is not None and day2.setup is not None
    assert day1.setup.structure_key == day2.setup.structure_key
    assert day1.setup.strategy == day2.setup.strategy == "Trend Continuation"
    assert day1.setup.levels == day2.setup.levels
    assert day1.setup.planned_entry == day2.setup.planned_entry
    assert day1.setup.levels is not None
    assert day1.setup.levels.risk_reward == day2.setup.levels.risk_reward
    # Progress is allowed to change with the session.
    assert day1.progress is not None and day2.progress is not None
    assert day1.progress.status == "ready"
    assert day2.progress.status == "extended"
    assert day1.action == "Strong Buy"
    assert day2.action == "Watch"


def test_entry_zone_does_not_use_todays_close_as_ceiling():
    recommendation = engine.recommend(_struct(price=112.0))
    levels = recommendation.setup.levels
    assert levels is not None
    assert levels.entry_max != 112.0
    assert levels.entry_max < 112.0


def test_risk_reward_uses_planned_entry_not_spot_price():
    recommendation = engine.recommend(_struct(price=112.0))
    setup = recommendation.setup
    assert setup is not None and setup.levels is not None and setup.planned_entry is not None
    planned = setup.planned_entry
    levels = setup.levels
    expected = (levels.target1 - planned) / (planned - levels.stop_loss)
    assert levels.risk_reward == round(expected, 2)
    # Spot-based R:R would differ once price leaves the zone.
    spot_rr = (levels.target1 - 112.0) / (112.0 - levels.stop_loss)
    assert abs(levels.risk_reward - round(spot_rr, 2)) > 0.01


def test_summary_does_not_repeat_watch_next():
    recommendation = engine.recommend(_struct(price=112.0))
    assert recommendation.next_trigger not in recommendation.summary
    assert not recommendation.summary.endswith(recommendation.next_trigger)


# ---------- Strategy regression matrix ----------

STRATEGIES = {
    "Trend Continuation": _struct(price=110.0),
    "Pullback": _struct(price=110.0, rsi=85.0, resistance=125.0),
    "Breakout": _struct(
        price=100.0, ema20=99.0, ema50=98.0, ema200=97.0,
        support=99.0, resistance=101.9,
    ),
    "Consolidation": RecommendationInput(
        symbol="INFY", price=102.0, ema20=100.0, ema50=104.0,
        support=95.0, resistance=130.0,
    ),
    "No Entry Yet": _struct(price=80.0, support=70.0, resistance=95.0),
}


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_each_supported_strategy_builds_setup_and_progress(strategy: str):
    recommendation = engine.recommend(STRATEGIES[strategy])
    assert recommendation.strategy == strategy
    assert recommendation.setup is not None
    assert recommendation.progress is not None
    assert recommendation.setup.strategy == strategy
    assert recommendation.next_trigger == recommendation.progress.next_event
    assert recommendation.verdict
    assert recommendation.summary
    assert recommendation.why
    assert recommendation.risks


def test_breakout_keeps_plan_on_setup_but_not_legacy_buy_now_levels():
    recommendation = engine.recommend(STRATEGIES["Breakout"])
    assert recommendation.strategy == "Breakout"
    assert recommendation.levels is None
    assert recommendation.setup.levels is not None
    assert recommendation.setup.planned_entry is not None
    assert recommendation.setup.levels.entry_min >= (
        STRATEGIES["Breakout"].resistance or 0
    )
    assert recommendation.progress.status == "breakout_pending"


def test_pullback_and_continuation_publish_legacy_levels_from_setup():
    for key in ("Trend Continuation", "Pullback"):
        recommendation = engine.recommend(STRATEGIES[key])
        assert recommendation.levels == recommendation.setup.levels
        assert recommendation.levels is not None


def test_avoid_has_no_setup_levels():
    recommendation = engine.recommend(STRATEGIES["No Entry Yet"])
    assert recommendation.action == "Avoid"
    assert recommendation.setup.levels is None
    assert recommendation.progress.status == "no_setup"
