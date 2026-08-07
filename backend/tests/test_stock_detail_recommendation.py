"""Offline tests for the additive `recommendation` block on GET /stock/{symbol}.

The endpoint function is called directly with a seed-backed service, so these
tests need no network, no database and no running server.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

import routers.market as market_router
from services.market_data_service import MarketDataService
from services.providers.seed_provider import SeedProvider
from services.stock_decision import decide


@pytest.fixture
def seeded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve the endpoint from the deterministic seed provider only."""
    service = MarketDataService(
        primary_provider=SeedProvider(), fallback_provider=SeedProvider()
    )
    monkeypatch.setattr(market_router, "market_data_service", service)


def _detail(symbol: str = "RELIANCE") -> Dict[str, Any]:
    return market_router.stock_detail(symbol).model_dump()


def test_existing_contract_is_unchanged(seeded: None) -> None:
    payload = _detail()

    # Every field the endpoint served before the recommendation engine landed.
    expected = {
        "symbol", "name", "price", "changePct", "score", "trend", "rsi", "ema20",
        "vwap", "volume", "sector", "support", "resistance", "aiInsight",
        "series", "strengthScore", "stars", "classification", "tradeSetup",
        "riskLevel", "suggestedAction", "insight",
        "provider", "cached", "asOf", "marketStatus",
    }

    assert expected <= payload.keys()
    assert payload.keys() - expected == {"recommendation"}
    assert payload["symbol"] == "RELIANCE"
    assert payload["series"]


def test_recommendation_block_is_camel_cased_and_populated(seeded: None) -> None:
    recommendation = _detail()["recommendation"]

    assert recommendation is not None
    v1_fields = {
        "action", "conviction", "score", "trend", "confidence", "dataQuality",
        "holdingPeriod", "entryCondition", "rationale", "rulesMatched",
        "warnings", "levels",
    }
    v1_1_fields = {
        "strategy", "verdict", "summary", "why", "positives", "risks",
        "nextTrigger", "beginnerTip", "idealFor",
    }
    mentor_fields = {"setup", "progress"}

    assert recommendation.keys() == v1_fields | v1_1_fields | mentor_fields
    assert recommendation["setup"] is not None
    assert recommendation["progress"] is not None
    assert recommendation["setup"]["structureKey"]
    assert recommendation["progress"]["nextEvent"] == recommendation["nextTrigger"]
    assert recommendation["action"] in {
        "Strong Buy", "Buy", "Watch", "Wait", "Avoid"
    }
    assert recommendation["strategy"] in {
        "Trend Continuation", "Pullback", "Breakout", "Consolidation", "No Entry Yet"
    }
    assert 0 < recommendation["confidence"] < 1
    assert recommendation["holdingPeriod"]
    assert recommendation["entryCondition"]
    if recommendation["levels"] is not None:
        assert recommendation["levels"].keys() == {
            "entryMin", "entryMax", "stopLoss", "target1", "target2", "riskReward"
        }


def test_recommendation_answers_the_five_beginner_questions(seeded: None) -> None:
    recommendation = _detail()["recommendation"]

    assert recommendation["verdict"]
    assert recommendation["summary"]
    assert recommendation["why"]
    assert recommendation["risks"]
    assert recommendation["nextTrigger"]
    assert recommendation["beginnerTip"]
    assert recommendation["idealFor"]
    # The legacy alias must keep rendering the same text as `summary`.
    assert recommendation["rationale"] == recommendation["summary"]


def test_holding_period_is_a_trade_duration_not_a_status(seeded: None) -> None:
    assert _detail()["recommendation"]["holdingPeriod"] not in {
        "Wait", "No Trade", "Existing Holders"
    }


def test_legacy_analysis_fields_do_not_influence_the_recommendation(
    seeded: None,
) -> None:
    """`suggestedAction` and friends stay on the payload but decide nothing."""
    payload = _detail()
    assert payload["suggestedAction"] and payload["classification"]

    snapshot = {
        "symbol": "RELIANCE",
        "price": 110.0,
        "ema20": 105.0,
        "ema50": 100.0,
        "ema200": 90.0,
        "rsi": 60.0,
        "support": 100.0,
        "resistance": 120.0,
    }
    legacy = {
        "suggestedAction": "Exit",
        "classification": "Avoid",
        "insight": "Seeded insight text.",
        "score": 3,
        "trend": "bearish",
    }

    clean = decide(snapshot, {}).recommendation
    contaminated = decide({**snapshot, **legacy}, {}).recommendation

    assert clean == contaminated
    assert clean is not None and clean.action == "Strong Buy"


def test_recommendation_ignores_the_seeded_score_and_trend(seeded: None) -> None:
    """The engine re-derives both from live indicators; seeds must not leak."""
    recommendation = _detail()["recommendation"]

    # Seed EMA50/EMA200 are absent, so the engine can never award full marks.
    assert recommendation["score"] <= 75


def test_partial_indicator_set_is_reported_not_silently_degraded(
    seeded: None,
) -> None:
    recommendation = _detail()["recommendation"]

    assert recommendation["dataQuality"] == "Partial"
    assert recommendation["confidence"] < 1.0
    assert any(
        w.startswith("partial_data:")
        and "EMA50" in w
        and "incomplete indicator set" in w
        for w in recommendation["warnings"]
    )


@pytest.mark.parametrize(
    "snapshot",
    [
        {"symbol": "RELIANCE"},
        {"symbol": "RELIANCE", "price": None},
        {"price": 100.0},
    ],
)
def test_unusable_snapshot_yields_no_block_instead_of_raising(snapshot: dict) -> None:
    """A snapshot without a numeric price must not break the response."""
    decision = decide(snapshot, {})

    assert decision.recommendation is None
    # The parent payload then publishes no direction rather than a guessed one.
    assert (decision.trend, decision.score) == ("neutral", 0)


def test_unknown_symbol_still_returns_404(seeded: None) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        market_router.stock_detail("NOSUCHSYMBOL")

    assert excinfo.value.status_code == 404
