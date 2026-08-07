"""Unit tests for the pure recommendation engine (no network, no database)."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from recommendation.config import (
    ACTIONS,
    BEGINNER_TIPS,
    CONFIDENCE_BANDS,
    CONFIDENCE_CEILING,
    HOLDING_PERIODS,
    IDEAL_FOR,
    MAX_SCORE,
    MIN_RISK_REWARD,
    SCORING_RULES,
    STRATEGIES,
)
from recommendation.engine import RecommendationEngine
from recommendation.models import Recommendation, RecommendationInput

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


# ---------- One representative snapshot per recommendation state ----------

STRONG_BUY = _bullish()
#: Momentum is only lukewarm, so the picture falls short of full conviction.
BUY = _bullish(rsi=50.0, resistance=125.0)
#: A healthy trend that has run too far to join today.
WATCH_OVERBOUGHT = _bullish(rsi=85.0, resistance=125.0)
#: A healthy trend pinned under the ceiling it failed at last time.
WATCH_AT_RESISTANCE = _bullish(
    price=100.0, ema20=99.0, ema50=98.0, ema200=97.0,
    support=99.0, resistance=101.9,
)
#: No side in control and only half the evidence in place.
WAIT = _bullish(price=102.0, rsi=45.0, support=95.0, resistance=104.0)
#: Price below every average: sellers are in charge.
AVOID = _bullish(price=80.0, support=70.0, resistance=95.0)

BY_ACTION = {
    "Strong Buy": STRONG_BUY,
    "Buy": BUY,
    "Watch": WATCH_OVERBOUGHT,
    "Wait": WAIT,
    "Avoid": AVOID,
}


# ---------- Configuration ----------

def test_scoring_rules_sum_to_one_hundred():
    assert MAX_SCORE == 100
    assert sum(rule.points for rule in SCORING_RULES) == 100
    assert len({rule.key for rule in SCORING_RULES}) == len(SCORING_RULES)


def test_position_management_actions_are_out_of_scope():
    """Hold / Add More / Book Profit / Exit belong to the Portfolio Advisor."""
    assert ACTIONS == ("Strong Buy", "Buy", "Watch", "Wait", "Avoid")


def test_no_action_encodes_a_trading_strategy():
    """Breakout/pullback context lives in `strategy`, never in the action."""
    for action in ACTIONS:
        assert not any(word in action.lower() for word in ("breakout", "pullback"))
    assert STRATEGIES == (
        "Trend Continuation",
        "Pullback",
        "Breakout",
        "Consolidation",
        "No Entry Yet",
    )


@pytest.mark.parametrize("action", BY_ACTION)
def test_every_state_reports_a_known_strategy(action: str):
    assert engine.recommend(BY_ACTION[action]).strategy in STRATEGIES


def test_an_entry_call_follows_the_trend():
    for entry in (STRONG_BUY, BUY):
        assert engine.recommend(entry).strategy == "Trend Continuation"


def test_an_overextended_stock_is_bought_back_on_a_pullback():
    recommendation = engine.recommend(WATCH_OVERBOUGHT)

    assert recommendation.action == "Watch"
    assert recommendation.strategy == "Pullback"


def test_a_stock_pinned_under_resistance_needs_the_breakout_to_confirm():
    recommendation = engine.recommend(WATCH_AT_RESISTANCE)

    assert recommendation.action == "Watch"
    assert recommendation.strategy == "Breakout"
    # Breakout never publishes a buy-now entry zone (ER-0016).
    assert recommendation.levels is None


def test_a_waiting_pullback_keeps_the_pullback_thesis():
    """A Wait inside an uptrend is still a Pullback — not a second thesis."""
    assert engine.recommend(WAIT).strategy == "Pullback"


def test_a_downtrend_has_no_entry_plan():
    assert engine.recommend(AVOID).strategy == "No Entry Yet"


def test_every_action_is_fully_configured():
    for table in (HOLDING_PERIODS, CONFIDENCE_BANDS, BEGINNER_TIPS, IDEAL_FOR):
        assert tuple(table) == ACTIONS


def test_holding_period_is_always_a_duration_never_a_status():
    """A trader planning an entry needs the horizon, not "Wait"."""
    for action, period in HOLDING_PERIODS.items():
        assert re.fullmatch(r"\d+-\d+ (Days|Weeks|Months)", period), action


def test_confidence_bands_are_ordered_and_never_reach_certainty():
    ordered = [CONFIDENCE_BANDS[action] for action in ACTIONS]
    for (low, high), (next_low, next_high) in zip(ordered, ordered[1:]):
        assert low > next_low and high > next_high
    assert max(high for _, high in ordered) == CONFIDENCE_CEILING
    assert CONFIDENCE_CEILING < 1.0


# ---------- Input validation and construction ----------

def test_input_rejects_non_positive_price_and_blank_symbol():
    with pytest.raises(ValueError):
        RecommendationInput(symbol="RELIANCE", price=0.0)
    with pytest.raises(ValueError):
        RecommendationInput(symbol="  ", price=100.0)


# ---------- Non-finite provider values ----------

def test_input_rejects_a_non_finite_price():
    for price in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            RecommendationInput(symbol="RELIANCE", price=price)


def test_non_finite_indicators_are_read_as_missing():
    market = _bullish(
        ema20=float("nan"),
        ema50=float("inf"),
        ema200=float("-inf"),
        rsi=float("nan"),
    )

    assert (market.ema20, market.ema50, market.ema200, market.rsi) == (
        None, None, None, None,
    )
    assert market.missing_indicators == ["ema20", "ema50", "ema200", "rsi"]


def test_from_snapshot_treats_nan_indicators_as_missing():
    stock = {
        "symbol": "RELIANCE",
        "price": 110.0,
        "ema20": float("nan"),
        "ema50": float("nan"),
        "ema200": float("nan"),
        "rsi": float("nan"),
    }

    market = RecommendationInput.from_snapshot(
        stock, {"support": 100.0, "resistance": 120.0}
    )

    assert market.missing_indicators == ["ema20", "ema50", "ema200", "rsi"]
    assert (market.support, market.resistance) == (100.0, 120.0)


def test_from_snapshot_rejects_a_nan_price():
    with pytest.raises(ValueError):
        RecommendationInput.from_snapshot(
            {"symbol": "RELIANCE", "price": float("nan")}
        )


def test_a_nan_riddled_snapshot_stays_json_compliant():
    """Regression: NaN in the payload must never reach the JSON encoder."""
    nan = float("nan")
    stock = {
        "symbol": "RELIANCE",
        "price": 110.0,
        "ema20": nan,
        "ema50": nan,
        "ema200": nan,
        "rsi": nan,
        "support": nan,
        "resistance": nan,
    }

    recommendation = engine.recommend(RecommendationInput.from_snapshot(stock))
    payload = recommendation.to_dict()

    # allow_nan=False raises exactly the ValueError FastAPI reported.
    assert json.loads(json.dumps(payload, allow_nan=False))
    assert recommendation.data_quality == "Partial"
    assert recommendation.levels is None
    # Nothing is known, which is a reason to wait, not evidence of a downtrend.
    assert recommendation.action == "Wait"


def test_every_numeric_output_is_finite_across_degraded_inputs():
    nan = float("nan")
    cases = [
        _bullish(),
        _bullish(support=nan, resistance=nan),
        _bullish(rsi=nan, ema200=nan),
        _bullish(ema20=nan, support=109.99),
        RecommendationInput(symbol="ITC", price=0.01, support=nan),
    ]

    for market in cases:
        recommendation = engine.recommend(market)
        numbers = [recommendation.score, recommendation.confidence]
        if recommendation.levels is not None:
            numbers.extend(recommendation.levels.to_dict().values())
        assert all(math.isfinite(value) for value in numbers), market


def test_from_snapshot_reads_live_fields_and_ignores_seeded_fields():
    stock = {
        "symbol": " reliance ",
        "price": 110.0,
        "ema20": 105.0,
        "ema50": 100.0,
        "ema200": 90.0,
        "rsi": 60.0,
        # Seeded and legacy analysis fields that must never reach the engine.
        "vwap": 999.0,
        "trend": "bearish",
        "avg_volume": 1,
        "day_high": 999.0,
        "score": 12,
        "suggestedAction": "Exit",
        "classification": "Avoid",
        "insight": "Seeded insight text.",
    }
    insight = {"support": 100.0, "resistance": 120.0}

    market = RecommendationInput.from_snapshot(stock, insight)

    assert market == _bullish()
    assert not hasattr(market, "vwap")
    assert not hasattr(market, "day_high")
    # Seeded "bearish" trend and a legacy "Exit" action are ignored.
    recommendation = engine.recommend(market)
    assert recommendation.trend == "bullish"
    assert recommendation.action == "Strong Buy"


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


# ---------- Trend: the three averages read together (ER-0014A) ----------

def test_price_above_every_average_is_an_uptrend():
    assert engine.recommend(_bullish()).trend == "bullish"


@pytest.mark.parametrize(
    "price, label",
    [
        (102.0, "below the short average only"),
        (95.0, "below the short and medium averages"),
        (90.5, "barely above the long-term average"),
    ],
)
def test_a_dip_that_holds_the_long_term_average_is_never_a_downtrend(
    price: float, label: str
):
    """ER-0014A: a shorter average alone cannot turn a pullback into a downtrend."""
    recommendation = engine.recommend(_bullish(price=price))

    assert recommendation.trend == "neutral", label
    assert recommendation.action in ("Watch", "Wait"), label


def test_losing_the_long_term_average_is_a_downtrend():
    assert engine.recommend(_bullish(price=89.0)).trend == "bearish"


def test_a_bounce_inside_a_falling_structure_is_not_an_uptrend():
    """Price above all three averages is not enough while they point down."""
    recovering = _bullish(price=110.0, ema20=90.0, ema50=100.0, ema200=105.0)

    assert recovering.stack_falling
    assert engine.recommend(recovering).trend == "neutral"


def test_trend_falls_back_to_the_averages_that_exist():
    below_the_only_average = RecommendationInput(
        symbol="INFY", price=95.0, ema20=100.0
    )
    above_the_only_average = RecommendationInput(
        symbol="INFY", price=105.0, ema20=100.0
    )

    assert engine.recommend(below_the_only_average).trend == "bearish"
    assert engine.recommend(above_the_only_average).trend == "bullish"


# ---------- Actions: one test per recommendation state ----------

def test_a_flawless_setup_is_a_strong_buy():
    recommendation = engine.recommend(STRONG_BUY)

    assert recommendation.score == 100
    assert recommendation.action == "Strong Buy"
    assert recommendation.conviction == "High"
    assert recommendation.trend == "bullish"
    assert recommendation.holding_period == "1-3 Months"
    assert recommendation.data_quality == "Complete"
    assert recommendation.warnings == []
    assert recommendation.levels is not None
    assert set(recommendation.rules_matched) == {rule.key for rule in SCORING_RULES}


def test_a_healthy_setup_with_lukewarm_momentum_is_a_plain_buy():
    recommendation = engine.recommend(BUY)

    assert recommendation.score == 85  # the healthy-momentum rule does not fire
    assert recommendation.action == "Buy"
    assert recommendation.holding_period == "1-3 Weeks"
    assert recommendation.levels is not None
    assert recommendation.levels.risk_reward >= MIN_RISK_REWARD


def test_an_overextended_uptrend_is_a_watch_not_a_buy():
    recommendation = engine.recommend(WATCH_OVERBOUGHT)

    assert recommendation.trend == "bullish"
    assert recommendation.action == "Watch"
    assert "rsi_overbought" in recommendation.warnings
    assert "chase" in recommendation.verdict.lower() or "pullback" in (
        recommendation.verdict.lower()
    )
    assert "cool off" in recommendation.next_trigger


def test_a_trend_pinned_under_resistance_is_a_watch_until_it_breaks_out():
    recommendation = engine.recommend(WATCH_AT_RESISTANCE)

    assert recommendation.action == "Watch"
    assert recommendation.strategy == "Breakout"
    assert recommendation.levels is None
    assert "breakout" in recommendation.verdict.lower()
    assert recommendation.next_trigger == (
        "Watch for a daily close above 101.90: that would confirm the breakout "
        "and create a fresh entry."
    )
    assert recommendation.entry_condition == (
        "Wait for a daily close above 101.90 before entering."
    )
    # No buy-now zone may appear in the plan.
    assert "between" not in recommendation.summary.lower()


def test_a_pullback_inside_an_uptrend_is_a_wait_not_an_avoid():
    """ER-0014A: a dip below the short average is not a broken trend."""
    recommendation = engine.recommend(WAIT)

    assert recommendation.trend == "neutral"
    assert recommendation.score == 55
    assert recommendation.action == "Wait"
    assert "pullback" in recommendation.verdict.lower()
    assert "long-term uptrend" in recommendation.summary.lower()
    assert "pullback" in recommendation.summary.lower()


def test_a_deep_pullback_with_thin_evidence_still_only_waits():
    """Low score cannot produce an Avoid while the long-term trend holds."""
    recommendation = engine.recommend(
        _bullish(price=91.0, support=None, resistance=None, rsi=None)
    )

    assert recommendation.trend == "neutral"
    assert recommendation.score < 40
    assert recommendation.action == "Wait"


def test_a_directionless_stock_is_a_wait():
    """No long-term average and averages in conflict: nothing to lean on."""
    recommendation = engine.recommend(
        RecommendationInput(
            symbol="INFY", price=102.0, ema20=100.0, ema50=104.0,
            support=95.0, resistance=130.0,
        )
    )

    assert recommendation.trend == "neutral"
    assert recommendation.action == "Wait"
    assert recommendation.strategy == "Consolidation"
    assert "nothing today" in recommendation.verdict.lower() or "range" in (
        recommendation.verdict.lower()
    )
    assert "consolidat" in recommendation.summary.lower() or "mixed" in (
        recommendation.summary.lower()
    )


def test_a_downtrend_is_avoided_and_never_priced():
    recommendation = engine.recommend(AVOID)

    assert recommendation.trend == "bearish"
    assert recommendation.action == "Avoid"
    assert recommendation.levels is None
    assert "stay out" in recommendation.verdict.lower()


def test_a_blocked_entry_never_becomes_a_position_management_verdict():
    """Poor reward:risk and missing levels both step down, never to "Hold"."""
    poor_reward = engine.recommend(_bullish(resistance=115.0))
    no_levels = engine.recommend(_bullish(resistance=105.0))

    assert poor_reward.score == 100
    assert poor_reward.strategy == "Pullback"
    assert poor_reward.levels is not None
    assert poor_reward.levels.risk_reward < MIN_RISK_REWARD
    assert poor_reward.action == "Watch"
    assert "risk_reward_below_minimum" in poor_reward.warnings

    # Price at/above resistance → Breakout thesis, no buy-now levels.
    assert no_levels.action == "Watch"
    assert no_levels.strategy == "Breakout"
    assert no_levels.levels is None
    assert "no_usable_levels" in no_levels.warnings
    assert "price_at_or_above_resistance" in no_levels.warnings


def test_oversold_momentum_is_flagged():
    assert "rsi_oversold" in engine.recommend(_bullish(rsi=25.0)).warnings


def test_missing_indicators_are_reported_and_block_an_entry():
    recommendation = engine.recommend(
        RecommendationInput(symbol="INFY", price=110.0, ema20=105.0, rsi=60.0)
    )

    assert recommendation.trend == "bullish"
    assert recommendation.score == 30  # only two rules can fire
    assert recommendation.action == "Wait"
    assert recommendation.data_quality == "Partial"
    assert recommendation.levels is None
    assert recommendation.warnings[0].startswith(
        "partial_data: EMA50, EMA200, support, resistance unavailable"
    )
    assert any("less complete than normal" in risk for risk in recommendation.risks)


# ---------- Confidence ----------

@pytest.mark.parametrize("action", BY_ACTION)
def test_confidence_stays_inside_the_band_for_its_action(action: str):
    recommendation = engine.recommend(BY_ACTION[action])
    low, high = CONFIDENCE_BANDS[action]

    assert recommendation.action == action
    assert low <= recommendation.confidence <= high


def test_confidence_never_reaches_certainty_even_on_a_flawless_setup():
    assert engine.recommend(STRONG_BUY).confidence == CONFIDENCE_CEILING
    assert CONFIDENCE_CEILING < 1.0


def test_incomplete_data_lowers_confidence_within_the_same_action():
    complete = engine.recommend(BUY)
    partial = engine.recommend(BUY.__class__(
        symbol=BUY.symbol, price=BUY.price, ema20=BUY.ema20, ema50=BUY.ema50,
        ema200=BUY.ema200, support=BUY.support, resistance=BUY.resistance,
    ))

    assert partial.action == complete.action
    assert partial.confidence < complete.confidence


def test_confidence_in_standing_aside_grows_as_the_setup_weakens():
    """For a waiting call, weaker evidence means a surer decision to stay out."""
    weaker = engine.recommend(_bullish(price=80.0, rsi=40.0, support=70.0,
                                       resistance=95.0))
    stronger = engine.recommend(AVOID)

    assert weaker.action == stronger.action == "Avoid"
    assert weaker.score < stronger.score
    assert weaker.confidence > stronger.confidence


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


# ---------- Explanations ----------

#: Indicator names a novice should never have to decode in prose.
JARGON = ("EMA", "RSI", "VWAP", "moving average", "oscillator", "MACD")


def _prose(recommendation: Recommendation) -> list[str]:
    return [
        recommendation.verdict,
        recommendation.summary,
        recommendation.next_trigger,
        recommendation.beginner_tip,
        recommendation.ideal_for,
        recommendation.entry_condition,
        *recommendation.why,
        *recommendation.positives,
        *recommendation.risks,
    ]


@pytest.mark.parametrize("action", BY_ACTION)
def test_every_state_explains_itself_in_plain_english(action: str):
    recommendation = engine.recommend(BY_ACTION[action])

    assert recommendation.action == action
    for text in _prose(recommendation):
        assert text and text[0].isupper() and text.endswith((".", "!"))
        for token in JARGON:
            assert token not in text, text


@pytest.mark.parametrize("action", BY_ACTION)
def test_every_state_answers_the_five_beginner_questions(action: str):
    recommendation = engine.recommend(BY_ACTION[action])

    # 1. Should I buy today?  2. Why?  5. What should I watch?
    assert recommendation.verdict
    assert recommendation.summary
    assert recommendation.why
    assert recommendation.next_trigger
    assert recommendation.beginner_tip and recommendation.ideal_for
    # 4. What could go wrong?  Every state carries at least one risk.
    assert recommendation.risks
    # 3. Where do I enter, and where is my downside?
    if action in ("Strong Buy", "Buy"):
        assert recommendation.levels is not None
        assert str(recommendation.levels.entry_min) in recommendation.entry_condition
        assert str(recommendation.levels.stop_loss) in recommendation.entry_condition
        assert recommendation.positives


@pytest.mark.parametrize("action", BY_ACTION)
def test_every_state_says_why_it_is_not_a_stronger_recommendation(action: str):
    why = engine.recommend(BY_ACTION[action]).why

    limits = (
        "It is not",
        "Only",
        "This is the most positive call",
        "A fresh buy is off the table",
    )
    assert any(line.startswith(limits) for line in why), why


def test_a_strong_buy_still_refuses_to_promise_an_outcome():
    recommendation = engine.recommend(STRONG_BUY)

    assert any("probability rather than a promise" in line
               for line in recommendation.why)
    assert any("closes below 99.00" in risk for risk in recommendation.risks)


#: Claims about who is "in control" or how strong an interest is cannot be read
#: off price-versus-average and RSI, so the engine must never make them.
UNSUPPORTED = (
    "buyers are in control",
    "buyers are firmly in control",
    "sellers are in control",
    "selling interest is weak",
    "buying interest is weak",
    "buying interest is strong",
    "no sign that buyers",
)


@pytest.mark.parametrize("action", BY_ACTION)
def test_no_state_claims_more_than_the_indicators_support(action: str):
    """ER-0014A: every sentence must be backed by an available indicator."""
    for text in _prose(engine.recommend(BY_ACTION[action])):
        lowered = text.lower()
        for claim in UNSUPPORTED:
            assert claim not in lowered, text


def test_prose_never_invokes_a_long_term_trend_it_cannot_see():
    """With only a short average present, nothing may be said about the long run."""
    recommendation = engine.recommend(
        RecommendationInput(symbol="INFY", price=110.0, ema20=105.0, rsi=60.0)
    )

    for text in _prose(recommendation):
        assert "long-term" not in text.lower(), text
        assert "every horizon" not in text.lower(), text


def test_prose_never_calls_a_pullback_a_downtrend():
    """The narrative must not contradict a price that is still above its trend."""
    recommendation = engine.recommend(_bullish(price=95.0))

    assert recommendation.action in ("Watch", "Wait")
    for text in _prose(recommendation):
        lowered = text.lower()
        assert "downtrend" not in lowered, text
        assert "sold into" not in lowered, text
    assert any("pullback" in line.lower() for line in recommendation.why)


def test_a_downtrend_is_never_dressed_up_with_encouraging_detail():
    """Room to run is only encouraging while buyers are still in the picture."""
    recommendation = engine.recommend(AVOID)

    assert recommendation.positives == []
    assert not any("clear air" in line for line in recommendation.why)


def test_summary_is_chart_context_not_a_repeat_of_watch_next():
    """ER-0017: each section owns one job — summary must not end with Watch Next."""
    recommendation = engine.recommend(WATCH_OVERBOUGHT)

    assert not recommendation.summary.endswith(recommendation.next_trigger)
    assert recommendation.next_trigger not in recommendation.summary
    assert "pullback" in recommendation.summary.lower()


def test_prose_never_quotes_levels_the_engine_does_not_have():
    recommendation = engine.recommend(
        RecommendationInput(
            symbol="INFY", price=110.0, ema20=100.0, ema50=104.0, ema200=90.0,
            rsi=85.0,
        )
    )

    assert recommendation.levels is None
    assert recommendation.action == "Wait"
    assert recommendation.next_trigger == (
        "Watch for the price to cool off and steady for a few sessions before "
        "considering an entry."
    )
    assert recommendation.entry_condition == (
        "Wait for the price to steady above its recent average price of 100.00 "
        "before considering an entry."
    )


# ---------- Backward compatibility ----------

def test_the_v1_0_fields_are_still_populated():
    payload = engine.recommend(STRONG_BUY).to_dict()

    v1_fields = {
        "symbol", "action", "conviction", "score", "trend", "confidence",
        "data_quality", "holding_period", "entry_condition", "rationale",
        "rules_matched", "warnings", "levels",
    }

    assert v1_fields <= payload.keys()
    assert all(payload[name] is not None for name in v1_fields)
    assert payload["levels"].keys() == {
        "entry_min", "entry_max", "stop_loss", "target1", "target2",
        "risk_reward",
    }


def test_rationale_mirrors_the_summary():
    """v1.0 consumers render `rationale`; it must not drift from `summary`."""
    for market in BY_ACTION.values():
        recommendation = engine.recommend(market)
        assert recommendation.rationale == recommendation.summary


def test_to_dict_is_json_shaped():
    payload = engine.recommend(STRONG_BUY).to_dict()

    assert payload["symbol"] == "RELIANCE"
    assert payload["action"] == "Strong Buy"
    assert payload["holding_period"] == "1-3 Months"
    assert payload["next_trigger"].startswith("Watch the 99.00 level")
    assert isinstance(payload["why"], list)
    assert isinstance(payload["positives"], list)
    assert isinstance(payload["risks"], list)
    assert json.loads(json.dumps(payload, allow_nan=False))


# ---------- Purity ----------

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
