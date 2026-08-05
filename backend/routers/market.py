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
from recommendation.engine import engine as recommendation_engine
from recommendation.models import RecommendationInput
from services.market_data_service import market_data_service

logger = logging.getLogger("tradelens.market")

router = APIRouter(tags=["market"])


def _recommendation(
    stock: Dict[str, Any], insight: Dict[str, Any]
) -> Optional[RecommendationOut]:
    """Map the pure engine's output onto the API model.

    Returns ``None`` when the live snapshot cannot even be read, so the rest of
    the response is never at risk.
    """
    try:
        market = RecommendationInput.from_snapshot(stock, insight)
    except (KeyError, ValueError):
        logger.warning(
            "market.recommendation_skipped_unusable_snapshot", exc_info=True
        )
        return None

    recommendation = recommendation_engine.recommend(market)
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
            trend=s["trend"],
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
    """Today's Rankings — analysis-driven leaderboard.

    Every stock is analysed by StockAnalysisService; rows are sorted by
    strength score descending and re-ranked. Curated 'reason' strings from
    the seed keep the human context.
    """
    opportunity_result = market_data_service.get_opportunities()
    reason_by_symbol = {
        o["symbol"]: o["reason"] for o in opportunity_result.data
    }
    metadata = opportunity_result.metadata.to_api_dict()

    rows: List[dict] = []
    for opportunity in opportunity_result.data:
        symbol = opportunity["symbol"]
        stock_result = market_data_service.get_stock(symbol)
        stock = stock_result.data
        if not stock:
            continue

        analysis = analysis_service.analyse(stock)
        rows.append({
            "symbol": symbol,
            "name": stock["name"],
            "price": stock["price"],
            "changePct": stock["changePct"],
            "trend": stock["trend"],
            "analysis": analysis,
        })

    rows.sort(
        key=lambda r: (r["analysis"].strength_score, r["price"]),
        reverse=True,
    )
    rows = rows[:10]

    result: List[Ranking] = []
    for idx, r in enumerate(rows, start=1):
        a = r["analysis"]
        reason = reason_by_symbol.get(
            r["symbol"],
            a.classification + " — " + a.trade_setup,
        )
        result.append(Ranking(
            **metadata,
            rank=idx,
            symbol=r["symbol"],
            name=r["name"],
            price=r["price"],
            changePct=r["changePct"],
            strengthScore=a.strength_score,
            stars=a.stars,
            classification=a.classification,
            trend=a.trend,
            tradeSetup=a.trade_setup,
            riskLevel=a.risk_level,
            suggestedAction=a.suggested_action,
            insight=a.insight,
            reason=reason,
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

    return StockDetail(
        **stock_result.metadata.to_api_dict(),
        symbol=stock["symbol"],
        name=stock["name"],
        price=stock["price"],
        changePct=stock["changePct"],
        score=stock["score"],
        trend=stock["trend"],
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
        recommendation=_recommendation(stock, insight),
    )
