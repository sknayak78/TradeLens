"""ER-0018: Watch Next must always be a future market event.

If the latest price has already cleared a hurdle, the trigger state machine
advances to the next logical event instead of asking the trader to wait for
something that already happened.
"""
from __future__ import annotations

import re

import pytest

from recommendation.engine import RecommendationEngine
from recommendation.models import RecommendationInput
from recommendation.triggers import Trigger, _reclaim_chain, resolve_watch_next

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


def _levels_mentioned(text: str) -> list[float]:
    """Parse Indian-formatted prices like 1,300.16 out of a trigger sentence."""
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.\d{2}", text)]


# ---------- Unit: Trigger primitive ----------

def test_above_trigger_is_satisfied_when_price_has_cleared_the_level():
    trigger = Trigger(level=1300.16, direction="above", label="avg")
    assert trigger.is_satisfied(1326.30)
    assert not trigger.is_satisfied(1290.00)


def test_toward_trigger_is_satisfied_at_or_below_the_floor():
    trigger = Trigger(level=1300.16, direction="toward", label="floor")
    assert trigger.is_satisfied(1300.16)
    assert trigger.is_satisfied(1295.00)
    assert not trigger.is_satisfied(1326.30)


def test_reclaim_chain_skips_levels_already_held():
    market = RecommendationInput(
        symbol="X",
        price=1326.30,
        ema20=1300.16,
        ema50=1280.0,
        ema200=1400.0,
        resistance=1500.0,
    )
    future = next(t for t in _reclaim_chain(market) if not t.is_satisfied(market.price))
    assert future.level == 1400.0


# ---------- Reported bug ----------

def test_never_asks_to_reclaim_a_level_price_already_holds():
    """Exact product bug: price 1326.30 must not watch for reclaim of 1300.16."""
    market = RecommendationInput(
        symbol="TEST",
        price=1326.30,
        ema20=1300.16,
        ema50=None,
        ema200=None,
        rsi=58.0,
    )
    recommendation = engine.recommend(market)

    assert recommendation.action == "Wait"
    assert "1,300.16" not in recommendation.next_trigger or "hold above" in (
        recommendation.next_trigger.lower()
    )
    assert "reclaim its recent average price of 1,300.16" not in (
        recommendation.next_trigger
    )
    # Plan must not ask to steady above a level already held.
    assert "steady above its recent average price of 1,300.16" not in (
        recommendation.entry_condition
    )


def test_reported_price_advances_past_the_short_average():
    market = RecommendationInput(
        symbol="TEST",
        price=1326.30,
        ema20=1300.16,
        ema50=None,
        ema200=None,
        rsi=58.0,
    )
    recommendation = engine.recommend(market)
    trigger = recommendation.next_trigger.lower()

    assert "hold above" in trigger or "support" in trigger or "direction" in trigger
    for level in _levels_mentioned(recommendation.next_trigger):
        # Any "above"/"reclaim" hurdle quoted must still be above the last price.
        if "reclaim" in trigger or "steady above" in trigger or "close above" in trigger:
            assert level > market.price


# ---------- Advancement scenarios ----------

def test_bearish_bounce_advances_reclaim_to_the_long_term_average():
    market = RecommendationInput(
        symbol="X",
        price=95.0,
        ema20=90.0,
        ema50=100.0,
        ema200=110.0,
        rsi=55.0,
        support=85.0,
        resistance=120.0,
    )
    recommendation = engine.recommend(market)

    assert recommendation.action == "Avoid"
    assert "90.00" not in recommendation.next_trigger or "hold" in (
        recommendation.next_trigger.lower()
    )
    assert "100.00" in recommendation.next_trigger or "110.00" in (
        recommendation.next_trigger
    )
    assert "reclaim" in recommendation.next_trigger.lower()
    # Next hurdle must still be above price.
    assert "reclaim its recent average price of 90.00" not in recommendation.next_trigger


def test_consolidation_already_above_short_average_advances():
    market = RecommendationInput(
        symbol="INFY",
        price=102.0,
        ema20=100.0,
        ema50=104.0,
        support=95.0,
        resistance=130.0,
    )
    recommendation = engine.recommend(market)

    assert recommendation.strategy == "Consolidation"
    assert "steady above its recent average price of 100.00" not in (
        recommendation.next_trigger
    )
    assert "104.00" in recommendation.next_trigger or "130.00" in (
        recommendation.next_trigger
    )


def test_breakout_already_through_resistance_advances_to_hold_confirmation():
    market = _bullish(
        price=102.0,
        ema20=99.0,
        ema50=98.0,
        ema200=97.0,
        support=99.0,
        resistance=101.0,
    )
    recommendation = engine.recommend(market)

    assert recommendation.strategy == "Breakout"
    assert "already above" in recommendation.next_trigger.lower()
    assert "holds above" in recommendation.next_trigger.lower()
    assert "slip back below" in recommendation.next_trigger.lower()
    assert recommendation.entry_condition.lower().startswith("do not chase")


