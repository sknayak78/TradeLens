"""ER-0021 — Single Setup Authority for stock-detail display.

Trading Plan must follow SetupProgress.status, and Chart Suggested Action must
follow recommendation.action (never legacy suggestedAction when a recommendation
exists). Decision thresholds and action_from_progress are unchanged.
"""
from __future__ import annotations

import pytest

from recommendation.config import MIN_RISK_REWARD
from recommendation.engine import RecommendationEngine
from recommendation.models import RecommendationInput

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


# Conceptual cross-stock shapes (not live Yahoo). Names document UX regressions.
BHARTI = _bullish(price=105.0, resistance=108.0, rsi=45.0, support=98.0)
EICHER = _bullish(
    price=100.0,
    ema20=99.0,
    ema50=98.0,
    ema200=97.0,
    support=99.0,
    resistance=101.9,
)
MARUTI = _bullish(
    price=100.5,
    ema20=99.0,
    ema50=98.0,
    ema200=97.0,
    support=99.0,
    resistance=101.9,
)
TATA = RecommendationInput(
    symbol="TATAMOTORS",
    price=80.0,
    ema20=100.0,
    ema50=105.0,
    ema200=110.0,
    rsi=35.0,
    support=70.0,
    resistance=95.0,
)

PULLBACK_AWAITING = _bullish(price=118.0, rsi=85.0, resistance=125.0)
PULLBACK_IN_ZONE = _bullish(price=110.0, rsi=85.0, resistance=125.0)
BREAKOUT_PENDING = EICHER
BREAKOUT_HOLDING = _bullish(
    price=102.5,
    ema20=99.0,
    ema50=98.0,
    ema200=97.0,
    support=99.0,
    resistance=101.9,
)


def test_a_pullback_awaiting_entry_keeps_wait_for_zone_plan():
    recommendation = engine.recommend(PULLBACK_AWAITING)

    assert recommendation.strategy == "Pullback"
    assert recommendation.progress is not None
    assert recommendation.progress.status == "awaiting_entry"
    entry = recommendation.entry_condition.lower()
    assert "wait for the price to pull back into the structural zone" in entry
    assert "already inside" not in entry


def test_b_pullback_in_entry_zone_acknowledges_zone_and_stays_watch():
    recommendation = engine.recommend(PULLBACK_IN_ZONE)

    assert recommendation.strategy == "Pullback"
    assert recommendation.progress is not None
    assert recommendation.progress.status == "in_entry_zone"
    assert recommendation.action == "Watch"

    entry = recommendation.entry_condition.lower()
    banned = "wait for the price to pull back into the structural zone"
    assert banned not in entry
    assert "already inside the structural zone" in entry
    assert "patient" in entry or "do not chase" in entry


def test_b_bharti_poor_rr_in_zone_never_asks_to_pull_back():
    """Bharti regression: in_zone + poor R:R stays WATCH, no stale pullback plan."""
    recommendation = engine.recommend(BHARTI)

    assert recommendation.strategy == "Pullback"
    assert recommendation.progress is not None
    assert recommendation.progress.status == "in_entry_zone"
    assert recommendation.levels is not None
    assert recommendation.levels.risk_reward < MIN_RISK_REWARD
    assert recommendation.action == "Watch"
    assert "risk_reward_below_minimum" in recommendation.warnings

    entry = recommendation.entry_condition.lower()
    assert "wait for the price to pull back" not in entry
    assert "already inside the structural zone" in entry
    # Chart authority is frontend, but the engine action must remain WATCH.
    assert recommendation.action != "Buy"
    assert "buy on breakout" not in recommendation.entry_condition.lower()


def test_c_breakout_pending_plan_matches_watch_next_confirmation():
    recommendation = engine.recommend(BREAKOUT_PENDING)

    assert recommendation.strategy == "Breakout"
    assert recommendation.progress is not None
    assert recommendation.progress.status == "breakout_pending"
    assert recommendation.action == "Watch"

    entry = recommendation.entry_condition.lower()
    trigger = recommendation.next_trigger.lower()
    assert "close above" in entry
    assert "close above" in trigger
    assert "101.90" in recommendation.entry_condition
    assert "101.90" in recommendation.next_trigger


