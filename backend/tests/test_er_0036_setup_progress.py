"""ER-0036 — persistent TradingSetup vs SetupProgress.

Pins the invariant that drives the whole feature: a TradingSetup is stable
market structure (derived from support/EMA20, never today's close), while
SetupProgress is where today's price sits against that unchanging setup.  Daily
price movement may change progress/action/next trigger but must not rebuild the
structural setup, and a price already inside the structural zone must never be
told to wait for a pullback into it.
"""
from __future__ import annotations

import pytest

from recommendation.engine import engine
from recommendation.models import RecommendationInput
from recommendation.setup import build_setup
from recommendation.progress import evaluate_progress


def _market(**overrides) -> RecommendationInput:
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


# Structural zone for the textbook case: floor = max(ema20 105, support 100) = 105,
# span = 20, band = max(105*0.05=5.25, 20*0.5=10) = 10, ceiling = min(115, 119.4) = 115.
STRUCTURAL = {
    "entry_min": 105.0,
    "entry_max": 115.0,
    "planned_entry": 110.0,
    "stop_loss": 99.0,
    "target1": 120.0,
    "target2": 130.0,
}


# ---------- 1. The setup is stable across daily price updates ----------

def test_setup_zone_is_structural_and_independent_of_price():
    """Vary today's close broadly; the structural zone never moves."""
    setups = [
        build_setup(_market(price=110.0), "Trend Continuation", "bullish"),
        build_setup(_market(price=116.0), "Trend Continuation", "bullish"),
        build_setup(_market(price=106.5), "Trend Continuation", "bullish"),
    ]
    assert all(s is not None for s in setups)
    for setup in setups:
        assert (setup.entry_min, setup.entry_max) == (105.0, 115.0)
        assert setup.planned_entry == STRUCTURAL["planned_entry"]
        assert setup.stop_loss == STRUCTURAL["stop_loss"]
        assert setup.thesis  # a structural thesis is always stated


def test_setup_is_unchanged_by_which_direction_price_moves_today():
    """Two very different closes share the same levels; only progress differs."""
    low = build_setup(_market(price=104.0), "Trend Continuation", "bullish")
    high = build_setup(_market(price=118.0), "Trend Continuation", "bullish")
    assert low == high


# ---------- 2. Price entering the zone updates progress, not the setup ----------

def test_price_entering_the_zone_updates_progress_without_moving_the_setup():
    setup = build_setup(_market(), "Trend Continuation", "bullish")
    assert setup is not None

    before = evaluate_progress(101.0, setup, "Watch")
    after = evaluate_progress(110.0, setup, "Strong Buy")

    assert before.status == "awaiting_entry"
    assert after.status == "ready"

    # ...and the structural setup is byte-for-byte the same plan.
    assert build_setup(_market(price=101.0), "Trend Continuation", "bullish") == setup


def test_progress_action_mirrors_the_engine_action_under_a_single_authority():
    """Progress action is the recommendation's own action, never a second thesis."""
    for price in (101.0, 106.0, 110.0, 114.0, 130.0):
        recommendation = engine.recommend(_market(price=price))
        if recommendation.progress is not None:
            assert recommendation.progress.action == recommendation.action


# ---------- 3. Price outside the structural zone ----------

def test_price_below_the_zone_is_awaiting_entry():
    setup = build_setup(_market(), "Trend Continuation", "bullish")
    assert setup is not None
    progress = evaluate_progress(102.0, setup, "Watch")

    assert progress.status == "awaiting_entry"
    assert progress.distance_to_entry_pct is not None
    assert progress.invalidation is None


def test_price_above_the_structural_ceiling_is_extended():
    setup = build_setup(_market(), "Trend Continuation", "bullish")
    assert setup is not None
    progress = evaluate_progress(118.0, setup, "Watch")

    assert progress.status == "extended"
    assert "chase" in progress.next_event.lower()


# ---------- 4. No contradictory "wait for a pullback" when already in-zone ----------

def test_in_zone_price_never_told_to_wait_for_a_pullback():
    """The ER-0036 contradiction: price already in the structural zone."""
    setup = build_setup(_market(price=112.0, rsi=85.0), "Pullback", "bullish")
    assert setup is not None
    # Price 112 sits inside the structural zone [105, 115] for this input.
    progress = evaluate_progress(112.0, setup, "Watch")

    assert progress.status == "in_entry_zone"
    lower = progress.next_event.lower()
    # It must not ask for a pullback / to settle back into a zone it is already in.
    assert "no further pullback is required" in lower
    assert "wait for a pullback" not in lower
    assert progress.invalidation is None


