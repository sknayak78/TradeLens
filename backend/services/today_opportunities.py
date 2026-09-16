"""MD-08 composition of the broad discovery pipeline for Today's Opportunities."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Literal

from services.deep_analysis_pipeline import (
    DeepAnalysisPipeline,
    DiscoveredOpportunity,
    RankedCandidate,
)
from services.market_data_service import MarketDataService
from services.market_scanner import MarketScanner, ScanResult
from services.opportunity_explainer import OpportunityExplainer
from services.opportunity_ranker import OpportunityRanker, RankingResult
from services.opportunity_selection import OpportunitySelectionResult, select_opportunities

logger = logging.getLogger("tradelens.today_opportunities")


@dataclass(frozen=True)
class TodayOpportunitiesResult:
    source_mode: Literal["discovery", "curated_fallback", "discovery_failed"]
    scan: ScanResult | None
    ranking: RankingResult | None
    discovered: tuple[DiscoveredOpportunity, ...]
    fallback: OpportunitySelectionResult | None = None
    fallback_metadata: dict[str, Any] | None = None
    error: str | None = None


class TodayOpportunitiesService:
    """Run discovery once and return the ranked/deep-analysed shortlist."""

    DEFAULT_LIMIT = 20
    SCAN_TIMEOUT_SECONDS = 60.0
    FALLBACK_TIMEOUT_SECONDS = 15.0

    def __init__(
        self,
        market_data_service: MarketDataService,
        *,
        fallback_selector: Callable[..., tuple[OpportunitySelectionResult, dict[str, Any]]] = select_opportunities,
        scanner: MarketScanner | None = None,
        ranker: OpportunityRanker | None = None,
        explainer: OpportunityExplainer | None = None,
        deep_analysis: DeepAnalysisPipeline | None = None,
    ):
        self._market_data_service = market_data_service
        self._scanner = scanner or MarketScanner(market_data_service)
        self._ranker = ranker or OpportunityRanker()
        self._explainer = explainer or OpportunityExplainer()
        self._deep_analysis = deep_analysis or DeepAnalysisPipeline(market_data_service)
        self._fallback_selector = fallback_selector

    def run(self, *, limit: int = DEFAULT_LIMIT) -> TodayOpportunitiesResult:
        try:
            scan = self._run_bounded(self._scanner.scan, self.SCAN_TIMEOUT_SECONDS)
            ranking = self._ranker.rank(scan.candidates, limit=limit)
            contexts = tuple(
                RankedCandidate(
                    ranked=ranked,
                    explanation=self._explainer.explain(ranked),
                )
                for ranked in ranking.opportunities
            )
            discovered = self._deep_analysis.analyze_top_n(contexts, limit=limit)
            successful = tuple(item for item in discovered if item.deep_analysis is not None)
            if successful:
                return TodayOpportunitiesResult(
                    source_mode="discovery",
                    scan=scan,
                    ranking=ranking,
                    discovered=discovered,
                )
            return self._curated_fallback(
                scan=scan,
                error="discovery produced no successfully analysed opportunities",
            )
        except TimeoutError:
            return TodayOpportunitiesResult(
                source_mode="discovery_failed",
                scan=None,
                ranking=None,
                discovered=(),
                error="broad-market discovery exceeded its execution deadline",
            )
        except Exception as exc:
            logger.warning("today_opportunities.discovery_failed", exc_info=True)
            return self._curated_fallback(error=str(exc))

    def _curated_fallback(
        self,
        *,
        scan: ScanResult | None = None,
        error: str | None = None,
    ) -> TodayOpportunitiesResult:
        try:
            fallback, metadata = self._run_bounded(
                lambda: self._fallback_selector(self._market_data_service),
                self.FALLBACK_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return TodayOpportunitiesResult(
                source_mode="discovery_failed",
                scan=scan,
                ranking=None,
                discovered=(),
                error="discovery and curated fallback exceeded their execution deadlines",
            )
        return TodayOpportunitiesResult(
            source_mode="curated_fallback",
            scan=scan,
            ranking=None,
            discovered=(),
            fallback=fallback,
            fallback_metadata=metadata,
            error=error,
        )

    @staticmethod
    def _run_bounded(function: Callable[[], Any], timeout: float) -> Any:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(function)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True)