def test_d_breakout_holding_plan_acknowledges_confirmation():
    recommendation = engine.recommend(BREAKOUT_HOLDING)

    assert recommendation.strategy == "Breakout"
    assert recommendation.progress is not None
    assert recommendation.progress.status == "breakout_holding"
    assert recommendation.action == "Watch"

    entry = recommendation.entry_condition.lower()
    trigger = recommendation.next_trigger.lower()
    assert "already" in entry or "underway" in entry or "holds" in entry
    assert "wait for a daily close above 101.90 before entering" not in entry
    assert "already above" in trigger or "holds above" in trigger
    # Current action remains Watch — confirmation is the trigger, not BUY.
    assert recommendation.action == "Watch"


def test_e_invalidated_has_no_stale_entry_instruction():
    # Build a continuation setup then push price through the stop.
    healthy = engine.recommend(_bullish(price=110.0))
    assert healthy.setup is not None and healthy.setup.levels is not None
    stop = healthy.setup.levels.stop_loss
    broken = engine.recommend(_bullish(price=stop - 0.5))

    assert broken.progress is not None
    assert broken.progress.status == "invalidated"
    entry = broken.entry_condition.lower()
    assert "no active entry plan" in entry
    assert "invalidated" in entry
    assert "wait for the price to pull back into the structural zone" not in entry
    assert "plan the entry between" not in entry


@pytest.mark.parametrize(
    "label,fixture,action,strategy",
    [
        ("Eicher", EICHER, "Watch", "Breakout"),
        ("Maruti", MARUTI, "Watch", "Breakout"),
        ("Bharti", BHARTI, "Watch", "Pullback"),
        ("Tata Motors", TATA, "Avoid", "No Entry Yet"),
    ],
)
def test_i_cross_stock_authority_shapes(label, fixture, action, strategy):
    recommendation = engine.recommend(fixture)
    assert recommendation.action == action, label
    assert recommendation.strategy == strategy, label
    if strategy == "Pullback" and recommendation.progress.status == "in_entry_zone":
        assert "wait for the price to pull back" not in (
            recommendation.entry_condition.lower()
        )
    if strategy == "Breakout":
        assert recommendation.action == "Watch"
        assert "buy on breakout" not in recommendation.entry_condition.lower()


# ---------- Rankings / Opportunities authority ----------

def test_opportunities_exposes_mentor_action_and_strategy(monkeypatch):
    """Mentor Breakout/Wait wins over legacy Trend Continuation / Buy on Breakout."""
    from datetime import datetime, timezone

    from analysis.service import Analysis
    from routers import market as market_router
    from services.market_data_service import MarketDataMetadata, MarketDataResult
    from services.stock_decision import StockDecision

    metadata = MarketDataMetadata(
        provider="seed",
        cached=False,
        as_of=datetime.now(timezone.utc),
        market_status="OPEN",
    )
    stock = {
        "symbol": "INFY",
        "name": "Infosys",
        "price": 100.0,
        "changePct": 1.0,
        "score": 75,
        "trend": "bullish",
        "rsi": 60.0,
        "ema20": 99.0,
        "ema50": 98.0,
        "ema200": 97.0,
        "vwap": 99.0,
        "volume": 1000,
        "avg_volume": 800,
        "day_high": 101.0,
        "sector": "IT",
        "support": 99.0,
        "resistance": 101.9,
    }
    legacy = Analysis(
        symbol="INFY",
        trend="bullish",
        strength_score=80,
        stars=4,
        classification="Good",
        trade_setup="Trend Continuation",
        risk_level="Medium",
        suggested_action="Buy on Breakout",
        insight="legacy",
        rules_matched=[],
    )
    mentor = engine.recommend(
        RecommendationInput(
            symbol="INFY",
            price=100.0,
            ema20=99.0,
            ema50=98.0,
            ema200=97.0,
            rsi=60.0,
            support=99.0,
            resistance=101.9,
        )
    )
    assert mentor.strategy == "Breakout"
    assert mentor.action in ("Watch", "Wait")

    decide_calls = {"n": 0}

    def _decide(snapshot, insight=None):
        decide_calls["n"] += 1
        return StockDecision(
            recommendation=mentor, trend=mentor.trend, score=mentor.score
        )

    monkeypatch.setattr(
        market_router.market_data_service,
        "get_opportunities",
        lambda: MarketDataResult(
            data=[{"symbol": "INFY", "reason": "seed"}],
            metadata=metadata,
        ),
    )
    monkeypatch.setattr(
        market_router.market_data_service,
        "get_stock",
        lambda symbol: MarketDataResult(data={**stock, "symbol": symbol}, metadata=metadata),
    )
    monkeypatch.setattr(market_router.analysis_service, "analyse", lambda s: legacy)
    monkeypatch.setattr(market_router, "decide", _decide)

    rows = market_router.opportunities()

    assert len(rows) == 1
    row = rows[0]
    assert decide_calls["n"] == 1  # reused — not called twice
    assert row.strategy == mentor.strategy == "Breakout"
    assert row.action == mentor.action
    assert row.action != "Buy on Breakout"
    # Legacy fields remain the analysis classifier's values.
    assert row.tradeSetup == "Trend Continuation"
    assert row.suggestedAction == "Buy on Breakout"


