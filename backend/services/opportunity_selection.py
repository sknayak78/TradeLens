"""Opportunity selection from the screened market universe.

Today's Opportunities is built from the broader STOCKS catalogue after
candidate screening, not from the legacy 10-symbol OPPORTUNITIES list.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from analysis.service import service as analysis_service
from services.market_data.screening import ScreeningSummary, screen_candidates
from services.market_data.universe import default_universe
from services.market_data_service import MarketDataResult, MarketDataService
from services.stock_decision import decide

logger = logging.getLogger("tradelens.opportunity_selection")

MAX_OPPORTUNITY_ROWS = 10


@dataclass(frozen=True)
class OpportunityRow:
    symbol: str
    name: str
    price: float
    change_pct: float
    trend: str
    analysis: Any
    reason: str


@dataclass(frozen=True)
class OpportunitySelectionResult:
    screening: ScreeningSummary
    analysed_count: int
    rows: tuple[OpportunityRow, ...]

    @property
    def returned_count(self) -> int:
        return len(self.rows)


def select_opportunities(
    market_data_service: MarketDataService,
    *,
    legacy_reasons: dict[str, str] | None = None,
    max_rows: int = MAX_OPPORTUNITY_ROWS,
) -> tuple[OpportunitySelectionResult, dict[str, Any]]:
    """Screen, analyse, and rank candidates for Today's Opportunities."""
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
            OpportunitySelectionResult(screening=screening, analysed_count=0, rows=()),
            universe_result.metadata.to_api_dict(),
        )

    candidate_rows: list[dict[str, Any]] = []
    for stock in screening.eligible:
        symbol = stock["symbol"]
        stock_result = market_data_service.get_stock(symbol)
        snapshot = stock_result.data
        if not snapshot:
            continue

        analysis = analysis_service.analyse(snapshot)
        candidate_rows.append({
            "symbol": symbol,
            "name": snapshot["name"],
            "price": snapshot["price"],
            "changePct": snapshot["changePct"],
            "trend": decide(snapshot).trend,
            "analysis": analysis,
        })

    candidate_rows.sort(
        key=lambda row: (row["analysis"].strength_score, row["price"]),
        reverse=True,
    )
    candidate_rows = candidate_rows[:max_rows]

    rows = tuple(
        OpportunityRow(
            symbol=row["symbol"],
            name=row["name"],
            price=row["price"],
            change_pct=row["changePct"],
            trend=row["trend"],
            analysis=row["analysis"],
            reason=reasons.get(
                row["symbol"],
                row["analysis"].classification + " — " + row["analysis"].trade_setup,
            ),
        )
        for row in candidate_rows
    )

    return (
        OpportunitySelectionResult(
            screening=screening,
            analysed_count=len(screening.eligible),
            rows=rows,
        ),
        universe_result.metadata.to_api_dict(),
    )
