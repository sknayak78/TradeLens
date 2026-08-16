"""ER-0024: Mentor-action featured opportunity ranking tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

import routers.market as market_router
from recommendation.config import ACTIONS
from recommendation.models import Recommendation
from services.opportunity_selection import (
    EvaluatedCandidate,
    MAX_OPPORTUNITY_ROWS,
    select_featured_candidates,
    select_opportunities,
)
from services.stock_decision import StockDecision
from tests.test_single_source_of_truth import SNAPSHOTS, STALE_METADATA, _RowProvider


def _analysis(strength_score: int) -> Any:
    analysis = MagicMock()
    analysis.strength_score = strength_score
    analysis.stars = 3
    analysis.classification = "Watch"
    analysis.trade_setup = "Momentum"
    analysis.risk_level = "Medium"
    analysis.suggested_action = "Watch"
    analysis.insight = "test"
    return analysis


def _recommendation(action: str, score: int, symbol: str) -> Recommendation:
    return Recommendation(
        symbol=symbol,
        action=action,  # type: ignore[arg-type]
        strategy="Pullback",
        verdict="test",
        summary="test",
        conviction="Medium",
        score=score,
        trend="bullish",
        confidence=0.8,
        data_quality="Complete",
        holding_period="intraday",
        next_trigger="test",
        beginner_tip="test",
        ideal_for="test",
        why=["test"],
        positives=["test"],
        risks=["test"],
        entry_condition="test",
        rationale="test",
        rules_matched=["test"],
        warnings=[],
        levels=None,
    )


def _candidate(
    symbol: str,
    *,
    action: str,
    recommendation_score: int,
    strength_score: int,
) -> EvaluatedCandidate:
    decision = StockDecision(
        recommendation=_recommendation(action, recommendation_score, symbol),
        trend="bullish",
        score=recommendation_score,
    )
    return EvaluatedCandidate(
        symbol=symbol,
        name=symbol,
        price=100.0,
        change_pct=1.0,
        trend="bullish",
        action=action,
        recommendation_score=recommendation_score,
        analysis=_analysis(strength_score),
        decision=decision,
        reason="test",
    )


def test_buy_with_lower_strength_score_is_not_hidden_by_watch():
    candidates = [
        _candidate("ICICIBANK", action="Buy", recommendation_score=85, strength_score=65),
        *[
            _candidate(f"WATCH{i}", action="Watch", recommendation_score=100 - i, strength_score=95 - i)
            for i in range(12)
        ],
    ]

    featured = select_featured_candidates(candidates, max_rows=10)
    symbols = [row.symbol for row in featured]

    assert "ICICIBANK" in symbols
    assert len(featured) == 10


def test_strong_buy_is_surfaced_when_present():
    candidates = [
        _candidate("SB1", action="Strong Buy", recommendation_score=90, strength_score=50),
        *[
            _candidate(f"W{i}", action="Watch", recommendation_score=99 - i, strength_score=99 - i)
            for i in range(9)
        ],
    ]

    featured = select_featured_candidates(candidates, max_rows=10)

    assert featured[0].symbol == "SB1"
    assert featured[0].action == "Strong Buy"


def test_buy_is_surfaced_when_present():
    candidates = [
        _candidate("BUY1", action="Buy", recommendation_score=80, strength_score=40),
        *[
            _candidate(f"W{i}", action="Watch", recommendation_score=95 - i, strength_score=95 - i)
            for i in range(9)
        ],
    ]

    featured = select_featured_candidates(candidates, max_rows=10)
    actions = {row.symbol: row.action for row in featured}

    assert actions["BUY1"] == "Buy"


def test_empty_buy_buckets_do_not_create_fake_rows():
    candidates = [
        _candidate(f"W{i}", action="Watch", recommendation_score=90 - i, strength_score=80 - i)
        for i in range(8)
    ]

    featured = select_featured_candidates(candidates, max_rows=10)

    assert len(featured) == 8
    assert all(row.action == "Watch" for row in featured)


def test_wait_and_avoid_candidates_remain_valid_in_featured_pool():
    candidates = [
        _candidate("WAIT1", action="Wait", recommendation_score=70, strength_score=30),
        _candidate("AVOID1", action="Avoid", recommendation_score=60, strength_score=20),
        _candidate("WATCH1", action="Watch", recommendation_score=90, strength_score=85),
    ]

    featured = select_featured_candidates(candidates, max_rows=3)
    actions = {row.action for row in featured}

    assert actions == {"Watch", "Wait", "Avoid"}


def test_bucket_ordering_uses_recommendation_score():
    candidates = [
        _candidate("W_LOW", action="Watch", recommendation_score=70, strength_score=99),
        _candidate("W_HIGH", action="Watch", recommendation_score=95, strength_score=10),
    ]

    featured = select_featured_candidates(candidates, max_rows=2)

    assert [row.symbol for row in featured] == ["W_HIGH", "W_LOW"]


def test_deterministic_tie_ordering_uses_symbol():
    candidates = [
        _candidate("BBB", action="Watch", recommendation_score=80, strength_score=80),
        _candidate("AAA", action="Watch", recommendation_score=80, strength_score=80),
    ]

    featured = select_featured_candidates(candidates, max_rows=2)

    assert [row.symbol for row in featured] == ["AAA", "BBB"]


def test_featured_rows_remain_capped_at_ten():
    candidates = [
        _candidate(f"S{i}", action="Watch", recommendation_score=90 - i, strength_score=90 - i)
        for i in range(20)
    ]

    featured = select_featured_candidates(candidates, max_rows=MAX_OPPORTUNITY_ROWS)

    assert len(featured) == 10


def test_action_counts_match_eligible_distribution():
    provider = __import__(
        "services.providers.seed_provider", fromlist=["SeedProvider"]
    ).SeedProvider
    service = __import__(
        "services.market_data_service", fromlist=["MarketDataService"]
    ).MarketDataService(provider(), provider())

    selection, _ = select_opportunities(service)

    assert sum(selection.action_counts.values()) == selection.analysed_count
    assert set(selection.action_counts.keys()) == set(ACTIONS)


def test_api_response_includes_rankings_action_counts_and_recommendation(served):
    served("Buy")
    payload = market_router.opportunities()

    assert len(payload.rankings) <= 10
    assert payload.actionCounts
    assert sum(payload.actionCounts.values()) >= len(payload.rankings)
    assert payload.rankings[0].recommendation is not None
    assert payload.rankings[0].recommendation.action == "Buy"


def test_er_0021_authority_trend_and_score_on_featured_rows(served):
    served("Watch")
    payload = market_router.opportunities()
    row = payload.rankings[0]

    assert row.trend == row.recommendation.trend
    assert row.recommendation.action == "Watch"


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch):
    def _serve(action: str) -> None:
        row = {
            "symbol": "RELIANCE",
            "name": "Reliance Industries",
            "changePct": 1.24,
            "volume": 4_820_000,
            "avg_volume": 4_097_000,
            "day_high": SNAPSHOTS[action]["price"],
            "sector": "Energy",
            **STALE_METADATA,
            **SNAPSHOTS[action],
        }
        provider = _RowProvider(row)
        service = __import__(
            "services.market_data_service", fromlist=["MarketDataService"]
        ).MarketDataService(primary_provider=provider, fallback_provider=provider)
        monkeypatch.setattr(market_router, "market_data_service", service)

    return _serve
