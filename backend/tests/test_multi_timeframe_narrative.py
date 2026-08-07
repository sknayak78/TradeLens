"""ER-0017: multi-timeframe narrative intelligence.

The card must reconcile short-term chart moves with the longer-term trend so a
beginner never feels the narrative contradicts what they see.
"""
from __future__ import annotations

import pytest

from recommendation.engine import RecommendationEngine
from recommendation.models import Recommendation, RecommendationInput
from recommendation.timeframe import read_timeframes

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


#: Long-term bearish, recent sessions lifting — the reported communication bug.
COUNTER_TREND = RecommendationInput(
    symbol="TEST",
    price=95.0,
    ema20=90.0,
    ema50=100.0,
    ema200=110.0,
    rsi=55.0,
    support=85.0,
    resistance=105.0,
)

PULLBACK = _bullish(price=102.0, rsi=45.0, support=95.0, resistance=130.0)
TREND_CONTINUATION = _bullish()
BREAKOUT = _bullish(
    price=100.0,
    ema20=99.0,
    ema50=98.0,
    ema200=97.0,
    support=99.0,
    resistance=101.9,
)
CONSOLIDATION = RecommendationInput(
    symbol="INFY",
    price=102.0,
    ema20=100.0,
    ema50=104.0,
    support=95.0,
    resistance=130.0,
)
ALIGNED_BEARISH = _bullish(
    price=80.0, ema20=85.0, ema50=90.0, ema200=100.0, support=70.0, resistance=95.0
)


def _sections(recommendation: Recommendation) -> dict[str, str | list[str]]:
    return {
        "verdict": recommendation.verdict,
        "summary": recommendation.summary,
        "why": recommendation.why,
        "risks": recommendation.risks,
        "plan": recommendation.entry_condition,
        "watch": recommendation.next_trigger,
    }


# ---------- Timeframe detection ----------

def test_counter_trend_rally_is_detected():
    ctx = read_timeframes(COUNTER_TREND)
    assert ctx.long_term == "bearish"
    assert ctx.short_term == "bullish"
    assert ctx.is_counter_trend_rally


def test_pullback_structure_is_detected():
    ctx = read_timeframes(PULLBACK)
    assert ctx.long_term == "bullish"
    assert ctx.short_term == "bearish"
    assert ctx.is_pullback


def test_aligned_bullish_structure_is_detected():
    ctx = read_timeframes(TREND_CONTINUATION)
    assert ctx.structure == "aligned_bullish"


# ---------- Counter-trend rally communication ----------

def test_counter_trend_rally_acknowledges_the_visible_bounce():
    recommendation = engine.recommend(COUNTER_TREND)
    summary = recommendation.summary.lower()
    risks = " ".join(recommendation.risks).lower()

    assert recommendation.action == "Avoid"
    assert "recovered" in summary or "bounce" in summary or "sessions" in summary
    assert "long-term" in summary and "bearish" in summary
    assert "counter-trend rally" in summary
    assert "counter-trend" in risks
    # Must not pretend the chart is only falling.
    assert "lost its long-term average, so the larger trend is down and rallies" not in (
        recommendation.summary
    )


def test_counter_trend_watch_next_targets_the_long_term_reclaim():
    recommendation = engine.recommend(COUNTER_TREND)
    trigger = recommendation.next_trigger.lower()

    # Price is already above the short average — do not ask to "reclaim" it.
    assert "90.00" not in recommendation.next_trigger or "long-term" in trigger
    assert "long-term average" in trigger
    assert "110.00" in recommendation.next_trigger
    assert "temporary" in trigger or "rallies" in trigger


def test_aligned_bearish_avoids_false_reclaim_of_short_average_when_below_it():
    recommendation = engine.recommend(ALIGNED_BEARISH)
    assert recommendation.action == "Avoid"
    assert "long-term" in recommendation.summary.lower()


# ---------- Section uniqueness ----------

@pytest.mark.parametrize(
    "market",
    [TREND_CONTINUATION, PULLBACK, COUNTER_TREND, BREAKOUT, CONSOLIDATION, ALIGNED_BEARISH],
)
def test_sections_do_not_repeat_the_same_guidance(market: RecommendationInput):
    recommendation = engine.recommend(market)
    sections = _sections(recommendation)

    # Summary must not swallow Watch Next (previous repetition bug).
    assert not str(sections["summary"]).endswith(str(sections["watch"]))
    assert str(sections["watch"]) not in str(sections["summary"])

    # Verdict is the action; Watch Next is the event — they must differ.
    assert sections["verdict"] != sections["watch"]
    assert sections["verdict"] != sections["plan"]

    # No why bullet may equal the verdict or the watch line.
    for line in sections["why"]:
        assert line != sections["verdict"]
        assert line != sections["watch"]


@pytest.mark.parametrize(
    "market",
    [TREND_CONTINUATION, PULLBACK, COUNTER_TREND, BREAKOUT, CONSOLIDATION],
)
def test_timeframe_words_appear_when_horizons_matter(market: RecommendationInput):
    recommendation = engine.recommend(market)
    blob = " ".join(
        [
            recommendation.summary,
            *recommendation.why,
            *recommendation.risks,
        ]
    ).lower()
    assert "long-term" in blob or "short-term" in blob or "consolidat" in blob


# ---------- Scenario before/after anchors ----------

def test_bullish_continuation_teaches_alignment():
    recommendation = engine.recommend(TREND_CONTINUATION)
    assert recommendation.strategy == "Trend Continuation"
    assert "agree" in recommendation.summary.lower() or "alignment" in (
        recommendation.summary.lower()
    )
    assert recommendation.levels is not None
    assert str(recommendation.levels.entry_min) in recommendation.entry_condition
    assert str(recommendation.levels.entry_min) not in recommendation.summary


def test_pullback_explains_short_vs_long():
    recommendation = engine.recommend(PULLBACK)
    summary = recommendation.summary.lower()
    assert "long-term uptrend" in summary or "pullback" in summary
    assert "short-term" in summary


def test_breakout_teaches_confirmation():
    recommendation = engine.recommend(BREAKOUT)
    assert recommendation.strategy == "Breakout"
    assert "breakout" in recommendation.summary.lower()
    assert "close above" in recommendation.next_trigger.lower()
    assert recommendation.levels is None


def test_consolidation_explains_mixed_signals():
    recommendation = engine.recommend(CONSOLIDATION)
    assert recommendation.strategy == "Consolidation"
    assert "consolidat" in recommendation.summary.lower() or "mixed" in (
        recommendation.summary.lower()
    )


def test_avoid_without_bounce_still_names_the_long_term_downtrend():
    recommendation = engine.recommend(ALIGNED_BEARISH)
    assert recommendation.action == "Avoid"
    assert "long-term" in recommendation.summary.lower()
    assert "bearish" in recommendation.summary.lower() or "downtrend" in (
        recommendation.summary.lower()
    )