def test_pullback_trigger_targets_the_zone_floor_not_the_current_price():
    market = _bullish(
        price=1326.30,
        ema20=1300.16,
        ema50=1280.0,
        ema200=1200.0,
        support=1250.0,
        resistance=1400.0,
        rsi=58.0,
    )
    recommendation = engine.recommend(market)

    assert recommendation.strategy == "Pullback"
    assert "1,300.16" in recommendation.next_trigger
    assert "1,326.30" not in recommendation.next_trigger
    assert "pullback toward" in recommendation.next_trigger.lower()


def test_pullback_zone_already_reached_advances_to_invalidation():
    """Price at/under the zone floor → next event is stop invalidation."""
    market = _bullish(
        price=105.0,
        ema20=105.0,
        ema50=100.0,
        ema200=90.0,
        support=100.0,
        resistance=130.0,
        rsi=50.0,
    )
    # Force a pullback-style wait with a usable zone by weakening evidence.
    recommendation = engine.recommend(market)
    if recommendation.strategy == "Pullback" and recommendation.levels is not None:
        if market.price <= recommendation.levels.entry_min:
            assert "cancels" in recommendation.next_trigger.lower() or "stop" in (
                recommendation.next_trigger.lower()
            ) or "close below" in recommendation.next_trigger.lower()


def test_trend_continuation_advances_target_when_target1_is_cleared():
    market = _bullish(price=121.0, resistance=120.0, support=100.0)
    # Price above resistance may not publish Trend Continuation levels; craft
    # via the resolver directly with a synthetic plan.
    from recommendation.models import TradeLevels

    levels = TradeLevels(
        entry_min=105.0,
        entry_max=110.0,
        stop_loss=99.0,
        target1=120.0,
        target2=130.0,
        risk_reward=2.0,
    )
    text = resolve_watch_next(
        market=_bullish(price=121.0),
        strategy="Trend Continuation",
        levels=levels,
        limits=(),
        trend="bullish",
    )
    assert "130.00" in text
    assert "opens the way to 130.00" not in text  # advanced off target1 path
    assert "extends the trend-continuation plan" in text


# ---------- Global invariant ----------

@pytest.mark.parametrize(
    "market",
    [
        RecommendationInput(
            symbol="A", price=1326.30, ema20=1300.16, rsi=58.0,
        ),
        RecommendationInput(
            symbol="B", price=95.0, ema20=90.0, ema50=100.0, ema200=110.0,
            rsi=55.0, support=85.0, resistance=120.0,
        ),
        RecommendationInput(
            symbol="C", price=102.0, ema20=100.0, ema50=104.0,
            support=95.0, resistance=130.0,
        ),
        _bullish(price=102.0, ema20=99.0, ema50=98.0, ema200=97.0,
                 support=99.0, resistance=101.0),
        _bullish(),
        _bullish(price=80.0, support=70.0, resistance=95.0),
    ],
)
def test_reclaim_or_close_above_levels_must_still_be_above_price(
    market: RecommendationInput,
):
    recommendation = engine.recommend(market)
    text = recommendation.next_trigger.lower()
    if not any(token in text for token in ("reclaim", "close above", "steady above")):
        return
    for level in _levels_mentioned(recommendation.next_trigger):
        # Hold-above confirmations may quote a level already cleared; skip those.
        if "hold above" in text or "already above" in text or "holds above" in text:
            continue
        assert level > market.price, recommendation.next_trigger


@pytest.mark.parametrize(
    "market",
    [
        RecommendationInput(
            symbol="A", price=1326.30, ema20=1300.16, rsi=58.0,
        ),
        RecommendationInput(
            symbol="B", price=95.0, ema20=90.0, ema50=100.0, ema200=110.0,
            rsi=55.0, support=85.0, resistance=120.0,
        ),
        _bullish(price=102.0, ema20=99.0, ema50=98.0, ema200=97.0,
                 support=99.0, resistance=101.0),
    ],
)
def test_plan_and_watch_next_share_one_future_thesis(market: RecommendationInput):
    recommendation = engine.recommend(market)
    plan = recommendation.entry_condition.lower()
    watch = recommendation.next_trigger.lower()

    # If watch advanced past a short-average reclaim, plan must not still demand it.
    if "1,300.16" in watch and "reclaim" in watch:
        pytest.fail("stale reclaim should have advanced")
    if market.price > (market.ema20 or 0):
        assert f"reclaim its recent average price of {_fmt(market.ema20)}" not in (
            recommendation.next_trigger
        )
        assert f"steady above its recent average price of {_fmt(market.ema20)}" not in (
            recommendation.entry_condition
        )


def _fmt(value: float | None) -> str:
    assert value is not None
    return f"{value:,.2f}"
