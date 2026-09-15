"""MD-07 orchestration from ranked candidates to existing deep analysis."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from analysis.service import Analysis, service as analysis_service
from services.market_data_service import MarketDataService
from services.opportunity_explainer import OpportunityExplanation
from services.opportunity_ranker import RankedOpportunity
from services.stock_decision import StockDecision, decide

logger = logging.getLogger("tradelens.deep_analysis_pipeline")


@dataclass(frozen=True)
class RankedCandidate:
    """The MD-05 rank and MD-06 explanation carried into deep analysis."""

    ranked: RankedOpportunity
    explanation: OpportunityExplanation


@dataclass(frozen=True)
class DeepAnalysisResult:
    """Existing technical outputs associated with their source provenance."""

    snapshot: dict[str, Any]
    insight: dict[str, Any]
    legacy_analysis: Analysis
    decision: StockDecision
    snapshot_provider: str
    insight_provider: str


@dataclass(frozen=True)
class DiscoveredOpportunity:
    """One ranked candidate and its successful or failed deep-analysis result."""

    ranked: RankedOpportunity
    explanation: OpportunityExplanation
    deep_analysis: DeepAnalysisResult | None
    error: str | None = None


DeepAnalyzer = Callable[[str], DeepAnalysisResult]


class ExistingTechnicalAnalyzer:
    """Adapter to the established snapshot, analysis, and recommendation path."""

    def __init__(self, market_data_service: MarketDataService):
        self._market_data_service = market_data_service

    def analyze(self, symbol: str) -> DeepAnalysisResult:
        snapshot_result = self._market_data_service.get_stock(symbol)
        snapshot = snapshot_result.data
        if not snapshot:
            raise ValueError(f"deep analysis returned no snapshot for {symbol}")

        insight_result = self._market_data_service.get_stock_insight(symbol)
        insight = insight_result.data
        if not insight:
            raise ValueError(f"deep analysis returned no insight for {symbol}")

        legacy_analysis = analysis_service.analyse(snapshot)
        decision = decide(snapshot, insight)
        return DeepAnalysisResult(
            snapshot=snapshot,
            insight=insight,
            legacy_analysis=legacy_analysis,
            decision=decision,
            snapshot_provider=snapshot_result.metadata.provider,
            insight_provider=insight_result.metadata.provider,
        )


class DeepAnalysisPipeline:
    """Analyze only the highest-ranked candidates, sequentially and safely."""

    DEFAULT_LIMIT = 20

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        *,
        analyzer: DeepAnalyzer | None = None,
    ) -> None:
        if analyzer is not None and market_data_service is not None:
            raise ValueError("provide analyzer or market_data_service, not both")
        if analyzer is not None:
            self._analyzer: Any = analyzer
        elif market_data_service is not None:
            self._analyzer = ExistingTechnicalAnalyzer(market_data_service)
        else:
            raise ValueError("deep analysis pipeline requires an analyzer or market_data_service")

    def analyze_top_n(
        self,
        candidates: Sequence[RankedCandidate],
        *,
        limit: int = DEFAULT_LIMIT,
    ) -> tuple[DiscoveredOpportunity, ...]:
        """Analyze candidates in supplied rank order, up to ``limit`` unique symbols."""
        if limit < 0:
            raise ValueError("deep analysis limit must not be negative")

        results: list[DiscoveredOpportunity] = []
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate.ranked.scanner_result.passed:
                continue
            symbol = candidate.ranked.symbol
            if symbol in seen:
                continue
            if len(results) >= limit:
                break
            seen.add(symbol)
            try:
                analysis = self._analyzer(symbol) if callable(self._analyzer) else self._analyzer.analyze(symbol)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning(
                    "deep_analysis_pipeline.failed symbol=%s rank=%s",
                    symbol,
                    candidate.ranked.rank,
                    exc_info=True,
                )
                results.append(
                    DiscoveredOpportunity(
                        ranked=candidate.ranked,
                        explanation=candidate.explanation,
                        deep_analysis=None,
                        error=str(exc),
                    )
                )
                continue

            results.append(
                DiscoveredOpportunity(
                    ranked=candidate.ranked,
                    explanation=candidate.explanation,
                    deep_analysis=analysis,
                )
            )
        return tuple(results)
