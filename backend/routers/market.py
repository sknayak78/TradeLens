"""Market data endpoints — served from static seed data + analysis service."""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException

from schemas import (
    MarketSummary,
    IndexItem,
    TodaysFocusItem,
    Ranking,
    StockDetail,
    StockSummary,
    SeriesPoint,
)
from seed_data import (
    MARKET_INDICES,
    TODAYS_FOCUS,
    OPPORTUNITIES,
    STOCKS_BY_SYMBOL,
    INSIGHTS,
    synthesize_insight,
)
from analysis.service import service as analysis_service

router = APIRouter(tags=["market"])


@router.get("/stocks", response_model=List[StockSummary])
def list_stocks(q: str = "", limit: int = 20) -> List[StockSummary]:
    """Return the stock catalog. Optional `q` filters by symbol or name."""
    query = q.strip().lower()
    if query:
        matches = [
            s for s in STOCKS_BY_SYMBOL.values()
            if query in s["symbol"].lower() or query in s["name"].lower()
        ]
    else:
        matches = list(STOCKS_BY_SYMBOL.values())
    matches = matches[: max(1, min(limit, 100))]
    return [
        StockSummary(
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
    return MarketSummary(
        indices=[IndexItem(**i) for i in MARKET_INDICES],
        todaysFocus=[TodaysFocusItem(**f) for f in TODAYS_FOCUS],
        status="open",
        asOf=datetime.now(timezone.utc),
    )


@router.get("/opportunities", response_model=List[Ranking])
def opportunities() -> List[Ranking]:
    """Today's Rankings — analysis-driven leaderboard.

    Every stock is analysed by StockAnalysisService; rows are sorted by
    strength score descending and re-ranked. Curated 'reason' strings from
    the seed keep the human context.
    """
    reason_by_symbol = {o["symbol"]: o["reason"] for o in OPPORTUNITIES}

    rows: List[dict] = []
    for symbol, stock in STOCKS_BY_SYMBOL.items():
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
    stock = STOCKS_BY_SYMBOL.get(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    insight = INSIGHTS.get(symbol) or synthesize_insight(symbol)
    analysis = analysis_service.analyse(stock)

    return StockDetail(
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
    )