def test_in_zone_trend_continuation_is_ready_with_no_pullback_instruction():
    setup = build_setup(_market(price=110.0), "Trend Continuation", "bullish")
    assert setup is not None
    progress = evaluate_progress(110.0, setup, "Strong Buy")

    assert progress.status == "ready"
    assert "actionable today" in progress.next_event.lower()
    assert "wait for a pullback" not in progress.next_event.lower()


# ---------- 5. Invalidation updates progress without redefining the setup ----------

def test_invalidation_changes_progress_but_not_the_structural_setup():
    setup = build_setup(_market(), "Trend Continuation", "bullish")
    assert setup is not None

    progress = evaluate_progress(98.0, setup, "Watch")

    assert progress.status == "invalidated"
    assert progress.invalidation is not None
    assert progress.next_event
    # The setup itself is untouched by the broken price.
    assert build_setup(_market(), "Trend Continuation", "bullish") == setup


def test_invalidation_never_emits_a_newly_rebuilt_setup():
    """After invalidation the original setup values are still exposed."""
    setup = build_setup(_market(), "Trend Continuation", "bullish")
    assert setup is not None
    progress = evaluate_progress(95.0, setup, "Watch")

    assert progress.status == "invalidated"
    assert (setup.entry_min, setup.entry_max) == (
        STRUCTURAL["entry_min"], STRUCTURAL["entry_max"],
    )


# ---------- 6. Recommendation flows through the single authority ----------

def test_engine_attaches_setup_and_progress_to_the_recommendation():
    """The single authority (`decide`/engine) now also carries setup+progress."""
    from services.stock_decision import decide

    row = {
        "symbol": "RELIANCE", "price": 110.0, "ema20": 105.0, "ema50": 100.0,
        "ema200": 90.0, "rsi": 60.0,
    }
    decision = decide(row, {"support": 100.0, "resistance": 120.0})
    recommendation = decision.recommendation
    assert recommendation is not None
    assert recommendation.setup is not None
    assert recommendation.progress is not None
    assert recommendation.progress.action == recommendation.action


def test_legacy_levels_still_derive_from_the_same_authoritative_model():
    """The published `levels` continue to be derived by the single authority.

    ER-0036 keeps the legacy `levels` field intact (and hence the REST contract
    frozen) while the structural `setup`/`progress` are exposed on the same
    recommendation model, so consumers never reconstruct setup or progress.
    """
    from services.stock_decision import decide

    row = {
        "symbol": "RELIANCE", "price": 110.0, "ema20": 105.0, "ema50": 100.0,
        "ema200": 90.0, "rsi": 60.0,
    }
    decision = decide(row, {"support": 100.0, "resistance": 120.0})
    recommendation = decision.recommendation
    assert recommendation is not None

    # Legacy published zone: floor = max(ema20, support) = 105, ceiling = close.
    assert recommendation.levels is not None
    assert recommendation.levels.entry_min == 105.0
    assert recommendation.levels.entry_max == 110.0

    # The structural setup shares the same floor but has a price-independent
    # ceiling, and progress is consistent with the recommendation.
    assert recommendation.setup is not None
    assert recommendation.setup.entry_min == 105.0
    assert recommendation.setup.entry_max == 115.0
    assert recommendation.progress is not None
    assert recommendation.progress.status == "ready"
    assert recommendation.progress.action == recommendation.action


# ---------- Strategy gating ----------

def test_no_structural_setup_for_non_buy_zone_strategies():
    """Breakout/Consolidation/No Entry Yet have no stable zone to track."""
    from services.stock_decision import decide

    for row, insight in (
        (  # Breakout: pinned under resistance with thin headroom.
            {"symbol": "T", "price": 100.0, "ema20": 99.0, "ema50": 98.0,
             "ema200": 97.0, "rsi": 65.0},
            {"support": 99.0, "resistance": 101.9},
        ),
        (  # Consolidation.
            {"symbol": "I", "price": 102.0, "ema20": 100.0, "ema50": 104.0,
             "rsi": 55.0},
            {"support": 95.0, "resistance": 130.0},
        ),
    ):
        decision = decide(row, insight)
        recommendation = decision.recommendation
        assert recommendation is not None
        if recommendation.strategy not in ("Trend Continuation", "Pullback"):
            assert recommendation.setup is None
            assert recommendation.progress is None
