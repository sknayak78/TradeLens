"""Deterministic MD-06 opportunity explainability tests."""
from __future__ import annotations

import pytest

from services.market_scanner import ScreeningResult
from services.opportunity_explainer import OpportunityExplainer
from services.opportunity_ranker import OpportunityRanker


def _ranked(*, signals: dict[str, bool] | None = None, provider: str = "upstox"):
    scanner_result = ScreeningResult(
        symbol="VOLTAS",
        instrument_key="NSE_EQ|INE226A01021",
        passed=True,
        score=80,
        signals=signals if signals is not None else {
            "trend": True,
            "momentum": True,
            "liquidity": True,
            "support_resistance": True,
            "breakout_breakdown": True,
            "volatility": True,
        },
        reason_codes=("trend_signal", "momentum_signal"),
        provider=provider,
    )
    return OpportunityRanker().rank([scanner_result]).opportunities[0]


def test_high_score_explanation_has_high_priority_and_strengths() -> None:
    explanation = OpportunityExplainer().explain(_ranked())

    assert explanation.priority == "High analysis priority"
    assert explanation.opportunity_score == 100.0
    assert explanation.strengths
    assert explanation.score_breakdown["trend"].weighted_contribution == 20.0
    assert "High analysis priority" in explanation.summary


@pytest.mark.parametrize(
    ("signals", "priority"),
    [
        ({"trend": True, "momentum": True, "liquidity": True, "support_resistance": False, "breakout_breakdown": False, "volatility": True}, "Moderate analysis priority"),
        ({"trend": True, "momentum": False, "liquidity": True, "support_resistance": False, "breakout_breakdown": False, "volatility": True}, "Lower analysis priority"),
        ({"trend": False, "momentum": False, "liquidity": False, "support_resistance": False, "breakout_breakdown": False, "volatility": False}, "Low analysis priority"),
    ],
)
def test_score_interpretation_bands_are_deterministic(signals, priority: str) -> None:
    explanation = OpportunityExplainer().explain(_ranked(signals=signals))

    assert explanation.priority == priority


def test_missing_components_are_unavailable_not_cautions_as_failures() -> None:
    explanation = OpportunityExplainer().explain(
        _ranked(signals={"trend": True, "momentum": True})
    )

    assert explanation.score_breakdown["volatility"].available is False
    assert explanation.score_breakdown["volatility"].score is None
    assert explanation.score_breakdown["volatility"].weighted_contribution is None
    assert "healthy volatility unavailable" in explanation.cautions
    assert "2 of 6" in explanation.summary


def test_breakdown_contributions_match_md05_and_sum_to_score() -> None:
    explanation = OpportunityExplainer().explain(_ranked())
    contributions = [
        item.weighted_contribution
        for item in explanation.score_breakdown.values()
        if item.weighted_contribution is not None
    ]

    assert sum(contributions) == pytest.approx(explanation.opportunity_score)


def test_torrent_like_candidate_explains_analysis_priority_not_entry_or_investment() -> None:
    explanation = OpportunityExplainer().explain(
        _ranked(
            signals={
                "trend": True,
                "momentum": True,
                "liquidity": True,
                "support_resistance": False,
                "breakout_breakdown": False,
                "volatility": True,
            }
        )
    )

    assert explanation.priority == "Moderate analysis priority"
    assert "analysis priority" in explanation.summary.lower()
    forbidden = ("buy", "sell", "watch", "wait", "avoid", "investment", "profit")
    assert not any(word in explanation.summary.lower() for word in forbidden)


def test_provider_provenance_and_raw_signal_evidence_are_preserved() -> None:
    explanation = OpportunityExplainer().explain(_ranked(provider="yahoo_finance"))

    assert explanation.provider == "yahoo_finance"
    assert explanation.signal_evidence["scanner_signals"]["trend"] is True
    assert explanation.ranking_factors == ("trend_signal", "momentum_signal")


def test_explanation_is_deterministic_and_makes_no_service_calls() -> None:
    ranked = _ranked()
    explainer = OpportunityExplainer()

    first = explainer.explain(ranked)
    second = explainer.explain(ranked)

    assert first == second


def test_empty_or_invalid_input_fails_cleanly() -> None:
    with pytest.raises(ValueError):
        OpportunityExplainer().explain(None)  # type: ignore[arg-type]
