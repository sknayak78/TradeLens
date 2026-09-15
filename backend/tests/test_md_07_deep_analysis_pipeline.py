"""Deterministic MD-07 ranked-candidate deep-analysis pipeline tests."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from services.deep_analysis_pipeline import (
    DeepAnalysisPipeline,
    DeepAnalysisResult,
    ExistingTechnicalAnalyzer,
    RankedCandidate,
)
from services.market_data_service import MarketDataMetadata, MarketDataResult
from services.market_scanner import ScreeningResult
from services.opportunity_explainer import OpportunityExplanation
from services.opportunity_ranker import OpportunityRanker
from services.providers.seed_provider import SeedProvider
from services.stock_decision import StockDecision


def _candidate(symbol: str, rank: int, *, passed: bool = True) -> RankedCandidate:
    scanner_result = ScreeningResult(
        symbol=symbol,
        instrument_key=f"NSE_EQ|{symbol}",
        passed=passed,
        score=80 if passed else 0,
        signals={"trend": True, "momentum": True},
        provider="upstox",
    )
    ranking_input = scanner_result if passed else ScreeningResult(
        symbol=scanner_result.symbol,
        instrument_key=scanner_result.instrument_key,
        passed=True,
        score=80,
        signals=scanner_result.signals,
        provider=scanner_result.provider,
    )
    ranked = OpportunityRanker().rank([ranking_input]).opportunities[0]
    # Ranker assigns rank 1 for a single candidate; preserve the fixture's
    # requested rank to test that MD-07 does not re-rank.
    ranked = type(ranked)(
        rank=rank,
        symbol=ranked.symbol,
        instrument_key=ranked.instrument_key,
        overall_score=ranked.overall_score,
        available_weight=ranked.available_weight,
        component_scores=ranked.component_scores,
        weighted_components=ranked.weighted_components,
        strengths=ranked.strengths,
        cautions=ranked.cautions,
        provider=ranked.provider,
        scanner_result=scanner_result,
    )
    explanation = OpportunityExplanation(
        symbol=symbol,
        rank=rank,
        opportunity_score=ranked.opportunity_score,
        priority="High analysis priority",
        summary="High analysis priority based on technical evidence.",
        strengths=("EMA trend alignment",),
        cautions=(),
        score_breakdown={},
        signal_evidence={},
        ranking_factors=("trend_signal",),
        provider="upstox",
    )
    return RankedCandidate(ranked=ranked, explanation=explanation)


def _deep_result(symbol: str, action: str = "Wait") -> DeepAnalysisResult:
    return DeepAnalysisResult(
        snapshot={"symbol": symbol},
        insight={"support": 1.0, "resistance": 2.0},
        legacy_analysis=SimpleNamespace(symbol=symbol),
        decision=StockDecision(
            recommendation=SimpleNamespace(action=action),
            trend="neutral",
            score=0,
        ),
        snapshot_provider="upstox",
        insight_provider="upstox",
    )


def test_top_n_processes_only_the_requested_number_in_rank_order() -> None:
    calls: list[str] = []
    pipeline = DeepAnalysisPipeline(analyzer=lambda symbol: calls.append(symbol) or _deep_result(symbol))
    candidates = [_candidate(f"S{i:04d}", i + 1) for i in range(2656)]

    results = pipeline.analyze_top_n(candidates, limit=20)

    assert len(results) == 20
    assert len(calls) == 20
    assert calls == [f"S{i:04d}" for i in range(20)]
    assert [result.ranked.rank for result in results] == list(range(1, 21))


def test_default_limit_is_twenty_and_fewer_candidates_are_all_processed() -> None:
    calls: list[str] = []
    pipeline = DeepAnalysisPipeline(analyzer=lambda symbol: calls.append(symbol) or _deep_result(symbol))

    results = pipeline.analyze_top_n([_candidate("VOLTAS", 1), _candidate("PIDILITIND", 2)])

    assert len(results) == 2
    assert calls == ["VOLTAS", "PIDILITIND"]


def test_rejected_and_duplicate_candidates_do_not_trigger_duplicate_analysis() -> None:
    calls: list[str] = []
    pipeline = DeepAnalysisPipeline(analyzer=lambda symbol: calls.append(symbol) or _deep_result(symbol))

    results = pipeline.analyze_top_n([
        _candidate("REJECTED", 1, passed=False),
        _candidate("VOLTAS", 2),
        _candidate("VOLTAS", 2),
        _candidate("PIDILITIND", 3),
    ])

    assert calls == ["VOLTAS", "PIDILITIND"]
    assert [result.ranked.symbol for result in results] == ["VOLTAS", "PIDILITIND"]


def test_failure_isolated_and_rank_order_preserved() -> None:
    calls: list[str] = []

    def analyze(symbol: str) -> DeepAnalysisResult:
        calls.append(symbol)
        if symbol == "BROKEN":
            raise RuntimeError("deep analysis unavailable")
        return _deep_result(symbol)

    results = DeepAnalysisPipeline(analyzer=analyze).analyze_top_n([
        _candidate("VOLTAS", 1),
        _candidate("BROKEN", 2),
        _candidate("PIDILITIND", 3),
    ])

    assert calls == ["VOLTAS", "BROKEN", "PIDILITIND"]
    assert [result.ranked.rank for result in results] == [1, 2, 3]
    assert results[0].deep_analysis is not None
    assert results[1].deep_analysis is None
    assert results[1].error == "deep analysis unavailable"
    assert results[2].deep_analysis is not None


def test_high_priority_candidate_can_preserve_wait_or_avoid_recommendation() -> None:
    actions = ["Wait", "Avoid"]
    for action in actions:
        result = DeepAnalysisPipeline(
            analyzer=lambda symbol, action=action: _deep_result(symbol, action)
        ).analyze_top_n([_candidate("VOLTAS", 1)])[0]

        assert result.ranked.opportunity_score == 100.0
        assert result.deep_analysis.decision.recommendation.action == action


def test_explanation_and_provenance_are_preserved() -> None:
    candidate = _candidate("PIDILITIND", 4)
    result = DeepAnalysisPipeline(analyzer=lambda symbol: _deep_result(symbol)).analyze_top_n([candidate])[0]

    assert result.explanation is candidate.explanation
    assert result.deep_analysis.snapshot_provider == "upstox"
    assert result.deep_analysis.insight_provider == "upstox"


def test_existing_technical_analyzer_delegates_through_market_data_service() -> None:
    seed = SeedProvider()
    metadata = MarketDataMetadata("seed", False, datetime.now(timezone.utc), "CLOSED")

    class Service:
        def get_stock(self, symbol: str):
            return MarketDataResult(seed.get_stock(symbol), metadata)

        def get_stock_insight(self, symbol: str):
            return MarketDataResult(seed.get_stock_insight(symbol), metadata)

    result = ExistingTechnicalAnalyzer(Service()).analyze("RELIANCE")  # type: ignore[arg-type]

    assert result.snapshot["symbol"] == "RELIANCE"
    assert result.snapshot_provider == "seed"
    assert result.decision.recommendation is not None


def test_empty_and_invalid_limits() -> None:
    pipeline = DeepAnalysisPipeline(analyzer=lambda symbol: _deep_result(symbol))

    assert pipeline.analyze_top_n([]) == ()
    assert pipeline.analyze_top_n([_candidate("VOLTAS", 1)], limit=0) == ()
    with pytest.raises(ValueError):
        pipeline.analyze_top_n([], limit=-1)
