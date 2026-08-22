"""Market-data endpoints backed by the cached provider service."""
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from schemas import (
    MarketSummary,
    IndexItem,
    RecommendationLevels,
    RecommendationOut,
    TodaysFocusItem,
    Ranking,
    OpportunitiesResponse,
    StockDetail,
    StockSummary,
    SeriesPoint,
    DayRangeOut,
)
from analysis.service import service as analysis_service
from recommendation.models import Recommendation
from services.chart_series import build_chart_series, get_day_ohlc_range
from services.chart_timeframe import normalize_timeframe
from services.market_data_service import market_data_service
from services.opportunity_selection import select_opportunities
from services.stock_decision import decide

logger = logging.getLogger("tradelens.market")

# Short-lived response cache so repeated Dashboard loads do not re-enrich the universe.
_OPPORTUNITIES_CACHE_TTL_SECONDS = 30.0
_opportunities_cache: dict[str, Any] = {"expires_at": 0.0, "response": None}

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


def clear_opportunities_cache() -> None:
    """Reset the short-lived opportunities response cache (for tests)."""
    _opportunities_cache["response"] = None
    _opportunities_cache["expires_at"] = 0.0


@router.get("/opportunities", response_model=OpportunitiesResponse)
def opportunities() -> OpportunitiesResponse:
    """Today's Rankings — featured rows from the screened market universe.

    Candidates are drawn from the configured STOCKS catalogue, filtered by
  screening, evaluated by the Mentor Engine, bucketed by
  ``recommendation.action``, and featured by ``recommendation.score``.
    """
    now = time.monotonic()
    cached = _opportunities_cache.get("response")
    if cached is not None and now < _opportunities_cache["expires_at"]:
        logger.debug("market.opportunities.cache_hit")
        return cached

    started = time.perf_counter()
    selection, metadata = select_opportunities(market_data_service)

    rankings: List[Ranking] = []
    for idx, row in enumerate(selection.rows, start=1):
        analysis = row.analysis
        rankings.append(Ranking(
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
            recommendation=(
                None
                if row.recommendation is None
                else _recommendation_out(row.recommendation)
            ),
        ))

    response = OpportunitiesResponse(
        **metadata,
        rankings=rankings,
        actionCounts=selection.action_counts,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "market.opportunities built rows=%s elapsed_ms=%.1f cached=false",
        len(rankings),
        elapsed_ms,
    )
    _opportunities_cache["response"] = response
    _opportunities_cache["expires_at"] = now + _OPPORTUNITIES_CACHE_TTL_SECONDS
    return response


@router.get("/stock/{symbol}", response_model=StockDetail)
def stock_detail(symbol: str, timeframe: str = "1W") -> StockDetail:
    symbol = symbol.strip().upper()
    normalized_timeframe = normalize_timeframe(timeframe)
    stock_result = market_data_service.get_stock(symbol)
    stock = stock_result.data
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    insight = market_data_service.get_stock_insight(symbol).data
    analysis = analysis_service.analyse(stock)
    decision = decide(stock, insight)

    try:
        series, timeframe_label, timeframe_fallback = build_chart_series(
            market_data_service,
            symbol,
            normalized_timeframe,
        )
    except Exception as exc:
        logger.warning(
            "market.stock_detail.chart_series_failed symbol=%s timeframe=%s",
            symbol,
            normalized_timeframe,
            exc_info=True,
        )
        series = insight.get("series", [])
        timeframe_label = "Recent"
        timeframe_fallback = True

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
        series=[SeriesPoint(**p) for p in series],
        timeframe=normalized_timeframe,
        timeframeLabel=timeframe_label,
        timeframeFallback=timeframe_fallback,
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


@router.get("/stock/{symbol}/day-range", response_model=DayRangeOut)
def stock_day_range(symbol: str, date: str) -> DayRangeOut:
    symbol = symbol.strip().upper()
    try:
        trade_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from exc

    stock = market_data_service.get_stock(symbol).data
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    payload = get_day_ohlc_range(market_data_service, symbol, trade_date)
    return DayRangeOut(**payload)