def test_opportunities_row_matches_stock_detail_authority(monkeypatch):
    """INFY regression: Opportunities action/strategy agree with decide()."""
    from datetime import datetime, timezone

    from routers import market as market_router
    from services.market_data_service import MarketDataMetadata, MarketDataResult
    from services.stock_decision import decide as real_decide

    metadata = MarketDataMetadata(
        provider="seed",
        cached=False,
        as_of=datetime.now(timezone.utc),
        market_status="OPEN",
    )
    stock = {
        "symbol": "INFY",
        "name": "Infosys",
        "price": 100.0,
        "changePct": 1.0,
        "score": 75,
        "trend": "bullish",
        "rsi": 55.0,
        "ema20": 99.0,
        "ema50": 98.0,
        "ema200": 97.0,
        "vwap": 99.0,
        "volume": 1000,
        "avg_volume": 800,
        "day_high": 100.5,
        "sector": "IT",
        "support": 99.0,
        "resistance": 101.9,
    }

    monkeypatch.setattr(
        market_router.market_data_service,
        "get_opportunities",
        lambda: MarketDataResult(
            data=[{"symbol": "INFY", "reason": "seed"}],
            metadata=metadata,
        ),
    )
    monkeypatch.setattr(
        market_router.market_data_service,
        "get_stock",
        lambda symbol: MarketDataResult(data={**stock, "symbol": symbol}, metadata=metadata),
    )

    expected = real_decide(stock)
    rows = market_router.opportunities()
    assert len(rows) == 1
    assert expected.recommendation is not None
    assert rows[0].action == expected.recommendation.action
    assert rows[0].strategy == expected.recommendation.strategy


@pytest.mark.parametrize(
    "label,fixture,action,strategy",
    [
        ("Eicher", EICHER, "Watch", "Breakout"),
        ("Maruti", MARUTI, "Watch", "Breakout"),
        ("Bharti", BHARTI, "Watch", "Pullback"),
        ("Tata Motors", TATA, "Avoid", "No Entry Yet"),
    ],
)
def test_opportunities_cross_stock_authority_via_decide(
    label, fixture, action, strategy, monkeypatch
):
    """Ranking action/strategy mirror decide() for conceptual cross-stock shapes."""
    from datetime import datetime, timezone

    from routers import market as market_router
    from services.market_data_service import MarketDataMetadata, MarketDataResult
    from services.stock_decision import StockDecision

    metadata = MarketDataMetadata(
        provider="seed",
        cached=False,
        as_of=datetime.now(timezone.utc),
        market_status="OPEN",
    )
    recommendation = engine.recommend(fixture)
    assert recommendation.action == action, label
    assert recommendation.strategy == strategy, label

    stock = {
        "symbol": fixture.symbol,
        "name": label,
        "price": fixture.price,
        "changePct": 0.0,
        "score": 50,
        "trend": "bullish",
        "rsi": fixture.rsi or 50.0,
        "ema20": fixture.ema20,
        "ema50": fixture.ema50,
        "ema200": fixture.ema200,
        "vwap": fixture.price,
        "volume": 1000,
        "avg_volume": 800,
        "day_high": fixture.price,
        "sector": "Test",
        "support": fixture.support,
        "resistance": fixture.resistance,
    }

    monkeypatch.setattr(
        market_router.market_data_service,
        "get_opportunities",
        lambda: MarketDataResult(
            data=[{"symbol": fixture.symbol, "reason": "seed"}],
            metadata=metadata,
        ),
    )
    monkeypatch.setattr(
        market_router.market_data_service,
        "get_stock",
        lambda symbol: MarketDataResult(data={**stock, "symbol": symbol}, metadata=metadata),
    )
    monkeypatch.setattr(
        market_router,
        "decide",
        lambda snapshot, insight=None: StockDecision(
            recommendation=recommendation,
            trend=recommendation.trend,
            score=recommendation.score,
        ),
    )

    row = market_router.opportunities()[0]
    assert row.action == action, label
    assert row.strategy == strategy, label
