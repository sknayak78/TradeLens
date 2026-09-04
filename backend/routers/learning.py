"""Learning Journey endpoints (ER-0035).

The Learning Journey is an educational workflow, NOT a trade-entry workflow.
A user studies a supported NSE stock, makes their own decision, and only then
reads the TradeLens Mentor's view for comparison.

The Mentor view is gated behind `reveal=true`, so the Study phase never
receives the `recommendation` payload before the user has submitted their own
decision. This endpoint is intentionally additive and does NOT create trades or
regenerate/handle trade Mentor snapshots.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from schemas import (
    LearningJourneyOut,
    LearningJourneyStudySet,
    RecommendationLevels,
    RecommendationOut,
    SeriesPoint,
)
from recommendation.models import Recommendation
from services.chart_series import build_chart_series
from services.chart_timeframe import normalize_timeframe
from services.market_data_service import market_data_service
from services.stock_decision import decide

logger = logging.getLogger("tradelens.learning")

router = APIRouter(tags=["learning"])


def _recommendation_out(recommendation: Recommendation) -> RecommendationOut:
    """Map the pure engine's output onto the API model (see market router)."""
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


def _latest_series_emas(series: list) -> dict:
    """EMA20/50/200 at the latest displayed candle from the chart series.

    The chart's EMA overlay is the single authoritative EMA source on the Study
    screen: it is warmed over the timeframe's historical lookback (beyond the
    visible window) and sampled per candle. Scans from the last point backwards
    so the latest candle that actually carries a finite EMA wins.
    """
    emas = {"ema20": None, "ema50": None, "ema200": None}
    for point in reversed(series):
        for key in emas:
            value = point.get(key)
            if emas[key] is None and isinstance(value, (int, float)):
                emas[key] = value
        if all(emas.values()):
            break
    return emas


def _is_complete(display_emas: dict, stock: dict) -> bool:
    """True only when every headline indicator the Study screen shows is present.

    `display_emas` already resolves the authoritative chart-series EMA with a
    fallback to the daily `stock` snapshot, so only its presence needs checking.
    RSI and VWAP remain daily snapshot values.
    """
    ema_ok = all(value is not None for value in display_emas.values())
    return ema_ok and stock.get("rsi") is not None and stock.get("vwap") is not None


def _study_set(symbol: str, timeframe: str) -> LearningJourneyStudySet:
    """Build the study evidence for a symbol (never includes the Mentor view)."""
    symbol = symbol.strip().upper()
    normalized_timeframe = normalize_timeframe(timeframe)

    stock_result = market_data_service.get_stock(symbol)
    stock = stock_result.data
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    insight = market_data_service.get_stock_insight(symbol).data
    decision = decide(stock, insight)

    try:
        series, timeframe_label, timeframe_fallback, indicators = build_chart_series(
            market_data_service,
            symbol,
            normalized_timeframe,
        )
    except Exception as exc:
        logger.warning(
            "learning.study_set.chart_series_failed symbol=%s timeframe=%s",
            symbol,
            normalized_timeframe,
            exc_info=True,
        )
        series = insight.get("series", [])
        timeframe_label = "Recent"
        timeframe_fallback = True
        indicators = None

    # EMA authority: the timeframe chart series (warmed over the historical
    # lookback beyond the visible window). The daily `stock` snapshot EMA is used
    # only when the chart series cannot supply a value (e.g. seed/sparse fallback),
    # so the Quick Snapshot always agrees with the latest chart candle it can show.
    series_emas = _latest_series_emas(series)
    display_emas = {
        key: (
            series_emas[key]
            if series_emas[key] is not None
            else stock.get(key)
        )
        for key in ("ema20", "ema50", "ema200")
    }

    return LearningJourneyStudySet(
        **stock_result.metadata.to_api_dict(),
        symbol=stock["symbol"],
        name=stock["name"],
        price=stock["price"],
        changePct=stock["changePct"],
        trend=decision.trend,
        sector=stock.get("sector", ""),
        rsi=stock.get("rsi"),
        ema20=display_emas["ema20"],
        ema50=display_emas["ema50"],
        ema200=display_emas["ema200"],
        vwap=stock.get("vwap"),
        volume=stock.get("volume"),
        support=insight.get("support"),
        resistance=insight.get("resistance"),
        series=[SeriesPoint(**p) for p in series],
        timeframe=normalized_timeframe,
        timeframeLabel=timeframe_label,
        timeframeFallback=timeframe_fallback,
        dataQuality="Complete" if _is_complete(display_emas, stock) else "Partial",
        indicators=indicators,
    )


@router.get("/learning/stock/{symbol}", response_model=LearningJourneyOut)
def learning_stock(
    symbol: str,
    timeframe: str = "1W",
    reveal: bool = False,
) -> LearningJourneyOut:
    """Return study evidence, and the Mentor view only when `reveal=true`.

    `reveal` is a plain boolean default (not a Query object) so the function
    behaves identically when called directly by tests and when served by
    FastAPI's query-parameter handling.
    """
    study = _study_set(symbol, timeframe)

    if not reveal:
        return LearningJourneyOut(**study.model_dump(), recommendation=None)

    # Reveal: recompute the authoritative Mentor recommendation for this symbol.
    stock_result = market_data_service.get_stock(study.symbol)
    stock = stock_result.data
    insight = market_data_service.get_stock_insight(study.symbol).data
    decision = decide(stock, insight)
    recommendation_out = (
        None
        if decision.recommendation is None
        else _recommendation_out(decision.recommendation)
    )
    return LearningJourneyOut(**study.model_dump(), recommendation=recommendation_out)
