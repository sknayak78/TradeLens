"""Market-data endpoints backed by the cached provider service."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from schemas import (
    MarketSummary,
    IndexItem,
    RecommendationLevels,
    RecommendationOut,
    TodaysFocusItem,
    Ranking,
    StockDetail,
    StockSummary,
    SeriesPoint,
)
from analysis.service import service as analysis_service
from recommendation.models import Recommendation
from services.market_data_service import market_data_service
from services.opportunity_selection import select_opportunities
from services.stock_decision import decide

logger = logging.getLogger("tradelens.market")

router = APIRouter(tags=["market"])


def _recommendation_out(recommendation: Recommendation) -> RecommendationOut:
    """Map the pure engine's output onto the API model."""
    levels = recommendation.levels
    return RecommendationOut(
        action=recommendation.action,
        strategy=recommendation.strategy,
        verdict=recommendation.verdict,
        summary=recommendation.summary,
        conviction=recommendation.conviction,
        score=recommendation.score,
        trend=recommendation.trend,
        confidence=recommendation.confidence,
        dataQuality=recommendation.data_quality,
        holdingPeriod=recommendation.holding_period,
        nextTrigger=recommendation.next_trigger,
        beginnerTip=recommendation.beginner_tip,
        idealFor=recommendation.ideal_for,
        why=recommendation.why,
        positives=recommendation.positives,
        risks=recommendation.risks,
        entryCondition=recommendation.entry_condition,
        rationale=recommendation.rationale,
        rulesMatched=recommendation.rules_matched,
        warnings=recommendation.warnings,
        levels=None if levels is None else RecommendationLevels(
            entryMin=levels.entry_min,
            entryMax=levels.entry_max,
            stopLoss=levels.stop_loss,
            target1=levels.target1,
            target2=levels.target2,
            riskReward=levels.risk_reward,
        ),
    )


@router.get("/stocks", response_model=List[StockSummary])
def list_stocks(q: str = "", limit: int = 20) -> List[StockSummary]:
    """Return the stock catalog. Optional `q` filters by symbol or name."""
    result = market_data_service.search_stocks(q, limit)
    matches = result.data
    metadata = result.metadata.to_api_dict()
    return [
        StockSummary(
            **metadata,
            symbol=s["symbol"],
            name=s["name"],
            price=s["price"],
            changePct=s["changePct"],
            # Derived from the indicators on the row, not the seeded literal.
            trend=decide(s).trend,
            sector=s["sector"],
        )
        for s in matches
    ]


@router.get("/market-summary", response_model=MarketSummary)
def market_summary() -> MarketSummary:
    result = market_data_service.get_market_summary()
    summary = result.data
    return MarketSummary(
        **result.metadata.to_api_dict(),
        indices=[IndexItem(**i) for i in summary["indices"]],
        todaysFocus=[TodaysFocusItem(**f) for f in summary["todaysFocus"]],
        status="open",
    )


@router.get("/opportunities", response_model=List[Ranking])
def opportunities() -> List[Ranking]:
    """Today's Rankings — screened from the broader market universe.

    Candidates are drawn from the configured STOCKS catalogue, filtered by
    data-quality and liquidity screening, then ranked by the existing legacy
    strength score.  The legacy 10-symbol OPPORTUNITIES list supplies reason
    strings when available but no longer limits the candidate pool.
    """
    selection, metadata = select_opportunities(market_data_service)

    result: List[Ranking] = []
    for idx, row in enumerate(selection.rows, start=1):
        analysis = row.analysis
        result.append(Ranking(
            **metadata,
            rank=idx,
            symbol=row.symbol,
            name=row.name,
            price=row.price,
            changePct=row.change_pct,
            strengthScore=analysis.strength_score,
            stars=analysis.stars,
            classification=analysis.classification,
            trend=row.trend,
            tradeSetup=analysis.trade_setup,
            riskLevel=analysis.risk_level,
            suggestedAction=analysis.suggested_action,
            insight=analysis.insight,
            reason=row.reason,
        ))
    return result


@router.get("/stock/{symbol}", response_model=StockDetail)
def stock_detail(symbol: str) -> StockDetail:
    symbol = symbol.strip().upper()
    stock_result = market_data_service.get_stock(symbol)
    stock = stock_result.data
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    insight = market_data_service.get_stock_insight(symbol).data
    analysis = analysis_service.analyse(stock)
    decision = decide(stock, insight)

    return StockDetail(
        **stock_result.metadata.to_api_dict(),
        symbol=stock["symbol"],
        name=stock["name"],
        price=stock["price"],
        changePct=stock["changePct"],
        # Parent trend/score are the recommendation's, never the provider's.
        score=decision.score,
        trend=decision.trend,
        rsi=stock["rsi"],
        ema20=stock["ema20"],
        vwap=stock["vwap"],
        volume=stock["volume"],
        sector=stock["sector"],
        support=insight["support"],
        resistance=insight["resistance"],
        aiInsight=insight["aiInsight"],
        series=[SeriesPoint(**p) for p in insight["series"]],
        strengthScore=analysis.strength_score,
        stars=analysis.stars,
        classification=analysis.classification,
        tradeSetup=analysis.trade_setup,
        riskLevel=analysis.risk_level,
        suggestedAction=analysis.suggested_action,
        insight=analysis.insight,
        recommendation=(
            None
            if decision.recommendation is None
            else _recommendation_out(decision.recommendation)
        ),
    )
