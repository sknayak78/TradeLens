"""Deterministic MD-05 opportunity-ranking tests."""
from __future__ import annotations

import pytest

from services.market_scanner import ScreeningResult
from services.opportunity_ranker import OpportunityRanker


def _candidate(
    symbol: str,
    *,
    signals: dict[str, bool] | None = None,
    passed: bool = True,
    instrument_key: str | None = None,
    provider: str = "upstox",
) -> ScreeningResult:
    return ScreeningResult(
        symbol=symbol,
        instrument_key=instrument_key or f"NSE_EQ|{symbol}",
        passed=passed,
        score=80 if passed else 0,
        signals=signals if signals is not None else {
            "trend": True,
            "momentum": True,
            "liquidity": True,
            "support_resistance": True,
            "breakout_breakdown": True,
            "volatility": True,
            "technical": True,
        },
        provider=provider,
    )


def test_basic_ranking_descends_by_weighted_score() -> None:
    strong = _candidate("VOLTAS")
    weak = _candidate("PIDILITIND", signals={
        "trend": False,
        "momentum": False,
        "liquidity": True,
        "support_resistance": True,
        "breakout_breakdown": False,
        "volatility": True,
    })

    result = OpportunityRanker().rank([weak, strong])

    assert [item.symbol for item in result.opportunities] == ["VOLTAS", "PIDILITIND"]
    assert result.opportunities[0].overall_score == 100.0
    assert result.opportunities[1].overall_score == 50.0


@pytest.mark.parametrize("signal", [
    "trend", "momentum", "liquidity", "support_resistance",
    "breakout_breakdown", "volatility",
])
def test_each_available_signal_changes_component_score(signal: str) -> None:
    strong = _candidate("STRONG")
    signals = dict(strong.signals)
    signals[signal] = False
    weak = _candidate("WEAK", signals=signals)

    ranked = OpportunityRanker().rank([strong, weak])

    assert ranked.opportunities[0].symbol == "STRONG"
    assert ranked.opportunities[1].component_scores[{
        "support_resistance": "structure",
        "breakout_breakdown": "breakout",
    }.get(signal, signal)] == 0.0


def test_weighted_score_is_normalized_to_zero_to_hundred() -> None:
    all_false = _candidate("NONE", signals={
        "trend": False,
        "momentum": False,
        "liquidity": False,
        "support_resistance": False,
        "breakout_breakdown": False,
        "volatility": False,
    })
    result = OpportunityRanker().rank([all_false])

    assert result.opportunities[0].overall_score == 0.0
    assert result.opportunities[0].available_weight == 100.0


def test_missing_signal_renormalizes_available_weights() -> None:
    missing_volatility = _candidate("MISSING", signals={
        "trend": True,
        "momentum": True,
        "liquidity": True,
        "support_resistance": True,
        "breakout_breakdown": True,
    })

    opportunity = OpportunityRanker().rank([missing_volatility]).opportunities[0]

    assert opportunity.overall_score == 100.0
    assert opportunity.available_weight == 85.0
    assert opportunity.component_scores["volatility"] is None
    assert "healthy volatility unavailable" in opportunity.cautions


def test_all_components_unavailable_are_not_silently_zeroed() -> None:
    opportunity = OpportunityRanker().rank([
        _candidate("UNKNOWN", signals={}),
    ]).opportunities[0]

    assert opportunity.overall_score is None
    assert opportunity.available_weight == 0.0
    assert len(opportunity.cautions) == 6


def test_ties_use_trend_momentum_then_symbol_deterministically() -> None:
    candidates = [
        _candidate("BBB", signals={"trend": True, "momentum": False}),
        _candidate("AAA", signals={"trend": True, "momentum": False}),
    ]

    first = OpportunityRanker().rank(candidates)
    second = OpportunityRanker().rank(list(reversed(candidates)))

    assert [item.symbol for item in first.opportunities] == ["AAA", "BBB"]
    assert [item.symbol for item in first.opportunities] == [item.symbol for item in second.opportunities]


def test_limit_and_rejected_candidates() -> None:
    candidates = [_candidate(f"S{i:02d}") for i in range(25)]
    candidates.append(_candidate("REJECTED", passed=False))
    ranker = OpportunityRanker()

    assert len(ranker.rank(candidates, limit=20).opportunities) == 20
    assert len(ranker.rank(candidates, limit=100).opportunities) == 25
    assert all(item.symbol != "REJECTED" for item in ranker.rank(candidates).opportunities)
    assert ranker.rank([], limit=20).opportunities == ()


def test_duplicate_symbols_are_deduplicated_deterministically() -> None:
    candidates = [
        _candidate("VOLTAS", instrument_key="NSE_EQ|Z"),
        _candidate("VOLTAS", instrument_key="NSE_EQ|A"),
    ]

    result = OpportunityRanker().rank(candidates)

    assert result.candidate_count == 1
    assert result.opportunities[0].instrument_key == "NSE_EQ|A"


def test_broad_universe_candidates_retain_provenance_and_explanation() -> None:
    result = OpportunityRanker().rank([
        _candidate("VOLTAS"),
        _candidate("PIDILITIND", provider="yahoo_finance"),
    ])

    assert {item.symbol for item in result.opportunities} == {"VOLTAS", "PIDILITIND"}
    assert result.opportunities[0].strengths
    assert result.opportunities[0].scanner_result.symbol == result.opportunities[0].symbol
    assert {item.provider for item in result.opportunities} == {"upstox", "yahoo_finance"}


def test_ranker_does_not_call_market_data_or_recommendation_services() -> None:
    # ScreeningResult is the complete input boundary; no service object is accepted.
    candidate = _candidate("VOLTAS")
    first = OpportunityRanker().rank([candidate])
    second = OpportunityRanker().rank([candidate])

    assert first == second
