"""Opportunity selection from the screened market universe.

Today's Opportunities is built from the broader STOCKS catalogue after
candidate screening.  Featured rows are selected by Mentor
``recommendation.action`` and ranked within each bucket by
``recommendation.score`` (ER-0021 authority).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from analysis.service import service as analysis_service
from recommendation.config import ACTIONS
from recommendation.models import Recommendation
from services.market_data.screening import ScreeningSummary, screen_candidates
from services.market_data.universe import default_universe
from services.market_data_service import MarketDataResult, MarketDataService
from services.stock_decision import StockDecision, decide

logger = logging.getLogger("tradelens.opportunity_selection")

MAX_OPPORTUNITY_ROWS = 10

#: Mentor action priority — lower index means higher selection priority.
ACTION_PRIORITY: tuple[str, ...] = ACTIONS


@dataclass(frozen=True)
class EvaluatedCandidate:
    """One screened, analysed, and Mentor-evaluated instrument."""

    symbol: str
    name: str
    price: float
    change_pct: float
    trend: str
    action: str
    recommendation_score: int
    analysis: Any
    decision: StockDecision
    reason: str

    @property
    def recommendation(self) -> Recommendation | None:
        return self.decision.recommendation


@dataclass(frozen=True)
class OpportunityRow:
    symbol: str
    name: str
    price: float
    change_pct: float
    trend: str
    action: str
    recommendation_score: int
    analysis: Any
    reason: str
    recommendation: Recommendation | None


@dataclass(frozen=True)
class OpportunitySelectionResult:
    screening: ScreeningSummary
    analysed_count: int
    action_counts: dict[str, int]
    rows: tuple[OpportunityRow, ...]

    @property
    def returned_count(self) -> int:
        return len(self.rows)


def _bucket_sort_key(candidate: EvaluatedCandidate) -> tuple[Any, ...]:
    """Primary rank inside an action bucket: recommendation.score, then legacy strength."""
    return (
        -candidate.recommendation_score,
        -candidate.analysis.strength_score,
        candidate.symbol,
    )


def _global_sort_key(candidate: EvaluatedCandidate) -> tuple[Any, ...]:
    """Cross-bucket fill order: action priority, then recommendation.score."""
    try:
        action_rank = ACTION_PRIORITY.index(candidate.action)
    except ValueError:
        action_rank = len(ACTION_PRIORITY)
    return (
        action_rank,
        -candidate.recommendation_score,
        -candidate.analysis.strength_score,
        candidate.symbol,
    )


def select_featured_candidates(
    candidates: list[EvaluatedCandidate],
    *,
    max_rows: int = MAX_OPPORTUNITY_ROWS,
) -> list[EvaluatedCandidate]:
    """Select featured opportunities without hiding genuine Buy/Strong Buy rows.

    Algorithm (deterministic):

    1. Group candidates by ``recommendation.action``.
    2. Sort each bucket by ``recommendation.score`` (desc), then legacy
       ``strength_score`` (desc), then ``symbol`` (asc).
    3. If a Strong Buy bucket is non-empty, include its top row.
    4. If a Buy bucket is non-empty, include its top row.
    5. Fill remaining slots from all unselected candidates sorted by action
       priority, then ``recommendation.score``, then legacy ``strength_score``,
       then ``symbol``.

    No fixed per-category quotas are applied beyond the single-row guarantee
    for non-empty Strong Buy / Buy buckets.
    """
    if not candidates or max_rows <= 0:
        return []

    buckets: dict[str, list[EvaluatedCandidate]] = defaultdict(list)
    for candidate in candidates:
        buckets[candidate.action].append(candidate)

    for action in ACTION_PRIORITY:
        buckets[action].sort(key=_bucket_sort_key)

    featured: list[EvaluatedCandidate] = []
    selected_symbols: set[str] = set()

    def _take(candidate: EvaluatedCandidate) -> None:
        if candidate.symbol in selected_symbols:
            return
        featured.append(candidate)
        selected_symbols.add(candidate.symbol)

    for action in ("Strong Buy", "Buy"):
        if buckets[action] and len(featured) < max_rows:
            _take(buckets[action][0])

    remaining = [c for c in candidates if c.symbol not in selected_symbols]
    remaining.sort(key=_global_sort_key)
    for candidate in remaining:
        if len(featured) >= max_rows:
            break
        _take(candidate)

    return featured


def _empty_action_counts() -> dict[str, int]:
    return {action: 0 for action in ACTION_PRIORITY}


def _count_actions(candidates: list[EvaluatedCandidate]) -> dict[str, int]:
    counts = _empty_action_counts()
    for candidate in candidates:
        counts[candidate.action] = counts.get(candidate.action, 0) + 1
    return counts


def select_opportunities(
    market_data_service: MarketDataService,
    *,
    legacy_reasons: dict[str, str] | None = None,
    max_rows: int = MAX_OPPORTUNITY_ROWS,
) -> tuple[OpportunitySelectionResult, dict[str, Any]]:
    """Screen, analyse, Mentor-decide, and select featured opportunities."""
    reasons = legacy_reasons if legacy_reasons is not None else default_universe.legacy_reasons()
    universe_result: MarketDataResult = market_data_service.get_all_stocks()
    screening = screen_candidates(universe_result.data)

    logger.info(
        "opportunity_selection.screened universe=%s eligible=%s excluded=%s",
        screening.universe_size,
        screening.eligible_count,
        screening.excluded_count,
    )

    if not screening.eligible:
        return (
            OpportunitySelectionResult(
                screening=screening,
                analysed_count=0,
                action_counts=_empty_action_counts(),
                rows=(),
            ),
            universe_result.metadata.to_api_dict(),
        )

    evaluated: list[EvaluatedCandidate] = []
    for stock in screening.eligible:
        symbol = stock["symbol"]
        stock_result = market_data_service.get_stock(symbol)
        snapshot = stock_result.data
        if not snapshot:
            continue

        insight = market_data_service.get_stock_insight(symbol).data
        analysis = analysis_service.analyse(snapshot)
        decision = decide(snapshot, insight)
        if decision.recommendation is None:
            logger.warning(
                "opportunity_selection.skipping_no_recommendation symbol=%s",
                symbol,
            )
            continue

        action = decision.recommendation.action
        evaluated.append(
            EvaluatedCandidate(
                symbol=symbol,
                name=snapshot["name"],
                price=snapshot["price"],
                change_pct=snapshot["changePct"],
                trend=decision.trend,
                action=action,
                recommendation_score=decision.score,
                analysis=analysis,
                decision=decision,
                reason=reasons.get(
                    symbol,
                    analysis.classification + " — " + analysis.trade_setup,
                ),
            )
        )

    action_counts = _count_actions(evaluated)
    featured = select_featured_candidates(evaluated, max_rows=max_rows)

    rows = tuple(
        OpportunityRow(
            symbol=candidate.symbol,
            name=candidate.name,
            price=candidate.price,
            change_pct=candidate.change_pct,
            trend=candidate.trend,
            action=candidate.action,
            recommendation_score=candidate.recommendation_score,
            analysis=candidate.analysis,
            reason=candidate.reason,
            recommendation=candidate.recommendation,
        )
        for candidate in featured
    )

    logger.info(
        "opportunity_selection.featured returned=%s action_counts=%s",
        len(rows),
        action_counts,
    )

    return (
        OpportunitySelectionResult(
            screening=screening,
            analysed_count=len(evaluated),
            action_counts=action_counts,
            rows=rows,
        ),
        universe_result.metadata.to_api_dict(),
    )
