"""Single entry point for "what does TradeLens think of this stock?".

Every endpoint that publishes a trend or a score reads it from here, so the
Recommendation Engine is the only authority for those values.  Provider rows
still carry seeded ``trend``/``score`` literals for the deprecated analysis
layer; nothing in this module reads them.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from recommendation.engine import engine as recommendation_engine
from recommendation.models import Recommendation, RecommendationInput, Trend

logger = logging.getLogger("tradelens.stock_decision")

#: Served when the snapshot cannot be scored at all, so the API never publishes
#: a direction it has no evidence for.
UNKNOWN_TREND: Trend = "neutral"
UNKNOWN_SCORE: int = 0


@dataclass(frozen=True)
class StockDecision:
    """The engine's view of one stock, plus the values the parent payload shows.

    ``trend`` and ``score`` mirror ``recommendation`` whenever there is one, and
    that is the point: a caller cannot accidentally publish a parent field that
    disagrees with the recommendation block.
    """

    recommendation: Optional[Recommendation]
    trend: Trend
    score: int


def decide(
    stock: Dict[str, Any], insight: Optional[Dict[str, Any]] = None
) -> StockDecision:
    """Run the Recommendation Engine over a provider snapshot.

    An unusable snapshot degrades to a neutral, zero-score decision with no
    recommendation attached rather than failing the request.
    """
    try:
        market = RecommendationInput.from_snapshot(stock, insight)
    except (KeyError, ValueError):
        logger.warning(
            "stock_decision.unusable_snapshot symbol=%s",
            stock.get("symbol"),
            exc_info=True,
        )
        return StockDecision(
            recommendation=None, trend=UNKNOWN_TREND, score=UNKNOWN_SCORE
        )

    recommendation = recommendation_engine.recommend(market)
    logger.info(
        "stock_decision.decided symbol=%s action=%s trend=%s score=%s",
        recommendation.symbol,
        recommendation.action,
        recommendation.trend,
        recommendation.score,
    )
    return StockDecision(
        recommendation=recommendation,
        trend=recommendation.trend,
        score=recommendation.score,
    )
