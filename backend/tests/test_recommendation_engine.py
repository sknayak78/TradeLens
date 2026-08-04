"""Unit tests for the pure recommendation engine (no network, no database)."""
from __future__ import annotations

from pathlib import Path

import pytest

from recommendation.config import (
    HOLDING_PERIODS,
    MAX_SCORE,
    MIN_RISK_REWARD,
    SCORING_RULES,
)
from recommendation.engine import RecommendationEngine
from recommendation.models import RecommendationInput

engine = RecommendationEngine()


def _bullish(**overrides) -> RecommendationInput:
    """A textbook long setup: every rule fires and reward:risk is healthy."""
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


# ---------- Configuration ----------

def test_scoring_rules_sum_to_one_hundred():
    assert MAX_SCORE == 100
    assert sum(rule.points for rule in SCORING_RULES) == 100
    assert len({rule.key for rule in SCORING_RULES}) == len(SCORING_RULES)


def test_every_action_has_a_holding_period():
    assert HOLDING_PERIODS == {
        "Strong Buy": "2-6 weeks",
        "Buy": "1-4 weeks",
        "Buy on Breakout": "1-4 weeks after the breakout confirms",
        "Hold": "Existing holders",
        "Watch": "Wait",
        "Wait": "Wait",
        "Avoid": "No Trade",
    }


# ---------- Input validation and construction ----------

def test_input_rejects_non_positive_price_and_blank_symbol():
    with pytest.raises(ValueError):
        RecommendationInput(symbol="RELIANCE", price=0.0)
    with pytest.raises(ValueError):
        RecommendationInput(symbol="  ", price=100.0)


def test_from_snapshot_reads_live_fields_and_ignores_seeded_fields():
    stock = {
        "symbol": " reliance ",
        "price": 110.0,
        "ema20": 105.0,
        "ema50": 100.0,
        "ema200": 90.0,
        "rsi": 60.0,
        # Seeded fields that must never reach the engine.
        "vwap": 999.0,
        "trend": "bearish",
        "avg_volume": 1,
        "day_high": 999.0,
        "score": 12,
    }
    insight = {"support": 100.0, "resistance": 120.0}

    market = RecommendationInput.from_snapshot(stock, insight)

    assert market == _bullish()
    assert not hasattr(market, "vwap")
    assert not hasattr(market, "day_high")
    # Seeded "bearish" trend is ignored; the EMA stack decides.
    assert engine.recommend(market).trend == "bullish"


def test_from_snapshot_prefers_levels_on_the_stock_payload():
    stock = {"symbol": "TCS", "price": 100.0, "support": 95.0, "resistance": 110.0}
    insight = {"support": 1.0, "resistance": 2.0}

    market = RecommendationInput.from_snapshot(stock, insight)

    assert (market.support, market.resistance) == (95.0, 110.0)


def test_from_snapshot_tolerates_missing_indicators_but_requires_price():
    market = RecommendationInput.from_snapshot({"symbol": "SBIN", "price": 100.0})

    assert market.ema20 is None and market.rsi is None
    assert market.support is None and market.resistance is None

    with pytest.raises(ValueError):
        RecommendationInput.from_snapshot({"symbol": "SBIN", "price": None})


# ---------- Actions ----------

def test_full_score_setup_is_a_strong_buy():
    recommendation = engine.recommend(_bullish())

    assert recommendation.score == 100
    assert recommendation.action == "Strong Buy"
    assert recommendation.conviction == "High"
    assert recommendation.trend == "bullish"
    assert recommendation.confidence == 1.0
    assert recommendation.holding_period == "2-6 weeks"
    assert recommendation.warnings == []
    assert set(recommendation.rules_matched) == {rule.key for rule in SCORING_RULES}


def test_score_between_eighty_and_ninety_is_a_plain_buy():
    recommendation = engine.recommend(_bullish(rsi=50.0))

    assert recommendation.score == 85  # healthy-RSI rule does not fire
    assert recommendation.action == "Buy"
    assert recommendation.holding_period == "1-4 weeks"


def test_thin_headroom_becomes_a_breakout_setup():
    recommendation = engine.recommend(
        _bullish(price=100.0, ema20=99.0, ema50=98.0, ema200=97.0,
                 support=99.0, resistance=101.9)
    )

    assert recommendation.score == 85  # room-to-resistance rule does not fire
    assert recommendation.action == "Buy on Breakout"
    assert recommendation.holding_period == "1-4 weeks after the breakout confirms"
    assert recommendation.levels is not None


def test_price_below_every_ema_is_avoided_without_levels():
    recommendation = engine.recommend(
        _bullish(price=80.0, support=70.0, resistance=95.0)
    )

    assert recommendation.trend == "bearish"
    assert recommendation.action == "Avoid"
    assert recommendation.holding_period == "No Trade"
    assert recommendation.levels is None


def test_mixed_ema_stack_is_neutral_and_never_a_buy():
    recommendation = engine.recommend(_bullish(price=102.0, support=95.0))

    assert recommendation.trend == "neutral"
    assert recommendation.action == "Watch"
    assert recommendation.holding_period == "Wait"


def test_overbought_rsi_holds_a_healthy_trend_instead_of_entering():
    recommendation = engine.recommend(_bullish(rsi=85.0))

    assert recommendation.score == 85  # healthy-RSI rule does not fire
    assert recommendation.action == "Hold"
    assert recommendation.holding_period == "Existing holders"
    assert "rsi_overbought" in recommendation.warnings


def test_overbought_rsi_on_a_weak_setup_is_only_a_wait():
    recommendation = engine.recommend(
        RecommendationInput(symbol="ITC", price=110.0, ema20=105.0, rsi=85.0)
    )

    assert recommendation.score == 15
    assert recommendation.action == "Wait"


def test_oversold_rsi_is_flagged():
    recommendation = engine.recommend(_bullish(rsi=25.0))

    assert "rsi_oversold" in recommendation.warnings


def test_poor_reward_to_risk_downgrades_a_buy_to_hold():
    recommendation = engine.recommend(_bullish(resistance=115.0))

    assert recommendation.score == 100
    assert recommendation.levels is not None
    assert recommendation.levels.risk_reward < MIN_RISK_REWARD
    assert recommendation.action == "Hold"
    assert recommendation.holding_period == "Existing holders"
    assert "risk_reward_below_minimum" in recommendation.warnings


def test_price_above_resistance_holds_without_levels():
    recommendation = engine.recommend(_bullish(resistance=105.0))

    assert "price_at_or_above_resistance" in recommendation.warnings
    assert "no_usable_levels" in recommendation.warnings
    assert recommendation.levels is None
    assert recommendation.action == "Hold"


def test_missing_indicators_lower_confidence_and_block_a_buy():
    recommendation = engine.recommend(
        RecommendationInput(symbol="INFY", price=110.0, ema20=105.0, rsi=60.0)
    )

    assert recommendation.trend == "bullish"
    assert recommendation.score == 30  # only EMA20 and RSI rules can fire
    assert recommendation.conviction == "Low"
    assert recommendation.confidence == 0.22  # 2 of 6 indicators, score 30
    assert recommendation.levels is None
    assert recommendation.action == "Avoid"
    assert any(w.startswith("missing_indicators:") for w in recommendation.warnings)


def test_no_ema_data_is_neutral_and_not_actionable():
    recommendation = engine.recommend(
        RecommendationInput(symbol="ITC", price=100.0, rsi=60.0)
    )

    assert recommendation.trend == "neutral"
    assert recommendation.action == "Avoid"


# ---------- Levels ----------

def test_entry_zone_runs_from_the_higher_of_ema20_and_support_to_last_price():
    levels = engine.recommend(_bullish()).levels

    assert levels is not None
    assert levels.entry_min == 105.0  # EMA20 sits above support 100
    assert levels.entry_max == 110.0  # last price


def test_entry_zone_floor_uses_support_when_it_is_above_ema20():
    levels = engine.recommend(_bullish(support=108.0)).levels

    assert levels is not None
    assert levels.entry_min == 108.0
    assert levels.stop_loss == 106.92  # 108 * 0.99


def test_entry_zone_floor_uses_support_when_ema20_is_missing():
    levels = engine.recommend(_bullish(ema20=None)).levels

    assert levels is not None
    assert levels.entry_min == 100.0


def test_no_levels_when_price_sits_below_the_zone_floor():
    recommendation = engine.recommend(_bullish(price=101.0))

    assert recommendation.levels is None  # EMA20 105 is above the last price


def test_stop_and_targets_use_support_and_resistance():
    levels = engine.recommend(_bullish()).levels

    assert levels is not None
    assert levels.stop_loss == 99.0  # support 100 * 0.99
    assert levels.target1 == 120.0  # resistance
    assert levels.target2 == 130.0  # 120 + 0.5 * (120 - 100)
    # Measured from the zone midpoint 107.5: (120 - 107.5) / (107.5 - 99).
    assert levels.risk_reward == 1.47


# ---------- Output shape and purity ----------

def test_rationale_is_short_and_mentions_the_next_step():
    recommendation = engine.recommend(_bullish())

    assert len(recommendation.rationale.split()) <= 60
    assert "entry zone" in recommendation.rationale


def test_hold_rationale_addresses_existing_holders():
    recommendation = engine.recommend(_bullish(rsi=85.0))

    assert "Existing holders" in recommendation.rationale


def test_to_dict_is_json_shaped():
    payload = engine.recommend(_bullish()).to_dict()

    assert payload["symbol"] == "RELIANCE"
    assert payload["action"] == "Strong Buy"
    assert payload["holding_period"] == "2-6 weeks"
    assert payload["levels"]["entry_min"] == 105.0
    assert payload["levels"]["target2"] == 130.0
    assert isinstance(payload["rules_matched"], list)


def test_recommend_is_deterministic_and_batchable():
    market = _bullish()

    first = engine.recommend(market)
    second = engine.recommend(market)
    batch = engine.recommend_many([market, market])

    assert first == second
    assert batch == [first, second]


def test_engine_has_no_io_or_persistence_imports():
    """The engine must stay pure: no network, database, LLM or clock access."""
    package = Path(__file__).resolve().parents[1] / "recommendation"
    forbidden = (
        "requests", "yfinance", "httpx", "urllib", "socket",
        "sqlalchemy", "database", "models import", "openai", "anthropic",
        "services", "seed_data", "random", "datetime", "time",
    )
    for path in sorted(package.glob("*.py")):
        source = path.read_text()
        for token in forbidden:
            assert f"import {token}" not in source, f"{path.name} imports {token}"
            assert f"from {token}" not in source, f"{path.name} imports from {token}"
